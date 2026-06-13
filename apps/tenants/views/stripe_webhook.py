import logging

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.tenants.stripe_services import construct_webhook_event, process_webhook_event, stripe_enabled

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not stripe_enabled() or not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=503)

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = construct_webhook_event(payload, sig_header)
    except ValueError:
        logger.warning('Stripe webhook invalid payload')
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.warning('Stripe webhook signature verification failed')
        return HttpResponse(status=400)

    try:
        process_webhook_event(event)
    except Exception:
        logger.exception('Stripe webhook handler failed for %s', event.get('id'))
        return HttpResponse(status=500)

    return HttpResponse(status=200)
