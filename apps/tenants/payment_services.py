"""
Shared subscription payment logic for Stripe, JazzCash, and Easypaisa.
"""
import logging
import uuid
from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def ensure_public_schema():
    connection.set_schema_to_public()


def generate_txn_ref(prefix='SUB'):
    return f'{prefix}{timezone.now().strftime("%y%m%d%H%M%S")}{uuid.uuid4().hex[:8].upper()}'


def create_subscription_payment(hospital, plan, method, amount=None):
    from apps.tenants.models import SubscriptionPayment

    ensure_public_schema()
    return SubscriptionPayment.objects.create(
        hospital=hospital,
        plan=plan,
        method=method,
        amount=amount if amount is not None else plan.price_monthly,
        currency='PKR',
        txn_ref=generate_txn_ref(),
        status=SubscriptionPayment.STATUS_PENDING,
    )


@transaction.atomic
def complete_subscription_payment(payment, gateway_txn_id='', gateway_response=None):
    """Mark payment complete and activate the hospital subscription for one month."""
    from apps.tenants.models import SubscriptionPayment
    from apps.tenants.services import upgrade_hospital_subscription

    ensure_public_schema()
    payment = SubscriptionPayment.objects.select_for_update().select_related('hospital', 'plan').get(pk=payment.pk)
    if payment.status == SubscriptionPayment.STATUS_COMPLETED:
        return payment.hospital

    today = timezone.now().date()
    base = payment.hospital.paid_until if payment.hospital.paid_until and payment.hospital.paid_until >= today else today
    paid_until = base + timedelta(days=30)

    hospital = upgrade_hospital_subscription(
        payment.hospital,
        payment.plan,
        paid_until,
        status='active',
    )
    payment.status = SubscriptionPayment.STATUS_COMPLETED
    payment.gateway_txn_id = gateway_txn_id or payment.gateway_txn_id
    if gateway_response is not None:
        payment.gateway_response = gateway_response
    payment.completed_at = timezone.now()
    payment.save(update_fields=[
        'status', 'gateway_txn_id', 'gateway_response', 'completed_at',
    ])
    logger.info(
        'Subscription payment %s completed via %s for %s',
        payment.txn_ref, payment.method, hospital.subdomain,
    )
    return hospital


def fail_subscription_payment(payment, gateway_response=None):
    from apps.tenants.models import SubscriptionPayment

    ensure_public_schema()
    payment.status = SubscriptionPayment.STATUS_FAILED
    if gateway_response is not None:
        payment.gateway_response = gateway_response
    payment.save(update_fields=['status', 'gateway_response'])
    return payment


def tenant_subscription_url(hospital):
    prefix = 'h'
    return f'/h/{hospital.subdomain}/subscription/'
