"""
JazzCash Pakistan — page redirect checkout (MWALLET / mobile account).
Docs: https://sandbox.jazzcash.com.pk/SandboxDocumentation/
"""
import hashlib
import hmac
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

JAZZCASH_HASH_FIELDS = [
    'pp_Amount', 'pp_BillReference', 'pp_Description', 'pp_Language',
    'pp_MerchantID', 'pp_Password', 'pp_ProductID', 'pp_ReturnURL',
    'pp_TxnCurrency', 'pp_TxnDateTime', 'pp_TxnExpiryDateTime', 'pp_TxnRefNo',
    'pp_TxnType', 'pp_Version',
    'ppmpf_1', 'ppmpf_2', 'ppmpf_3', 'ppmpf_4', 'ppmpf_5',
]

JAZZCASH_RESPONSE_HASH_FIELDS = [
    'pp_Amount', 'pp_AuthCode', 'pp_BankID', 'pp_BillReference', 'pp_Language',
    'pp_MerchantID', 'pp_ResponseCode', 'pp_ResponseMessage', 'pp_RetreivalReferenceNo',
    'pp_SettlementExpiry', 'pp_SubMerchantId', 'pp_TxnCurrency', 'pp_TxnDateTime',
    'pp_TxnRefNo', 'pp_TxnType', 'pp_Version', 'ppmpf_1', 'ppmpf_2', 'ppmpf_3',
    'ppmpf_4', 'ppmpf_5',
]


class JazzCashNotConfigured(Exception):
    pass


def jazzcash_enabled():
    return all([
        getattr(settings, 'JAZZCASH_MERCHANT_ID', ''),
        getattr(settings, 'JAZZCASH_PASSWORD', ''),
        getattr(settings, 'JAZZCASH_INTEGRITY_SALT', ''),
    ])


def jazzcash_checkout_url():
    if getattr(settings, 'JAZZCASH_SANDBOX', True):
        return 'https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform/'
    return 'https://payments.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform/'


def _jazzcash_hash(data, fields):
    salt = settings.JAZZCASH_INTEGRITY_SALT
    values = ''.join(str(data.get(field, '') or '') for field in fields)
    digest = hmac.new(salt.encode('utf-8'), values.encode('utf-8'), hashlib.sha256).hexdigest()
    return digest.upper()


def build_jazzcash_payload(payment, return_url, mobile_account=''):
    if not jazzcash_enabled():
        raise JazzCashNotConfigured('JazzCash is not configured.')

    now = timezone.now()
    expiry = now + timedelta(hours=1)
    amount_paisa = int(payment.amount * 100)

    payload = {
        'pp_Version': '1.1',
        'pp_TxnType': 'MWALLET',
        'pp_Language': 'EN',
        'pp_MerchantID': settings.JAZZCASH_MERCHANT_ID,
        'pp_Password': settings.JAZZCASH_PASSWORD,
        'pp_ProductID': getattr(settings, 'JAZZCASH_PRODUCT_ID', 'RETL'),
        'pp_TxnRefNo': payment.txn_ref,
        'pp_Amount': str(amount_paisa),
        'pp_TxnCurrency': 'PKR',
        'pp_TxnDateTime': now.strftime('%Y%m%d%H%M%S'),
        'pp_BillReference': f'CAREU-{payment.hospital_id}',
        'pp_Description': f'{payment.plan.display_name} subscription',
        'pp_TxnExpiryDateTime': expiry.strftime('%Y%m%d%H%M%S'),
        'pp_ReturnURL': return_url,
        'ppmpf_1': str(payment.hospital_id),
        'ppmpf_2': str(payment.plan_id),
        'ppmpf_3': payment.hospital.subdomain,
        'ppmpf_4': '',
        'ppmpf_5': '',
    }
    if mobile_account:
        payload['pp_MobileNumber'] = mobile_account
    payload['pp_SecureHash'] = _jazzcash_hash(payload, JAZZCASH_HASH_FIELDS)
    return payload


def verify_jazzcash_response(data):
    if not jazzcash_enabled():
        return False
    received = data.get('pp_SecureHash', '')
    if not received:
        return False
    expected = _jazzcash_hash(data, JAZZCASH_RESPONSE_HASH_FIELDS)
    return hmac.compare_digest(received.upper(), expected.upper())


def jazzcash_payment_successful(data):
    return (
        verify_jazzcash_response(data)
        and str(data.get('pp_ResponseCode', '')) == '000'
    )
