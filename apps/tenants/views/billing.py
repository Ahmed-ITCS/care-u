from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.tenants.easypaisa_services import (
    EasypaisaNotConfigured,
    build_easypaisa_payload,
    easypaisa_checkout_url,
    easypaisa_enabled,
)
from apps.tenants.jazzcash_services import (
    JazzCashNotConfigured,
    build_jazzcash_payload,
    jazzcash_checkout_url,
    jazzcash_enabled,
)
from apps.tenants.middleware import ensure_request_tenant
from apps.tenants.models import SubscriptionPayment
from apps.tenants.payment_services import create_subscription_payment
from apps.tenants.stripe_services import (
    StripeNotConfigured,
    StripePlanNotReady,
    create_checkout_session,
    create_portal_session,
    stripe_enabled,
)


def _billing_base_url(request, tenant):
    prefix = settings.TENANT_SUBFOLDER_PREFIX.strip('/')
    return request.build_absolute_uri(f'/{prefix}/{tenant.subdomain}/subscription/')


def _paid_plans():
    from apps.tenants.models import SubscriptionPlan
    return SubscriptionPlan.objects.filter(is_active=True).exclude(name='trial').order_by('price_monthly')


def _any_payment_enabled():
    return stripe_enabled() or jazzcash_enabled() or easypaisa_enabled()


def _public_return_url(request, gateway):
    return request.build_absolute_uri(f'/payments/{gateway}/return/')


@login_required
def billing_paywall(request):
    """Subscription management — accessible even when trial/subscription expired."""
    tenant = ensure_request_tenant(request)
    if not tenant:
        return redirect('tenants:landing')

    plans = _paid_plans()
    is_admin = getattr(request.user, 'role', None) == 'admin'
    context = {
        'tenant': tenant,
        'plans': plans,
        'is_admin': is_admin,
        'stripe_enabled': stripe_enabled(),
        'jazzcash_enabled': jazzcash_enabled(),
        'easypaisa_enabled': easypaisa_enabled(),
        'any_payment_enabled': _any_payment_enabled(),
        'stripe_publishable_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', ''),
        'currency': settings.STRIPE_CURRENCY,
        'requires_payment': tenant.requires_payment,
        'days_until_expiry': tenant.days_until_expiry,
        'pending_payments': tenant.subscription_payments.filter(
            status=SubscriptionPayment.STATUS_PENDING,
        )[:5] if is_admin else [],
    }
    return render(request, 'tenants/billing/paywall.html', context)


@login_required
@require_POST
def billing_checkout(request):
    tenant = ensure_request_tenant(request)
    if not tenant or getattr(request.user, 'role', None) != 'admin':
        messages.error(request, 'Only hospital administrators can manage billing.')
        return redirect('tenants:billing')

    plan_id = request.POST.get('plan_id')
    plan = _paid_plans().filter(pk=plan_id).first()
    if not plan:
        messages.error(request, 'Invalid subscription plan.')
        return redirect('tenants:billing')

    base = _billing_base_url(request, tenant)
    try:
        session = create_checkout_session(
            tenant,
            plan,
            success_url=base + 'success/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=base + 'cancel/',
        )
    except StripeNotConfigured:
        messages.error(request, 'Online payments are not configured. Contact platform support.')
        return redirect('tenants:billing')
    except StripePlanNotReady as exc:
        messages.error(request, str(exc))
        return redirect('tenants:billing')

    return redirect(session.url, code=303)


@login_required
@require_POST
def billing_jazzcash(request):
    tenant = ensure_request_tenant(request)
    if not tenant or getattr(request.user, 'role', None) != 'admin':
        messages.error(request, 'Only hospital administrators can manage billing.')
        return redirect('tenants:billing')

    plan = _paid_plans().filter(pk=request.POST.get('plan_id')).first()
    if not plan:
        messages.error(request, 'Invalid subscription plan.')
        return redirect('tenants:billing')

    mobile = request.POST.get('mobile_account', '').strip()
    try:
        payment = create_subscription_payment(tenant, plan, SubscriptionPayment.METHOD_JAZZCASH)
        fields = build_jazzcash_payload(
            payment,
            return_url=_public_return_url(request, 'jazzcash'),
            mobile_account=mobile,
        )
    except JazzCashNotConfigured:
        messages.error(request, 'JazzCash is not configured. Contact platform support.')
        return redirect('tenants:billing')

    return render(request, 'tenants/billing/gateway_redirect.html', {
        'gateway': 'JazzCash',
        'action_url': jazzcash_checkout_url(),
        'fields': fields,
    })


@login_required
@require_POST
def billing_easypaisa(request):
    tenant = ensure_request_tenant(request)
    if not tenant or getattr(request.user, 'role', None) != 'admin':
        messages.error(request, 'Only hospital administrators can manage billing.')
        return redirect('tenants:billing')

    plan = _paid_plans().filter(pk=request.POST.get('plan_id')).first()
    if not plan:
        messages.error(request, 'Invalid subscription plan.')
        return redirect('tenants:billing')

    mobile = request.POST.get('mobile_account', '').strip()
    email = request.POST.get('email', tenant.email).strip()
    try:
        payment = create_subscription_payment(tenant, plan, SubscriptionPayment.METHOD_EASYPAISA)
        fields = build_easypaisa_payload(
            payment,
            post_back_url=_public_return_url(request, 'easypaisa'),
            email=email,
            mobile=mobile,
        )
    except EasypaisaNotConfigured:
        messages.error(request, 'Easypaisa is not configured. Contact platform support.')
        return redirect('tenants:billing')

    return render(request, 'tenants/billing/gateway_redirect.html', {
        'gateway': 'Easypaisa',
        'action_url': easypaisa_checkout_url(),
        'fields': fields,
    })


@login_required
@require_POST
def billing_portal(request):
    tenant = ensure_request_tenant(request)
    if not tenant or getattr(request.user, 'role', None) != 'admin':
        messages.error(request, 'Only hospital administrators can manage billing.')
        return redirect('tenants:billing')

    if not tenant.stripe_customer_id:
        messages.error(request, 'No billing account found. Subscribe to a plan first.')
        return redirect('tenants:billing')

    try:
        session = create_portal_session(tenant, return_url=_billing_base_url(request, tenant))
    except StripeNotConfigured:
        messages.error(request, 'Online payments are not configured.')
        return redirect('tenants:billing')

    return redirect(session.url, code=303)


@login_required
def billing_cancel(request):
    messages.info(request, 'Checkout canceled. You can choose a plan anytime.')
    return redirect('tenants:billing')


@login_required
def billing_success(request):
    tenant = ensure_request_tenant(request)
    messages.success(
        request,
        'Payment received! Your subscription is now active.',
    )
    if tenant and tenant.is_active_tenant:
        return redirect('core:dashboard')
    return redirect('tenants:billing')


@login_required
def billing_status_api(request):
    """JSON status for SPA / polling after checkout."""
    tenant = ensure_request_tenant(request)
    if not tenant:
        return JsonResponse({'detail': 'Tenant not found'}, status=404)
    return JsonResponse({
        'requires_payment': tenant.requires_payment,
        'status': tenant.status,
        'plan': tenant.plan.display_name if tenant.plan else None,
        'paid_until': tenant.paid_until.isoformat() if tenant.paid_until else None,
        'trial_ends': tenant.trial_ends.isoformat() if tenant.trial_ends else None,
        'is_active': tenant.is_active_tenant,
    })
