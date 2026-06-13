import pytest
from decimal import Decimal

from django.db import connection

from apps.tenants.jazzcash_services import (
    JAZZCASH_RESPONSE_HASH_FIELDS,
    _jazzcash_hash,
    build_jazzcash_payload,
    jazzcash_payment_successful,
)
from apps.tenants.models import SubscriptionPayment
from apps.tenants.payment_services import complete_subscription_payment, create_subscription_payment


@pytest.fixture
def paid_plan(db):
    connection.set_schema_to_public()
    from apps.tenants.models import SubscriptionPlan
    plan, _ = SubscriptionPlan.objects.update_or_create(
        name='test-basic',
        defaults={
            'display_name': 'Test Basic',
            'price_monthly': Decimal('9999'),
            'max_users': 15,
            'max_patients': 2000,
            'features': {'modules': 'core'},
            'is_active': True,
        },
    )
    return plan


@pytest.mark.django_db
class TestJazzCash:
    def test_build_payload_includes_secure_hash(self, test_tenant, paid_plan, settings):
        settings.JAZZCASH_MERCHANT_ID = 'MC12345'
        settings.JAZZCASH_PASSWORD = 'secret'
        settings.JAZZCASH_INTEGRITY_SALT = 'testsalt'
        settings.JAZZCASH_SANDBOX = True
        connection.set_schema_to_public()
        payment = create_subscription_payment(test_tenant, paid_plan, SubscriptionPayment.METHOD_JAZZCASH)
        payload = build_jazzcash_payload(payment, return_url='http://localhost/payments/jazzcash/return/')
        assert payload['pp_SecureHash']
        assert payload['pp_Amount'] == '999900'
        assert payload['ppmpf_1'] == str(test_tenant.pk)

    def test_successful_response_activates(self, test_tenant, paid_plan, settings):
        settings.JAZZCASH_MERCHANT_ID = 'MC12345'
        settings.JAZZCASH_PASSWORD = 'secret'
        settings.JAZZCASH_INTEGRITY_SALT = 'testsalt'
        connection.set_schema_to_public()
        payment = create_subscription_payment(test_tenant, paid_plan, SubscriptionPayment.METHOD_JAZZCASH)
        payload = build_jazzcash_payload(payment, return_url='http://localhost/payments/jazzcash/return/')
        response = {field: payload.get(field, '') for field in JAZZCASH_RESPONSE_HASH_FIELDS}
        response['pp_ResponseCode'] = '000'
        response['pp_ResponseMessage'] = 'Success'
        response['pp_AuthCode'] = 'AUTH'
        response['pp_RetreivalReferenceNo'] = 'REF123'
        response['pp_SettlementExpiry'] = ''
        response['pp_SubMerchantId'] = ''
        response['pp_BankID'] = ''
        response['pp_SecureHash'] = _jazzcash_hash(response, JAZZCASH_RESPONSE_HASH_FIELDS)

        assert jazzcash_payment_successful(response)
        complete_subscription_payment(payment, gateway_response=response)
        test_tenant.refresh_from_db()
        assert test_tenant.status == 'active'
        assert test_tenant.is_active_tenant


@pytest.mark.django_db
class TestEasypaisa:
    def test_build_payload(self, test_tenant, paid_plan, settings):
        from apps.tenants.easypaisa_services import build_easypaisa_payload

        settings.EASYPAISA_STORE_ID = 'STORE1'
        settings.EASYPAISA_HASH_KEY = 'hashkey'
        settings.EASYPAISA_SANDBOX = True
        connection.set_schema_to_public()
        payment = create_subscription_payment(test_tenant, paid_plan, SubscriptionPayment.METHOD_EASYPAISA)
        payload = build_easypaisa_payload(
            payment,
            post_back_url='http://localhost/payments/easypaisa/return/',
        )
        assert payload['encryptedHashRequest']
        assert payload['orderId'] == payment.txn_ref
