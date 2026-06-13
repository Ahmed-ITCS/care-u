import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.db import connection
from django.test import Client
from django.utils import timezone

from apps.tenants.models import Hospital, SubscriptionPlan, StripeWebhookEvent
from apps.tenants.stripe_services import (
    apply_subscription_to_hospital,
    handle_checkout_completed,
    process_webhook_event,
)


@pytest.fixture
def paid_plan(db):
    connection.set_schema_to_public()
    plan, _ = SubscriptionPlan.objects.update_or_create(
        name='test-basic',
        defaults={
            'display_name': 'Test Basic',
            'price_monthly': 9999,
            'max_users': 15,
            'max_patients': 2000,
            'features': {'modules': 'core'},
            'is_active': True,
            'stripe_price_id': 'price_test123',
        },
    )
    return plan


@pytest.fixture
def expired_tenant(test_tenant, paid_plan):
    connection.set_schema_to_public()
    test_tenant.plan = paid_plan
    test_tenant.status = 'trial'
    test_tenant.trial_ends = date.today() - timedelta(days=1)
    test_tenant.save(update_fields=['plan', 'status', 'trial_ends', 'updated_at'])
    connection.set_tenant(test_tenant)
    return test_tenant


@pytest.mark.django_db
class TestPaywallMiddleware:
    def test_expired_tenant_redirects_to_subscription(self, expired_tenant, admin_user, tenant_prefix):
        connection.set_tenant(expired_tenant)
        client = Client()
        client.force_login(admin_user)
        response = client.get(f'{tenant_prefix}/')
        assert response.status_code == 302
        assert '/subscription/' in response.url

    def test_subscription_page_accessible_when_expired(self, expired_tenant, admin_user, tenant_prefix):
        connection.set_tenant(expired_tenant)
        client = Client()
        client.force_login(admin_user)
        response = client.get(f'{tenant_prefix}/subscription/')
        assert response.status_code == 200


@pytest.mark.django_db
class TestStripeWebhook:
    def test_checkout_completed_activates_hospital(self, test_tenant, paid_plan):
        connection.set_schema_to_public()
        test_tenant.status = 'trial'
        test_tenant.trial_ends = date.today() - timedelta(days=1)
        test_tenant.save(update_fields=['status', 'trial_ends', 'updated_at'])

        period_end = int((timezone.now() + timedelta(days=30)).timestamp())
        session = {
            'id': 'cs_test',
            'client_reference_id': str(test_tenant.pk),
            'metadata': {'hospital_id': str(test_tenant.pk), 'plan_id': str(paid_plan.pk)},
            'subscription': 'sub_test123',
        }

        mock_sub = {
            'id': 'sub_test123',
            'status': 'active',
            'current_period_end': period_end,
            'metadata': {'hospital_id': str(test_tenant.pk), 'plan_id': str(paid_plan.pk)},
        }

        with patch('apps.tenants.stripe_services._configure_stripe'), \
             patch('apps.tenants.stripe_services.stripe.Subscription.retrieve', return_value=mock_sub):
            handle_checkout_completed(session)

        test_tenant.refresh_from_db()
        assert test_tenant.status == 'active'
        assert test_tenant.stripe_subscription_id == 'sub_test123'
        assert test_tenant.plan_id == paid_plan.pk
        assert test_tenant.is_active_tenant

    def test_webhook_idempotency(self, test_tenant, paid_plan):
        connection.set_schema_to_public()
        event = {
            'id': 'evt_test_idempotent',
            'type': 'customer.subscription.deleted',
            'data': {
                'object': {
                    'id': 'sub_unknown',
                    'metadata': {},
                },
            },
        }
        StripeWebhookEvent.objects.create(stripe_event_id=event['id'], event_type=event['type'])
        process_webhook_event(event)
        assert StripeWebhookEvent.objects.filter(stripe_event_id=event['id']).count() == 1


@pytest.mark.django_db
class TestApplySubscription:
    def test_apply_active_subscription(self, test_tenant, paid_plan):
        connection.set_schema_to_public()
        period_end = int((timezone.now() + timedelta(days=30)).timestamp())
        sub = {
            'id': 'sub_apply',
            'status': 'active',
            'current_period_end': period_end,
            'metadata': {'plan_id': str(paid_plan.pk)},
        }
        apply_subscription_to_hospital(test_tenant, sub, plan=paid_plan)
        test_tenant.refresh_from_db()
        assert test_tenant.status == 'active'
        assert test_tenant.paid_until is not None
