"""
Easypaisa Pakistan — hosted checkout redirect.
"""
import hashlib
import hmac
import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class EasypaisaNotConfigured(Exception):
    pass


def easypaisa_enabled():
    return all([
        getattr(settings, 'EASYPAISA_STORE_ID', ''),
        getattr(settings, 'EASYPAISA_HASH_KEY', ''),
    ])


def easypaisa_checkout_url():
    if getattr(settings, 'EASYPAISA_SANDBOX', True):
        return 'https://easypaystg.easypaisa.com.pk/easypay/Index.jsf'
    return 'https://easypay.easypaisa.com.pk/easypay/Index.jsf'


def _easypaisa_hash(store_id, order_id, amount, post_back_url):
    raw = f'{store_id}&{order_id}&{amount}&{post_back_url}&{settings.EASYPAISA_HASH_KEY}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()


def build_easypaisa_payload(payment, post_back_url, email='', mobile=''):
    if not easypaisa_enabled():
        raise EasypaisaNotConfigured('Easypaisa is not configured.')

    amount = f'{payment.amount:.2f}'
    expiry = (timezone.now() + timedelta(hours=1)).strftime('%Y%m%d %H:%M:%S')

    payload = {
        'storeId': settings.EASYPAISA_STORE_ID,
        'orderId': payment.txn_ref,
        'transactionAmount': amount,
        'transactionType': 'MA',
        'mobileAccountNo': mobile,
        'emailAddress': email or payment.hospital.email,
        'tokenExpiry': expiry,
        'bankIdentificationNumber': getattr(settings, 'EASYPAISA_BANK_ID', ''),
        'postBackURL': post_back_url,
    }
    payload['encryptedHashRequest'] = _easypaisa_hash(
        payload['storeId'],
        payload['orderId'],
        payload['transactionAmount'],
        payload['postBackURL'],
    )
    return payload


def verify_easypaisa_response(data):
    if not easypaisa_enabled():
        return False
    received = data.get('encryptedHashValue', '') or data.get('encryptedHash', '')
    if not received:
        return False
    store_id = data.get('storeId', settings.EASYPAISA_STORE_ID)
    order_id = data.get('orderId', '')
    amount = data.get('transactionAmount', data.get('amount', ''))
    post_back = data.get('postBackURL', '')
    expected = _easypaisa_hash(store_id, order_id, amount, post_back)
    return hmac_compare(received.upper(), expected.upper())


def hmac_compare(a, b):
    return hmac.compare_digest(a, b)


def easypaisa_payment_successful(data):
    status = str(data.get('status', data.get('transactionStatus', ''))).upper()
    return status in ('0000', 'SUCCESS', 'PAID', 'COMPLETED') or data.get('responseCode') == '0000'
