from django.contrib.auth import (
    SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY, logout,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.views.decorators.http import require_http_methods

from apps.tenants.models import Hospital, PlatformUser, SubscriptionPlan
from apps.tenants.services import create_hospital_tenant, get_tenant_usage_stats
from apps.tenants.decorators import platform_admin_required
from apps.tenants.auth import resolve_tenant_and_authenticate, admin_email_taken
from apps.tenants.auth_logging import log_auth, session_snapshot


def landing(request):
    """Public marketing / landing page."""
    plans = SubscriptionPlan.objects.filter(is_active=True)
    return render(request, 'tenants/landing.html', {'plans': plans})


def hospital_register(request):
    """Hospital sign-up — creates tenant schema automatically."""
    if request.method == 'POST':
        admin_email = request.POST.get('admin_email', '').strip()
        if admin_email_taken(admin_email):
            messages.error(
                request,
                'An account with this email already exists. Sign in with that email, '
                'or register using a different admin email.',
            )
            plans = SubscriptionPlan.objects.filter(is_active=True)
            return render(request, 'tenants/register.html', {'plans': plans})

        data = {
            'hospital_name': request.POST.get('hospital_name', '').strip(),
            'subdomain': request.POST.get('subdomain', '').strip().lower(),
            'admin_name': request.POST.get('admin_name', '').strip(),
            'admin_email': admin_email,
            'admin_phone': request.POST.get('admin_phone', '').strip(),
            'admin_username': request.POST.get('admin_username', '').strip(),
            'admin_password': request.POST.get('admin_password', ''),
            'address': request.POST.get('address', '').strip(),
            'base_domain': settings.BASE_DOMAIN,
        }
        try:
            hospital, reg = create_hospital_tenant(data, approve=True)
            messages.success(
                request,
                f'Hospital "{hospital.name}" registered! Sign in at /login/ with your admin credentials.'
            )
            return redirect('tenants:register_success', subdomain=hospital.subdomain)
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Registration failed: {e}')

    plans = SubscriptionPlan.objects.filter(is_active=True)
    return render(request, 'tenants/register.html', {'plans': plans})


def register_success(request, subdomain):
    hospital = get_object_or_404(Hospital, subdomain=subdomain)
    return render(request, 'tenants/register_success.html', {
        'hospital': hospital,
        'login_url': '/login/',
        'onboarding_url': f'/h/{subdomain}/onboarding/',
    })


@require_http_methods(['GET', 'POST'])
def unified_login(request):
    """
    Single login for all hospitals — username/email + password only.
    System finds the correct tenant automatically.
    """
    if request.user.is_authenticated:
        subdomain = request.session.get('tenant_subdomain')
        if subdomain:
            return redirect(f'/h/{subdomain}/')
        return redirect('/')

    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        hospital_code = request.POST.get('hospital_code', '').strip().lower()
        log_auth('login_attempt', request, identifier=identifier, hospital_code=hospital_code or None)
        hospital, user, error = resolve_tenant_and_authenticate(
            identifier, password, hospital_subdomain=hospital_code or None,
        )
        if hospital and user:
            backend = 'django.contrib.auth.backends.ModelBackend'
            request.session[SESSION_KEY] = user.pk
            request.session[BACKEND_SESSION_KEY] = backend
            request.session[HASH_SESSION_KEY] = user.get_session_auth_hash()
            request.session['tenant_subdomain'] = hospital.subdomain
            request.session['tenant_schema'] = hospital.schema_name
            request.session.modified = True
            log_auth(
                'login_success',
                request,
                identifier=identifier,
                hospital=hospital.subdomain,
                user_id=user.pk,
                username=user.username,
                session_after=session_snapshot(request.session),
            )
            return redirect(f'/h/{hospital.subdomain}/')
        log_auth('login_failed', request, identifier=identifier, error=error)
        if error == 'ambiguous':
            messages.error(
                request,
                'This username exists at more than one hospital. Sign in with your email address instead.',
            )
        elif error == 'invalid_hospital':
            messages.error(request, 'Hospital code not found. Check the code from your registration email or page.')
        else:
            messages.error(request, 'Invalid username/email, password, or hospital code.')

    return render(request, 'tenants/unified_login.html')


def public_logout(request):
    """Sign out hospital user and clear tenant session — public /logout/ URL."""
    logout(request)
    request.session.flush()
    messages.success(request, 'You have been signed out.')
    return redirect(settings.LOGIN_URL)


def tenant_login_redirect(request):
    """Legacy URL — redirect to unified login."""
    return redirect(settings.LOGIN_URL)


def suspended(request):
    return render(request, 'tenants/suspended.html')


def pricing(request):
    plans = SubscriptionPlan.objects.filter(is_active=True)
    return render(request, 'tenants/pricing.html', {'plans': plans})
