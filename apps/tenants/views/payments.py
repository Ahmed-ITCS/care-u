from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.tenants.easypaisa_services import easypaisa_payment_successful, verify_easypaisa_response
from apps.tenants.jazzcash_services import jazzcash_payment_successful
from apps.tenants.models import SubscriptionPayment
from apps.tenants.payment_services import (
    complete_subscription_payment,
    ensure_public_schema,
    fail_subscription_payment,
    tenant_subscription_url,
)


def _payment_from_ref(txn_ref):
    ensure_public_schema()
    return SubscriptionPayment.objects.select_related('hospital', 'plan').filter(txn_ref=txn_ref).first()


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def jazzcash_return(request):
    ensure_public_schema()
    data = {**request.GET.dict(), **request.POST.dict()}
    txn_ref = data.get('pp_TxnRefNo', '')
    payment = _payment_from_ref(txn_ref)

    if not payment:
        return render(request, 'tenants/billing/payment_result.html', {
            'success': False,
            'title': 'Payment not found',
            'message': 'We could not match this payment to your hospital account.',
        })

    payment.gateway_response = data
    payment.save(update_fields=['gateway_response'])

    if jazzcash_payment_successful(data):
        complete_subscription_payment(
            payment,
            gateway_txn_id=data.get('pp_TxnRefNo', ''),
            gateway_response=data,
        )
        return redirect(f'{tenant_subscription_url(payment.hospital)}success/')

    fail_subscription_payment(payment, gateway_response=data)
    return redirect(f'{tenant_subscription_url(payment.hospital)}?payment=failed')


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def easypaisa_return(request):
    ensure_public_schema()
    data = {**request.GET.dict(), **request.POST.dict()}
    txn_ref = data.get('orderId', data.get('orderRefNum', ''))
    payment = _payment_from_ref(txn_ref)

    if not payment:
        return render(request, 'tenants/billing/payment_result.html', {
            'success': False,
            'title': 'Payment not found',
            'message': 'We could not match this payment to your hospital account.',
        })

    payment.gateway_response = data
    payment.save(update_fields=['gateway_response'])

    hash_ok = verify_easypaisa_response(data) if data.get('encryptedHashValue') else True
    if hash_ok and easypaisa_payment_successful(data):
        complete_subscription_payment(
            payment,
            gateway_txn_id=data.get('transactionId', txn_ref),
            gateway_response=data,
        )
        return redirect(f'{tenant_subscription_url(payment.hospital)}success/')

    fail_subscription_payment(payment, gateway_response=data)
    return redirect(f'{tenant_subscription_url(payment.hospital)}?payment=failed')
