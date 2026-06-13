"""
Stripe Checkout, Customer Portal, and webhook sync for SaaS subscriptions.
All Hospital / SubscriptionPlan reads and writes run in the public schema.
"""
import logging
from datetime import datetime, timezone as dt_timezone

import stripe
from django.conf import settings
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)


class StripeNotConfigured(Exception):
    pass


class StripePlanNotReady(Exception):
    pass


def stripe_enabled():
    return bool(getattr(settings, 'STRIPE_SECRET_KEY', ''))


def _configure_stripe():
    if not stripe_enabled():
        raise StripeNotConfigured('Stripe is not configured. Set STRIPE_SECRET_KEY.')
    stripe.api_key = settings.STRIPE_SECRET_KEY


def _amount_minor_units(amount):
    """Convert decimal major units to Stripe's smallest currency unit."""
    return int(amount * 100)


def ensure_public_schema():
    connection.set_schema_to_public()


def sync_plan_to_stripe(plan):
    """Create or update Stripe Product + recurring Price for a subscription plan."""
    _configure_stripe()
    ensure_public_schema()

    if plan.name == 'trial' or plan.price_monthly <= 0:
        return plan

    metadata = {'plan_id': str(plan.pk), 'plan_slug': plan.name}

    if plan.stripe_product_id:
        stripe.Product.modify(
            plan.stripe_product_id,
            name=plan.display_name,
            active=plan.is_active,
            metadata=metadata,
        )
        product_id = plan.stripe_product_id
    else:
        product = stripe.Product.create(
            name=plan.display_name,
            metadata=metadata,
        )
        product_id = product.id
        plan.stripe_product_id = product_id

    currency = settings.STRIPE_CURRENCY.lower()
    unit_amount = _amount_minor_units(plan.price_monthly)

    price_needs_update = True
    if plan.stripe_price_id:
        try:
            existing = stripe.Price.retrieve(plan.stripe_price_id)
            if (
                existing.unit_amount == unit_amount
                and existing.currency == currency
                and existing.active
            ):
                price_needs_update = False
            else:
                stripe.Price.modify(plan.stripe_price_id, active=False)
        except stripe.error.InvalidRequestError:
            plan.stripe_price_id = ''

    if price_needs_update:
        price = stripe.Price.create(
            product=product_id,
            unit_amount=unit_amount,
            currency=currency,
            recurring={'interval': 'month'},
            metadata=metadata,
        )
        plan.stripe_price_id = price.id

    plan.save(update_fields=['stripe_product_id', 'stripe_price_id'])
    logger.info('Synced plan %s to Stripe price %s', plan.name, plan.stripe_price_id)
    return plan


def get_or_create_stripe_customer(hospital):
    _configure_stripe()
    ensure_public_schema()

    if hospital.stripe_customer_id:
        return hospital.stripe_customer_id

    customer = stripe.Customer.create(
        email=hospital.email,
        name=hospital.name,
        metadata={
            'hospital_id': str(hospital.pk),
            'subdomain': hospital.subdomain,
        },
    )
    hospital.stripe_customer_id = customer.id
    hospital.save(update_fields=['stripe_customer_id', 'updated_at'])
    return customer.id


def create_checkout_session(hospital, plan, success_url, cancel_url):
    _configure_stripe()
    ensure_public_schema()

    if not plan.stripe_price_id:
        sync_plan_to_stripe(plan)
    if not plan.stripe_price_id:
        raise StripePlanNotReady(f'Plan "{plan.display_name}" is not available for online checkout.')

    customer_id = get_or_create_stripe_customer(hospital)
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode='subscription',
        line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(hospital.pk),
        metadata={
            'hospital_id': str(hospital.pk),
            'plan_id': str(plan.pk),
        },
        subscription_data={
            'metadata': {
                'hospital_id': str(hospital.pk),
                'plan_id': str(plan.pk),
            },
        },
        allow_promotion_codes=True,
    )
    return session


def create_portal_session(hospital, return_url):
    _configure_stripe()
    ensure_public_schema()

    if not hospital.stripe_customer_id:
        get_or_create_stripe_customer(hospital)

    return stripe.billing_portal.Session.create(
        customer=hospital.stripe_customer_id,
        return_url=return_url,
    )


def _period_end_date(subscription):
    period_end = subscription.get('current_period_end') if isinstance(subscription, dict) else subscription.current_period_end
    return datetime.fromtimestamp(period_end, tz=dt_timezone.utc).date()


def apply_subscription_to_hospital(hospital, subscription, plan=None):
    """Activate or renew hospital subscription from a Stripe subscription object."""
    from apps.tenants.models import Hospital, SubscriptionPlan

    ensure_public_schema()
    sub_id = subscription['id'] if isinstance(subscription, dict) else subscription.id
    metadata = subscription.get('metadata', {}) if isinstance(subscription, dict) else (subscription.metadata or {})
    status = subscription.get('status') if isinstance(subscription, dict) else subscription.status

    if not plan and metadata.get('plan_id'):
        plan = SubscriptionPlan.objects.filter(pk=metadata['plan_id']).first()

    hospital = Hospital.objects.select_for_update().get(pk=hospital.pk)
    hospital.stripe_subscription_id = sub_id

    if plan:
        hospital.plan = plan

    if status in ('active', 'trialing'):
        hospital.status = 'active'
        hospital.paid_until = _period_end_date(subscription)
        hospital.trial_ends = None
    elif status in ('past_due', 'unpaid'):
        hospital.status = 'expired'
    elif status in ('canceled', 'incomplete_expired'):
        hospital.status = 'expired'
        hospital.stripe_subscription_id = ''

    hospital.save(update_fields=[
        'plan', 'status', 'paid_until', 'trial_ends',
        'stripe_subscription_id', 'updated_at',
    ])
    logger.info(
        'Applied Stripe subscription %s to hospital %s (status=%s, paid_until=%s)',
        sub_id, hospital.subdomain, hospital.status, hospital.paid_until,
    )
    return hospital


def handle_checkout_completed(session):
    from apps.tenants.models import Hospital, SubscriptionPlan

    ensure_public_schema()

    hospital_id = session.get('metadata', {}).get('hospital_id') or session.get('client_reference_id')
    plan_id = session.get('metadata', {}).get('plan_id')
    if not hospital_id:
        logger.warning('checkout.session.completed without hospital_id')
        return

    hospital = Hospital.objects.get(pk=hospital_id)
    plan = SubscriptionPlan.objects.filter(pk=plan_id).first() if plan_id else None
    subscription_id = session.get('subscription')
    if not subscription_id:
        logger.warning('checkout.session.completed without subscription for hospital %s', hospital_id)
        return

    _configure_stripe()
    subscription = stripe.Subscription.retrieve(subscription_id)
    apply_subscription_to_hospital(hospital, subscription, plan=plan)


def handle_subscription_updated(subscription):
    from apps.tenants.models import Hospital

    ensure_public_schema()
    hospital_id = (subscription.get('metadata') or {}).get('hospital_id')
    hospital = None
    if hospital_id:
        hospital = Hospital.objects.filter(pk=hospital_id).first()
    if not hospital:
        sub_id = subscription['id']
        hospital = Hospital.objects.filter(stripe_subscription_id=sub_id).first()
    if not hospital:
        logger.warning('subscription.updated for unknown hospital: %s', subscription.get('id'))
        return

    apply_subscription_to_hospital(hospital, subscription)


def handle_subscription_deleted(subscription):
    from apps.tenants.models import Hospital

    ensure_public_schema()
    sub_id = subscription['id']
    hospital = Hospital.objects.filter(stripe_subscription_id=sub_id).first()
    if not hospital:
        return
    hospital.status = 'expired'
    hospital.stripe_subscription_id = ''
    hospital.save(update_fields=['status', 'stripe_subscription_id', 'updated_at'])
    logger.info('Subscription canceled for hospital %s', hospital.subdomain)


def handle_payment_failed(invoice):
    from apps.tenants.models import Hospital

    ensure_public_schema()
    sub_id = invoice.get('subscription')
    if not sub_id:
        return
    hospital = Hospital.objects.filter(stripe_subscription_id=sub_id).first()
    if not hospital:
        return
    hospital.status = 'expired'
    hospital.save(update_fields=['status', 'updated_at'])
    logger.warning('Payment failed for hospital %s', hospital.subdomain)


def process_webhook_event(event):
    from apps.tenants.models import StripeWebhookEvent

    ensure_public_schema()
    if StripeWebhookEvent.objects.filter(stripe_event_id=event['id']).exists():
        return

    handlers = {
        'checkout.session.completed': lambda: handle_checkout_completed(event['data']['object']),
        'customer.subscription.updated': lambda: handle_subscription_updated(event['data']['object']),
        'customer.subscription.deleted': lambda: handle_subscription_deleted(event['data']['object']),
        'invoice.payment_failed': lambda: handle_payment_failed(event['data']['object']),
    }
    handler = handlers.get(event['type'])
    if handler:
        handler()

    StripeWebhookEvent.objects.create(
        stripe_event_id=event['id'],
        event_type=event['type'],
    )


def construct_webhook_event(payload, sig_header):
    _configure_stripe()
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
    )
