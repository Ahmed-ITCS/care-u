import pytest
from django.db import connection

from apps.tenants.forms import SubscriptionPlanForm
from apps.tenants.limits import resolve_allowed_modules
from apps.tenants.models import SubscriptionPlan


@pytest.mark.django_db
class TestSubscriptionPlanForm:
    def test_create_custom_plan(self, db):
        connection.set_schema_to_public()
        form = SubscriptionPlanForm(data={
            'name': 'starter',
            'display_name': 'Starter',
            'description': 'For small clinics',
            'price_monthly': '4999',
            'max_users': '10',
            'max_patients': '500',
            'trial_days': '',
            'support_level': 'standard',
            'sort_order': '1',
            'modules_mode': 'custom',
            'selected_modules': ['patients', 'appointments', 'billing'],
            'is_featured': '',
            'is_active': 'on',
        })
        assert form.is_valid(), form.errors
        plan = form.save()
        allowed = resolve_allowed_modules(plan)
        assert 'patients' in allowed
        assert 'billing' in allowed
        assert 'laboratory' not in allowed
        assert plan.features.get('explicit_modules') is True

    def test_create_all_modules_plan(self, db):
        connection.set_schema_to_public()
        form = SubscriptionPlanForm(data={
            'name': 'full-erp',
            'display_name': 'Full ERP',
            'description': '',
            'price_monthly': '19999',
            'max_users': '0',
            'max_patients': '0',
            'trial_days': '',
            'support_level': 'priority',
            'sort_order': '2',
            'modules_mode': 'all',
            'is_featured': 'on',
            'is_active': 'on',
        })
        assert form.is_valid(), form.errors
        plan = form.save()
        assert plan.max_users == 0
        assert plan.is_featured is True
        assert SubscriptionPlan.objects.filter(is_featured=True).count() == 1
