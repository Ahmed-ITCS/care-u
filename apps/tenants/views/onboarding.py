from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse

from apps.hr.decorators import admin_required
from apps.tenants.middleware import ensure_request_tenant
from apps.tenants.services import run_tenant_onboarding


@login_required
def onboarding_wizard(request):
    """Multi-step onboarding for newly registered hospitals."""
    tenant = ensure_request_tenant(request)
    if not tenant or tenant.schema_name == 'public':
        return redirect('tenants:landing')

    if tenant.onboarding_completed:
        messages.info(request, 'Onboarding already completed.')
        return redirect('core:dashboard')

    step = int(request.GET.get('step', 1))

    if request.method == 'POST':
        if step == 1:
            request.session['onboarding'] = {
                'departments': [
                    {'name': n.strip(), 'code': n.strip()[:3].upper()}
                    for n in request.POST.get('departments', '').split(',') if n.strip()
                ],
            }
            return redirect(reverse('tenants:onboarding') + '?step=2')
        elif step == 2:
            onboarding = request.session.get('onboarding', {})
            onboarding['primary_color'] = request.POST.get('primary_color', '#1E40AF')
            onboarding['accent_color'] = request.POST.get('accent_color', '#059669')
            request.session['onboarding'] = onboarding
            return redirect(reverse('tenants:onboarding') + '?step=3')
        elif step == 3:
            onboarding = request.session.get('onboarding', {})
            run_tenant_onboarding(tenant, onboarding)
            tenant.primary_color = onboarding.get('primary_color', tenant.primary_color)
            tenant.accent_color = onboarding.get('accent_color', tenant.accent_color)
            tenant.save(update_fields=['primary_color', 'accent_color'])
            request.session.pop('onboarding', None)
            messages.success(request, f'Onboarding complete! Welcome to {settings.PLATFORM_NAME}.')
            return redirect('core:dashboard')

    return render(request, 'tenants/onboarding/wizard.html', {'step': step, 'tenant': tenant})


@login_required
@admin_required
def hospital_settings(request):
    """Hospital admin: customize branding and settings."""
    tenant = ensure_request_tenant(request)
    if request.method == 'POST':
        from apps.core.models import HospitalConfig
        config = HospitalConfig.load()
        config.name = request.POST.get('name', config.name)
        config.address = request.POST.get('address', config.address)
        config.phone = request.POST.get('phone', config.phone)
        config.tax_rate = request.POST.get('tax_rate', config.tax_rate)
        config.save()

        if tenant:
            tenant.primary_color = request.POST.get('primary_color', tenant.primary_color)
            tenant.accent_color = request.POST.get('accent_color', tenant.accent_color)
            tenant.receipt_header = request.POST.get('receipt_header', '')
            tenant.receipt_footer = request.POST.get('receipt_footer', '')
            tenant.save()

        messages.success(request, 'Settings updated.')
        return redirect('tenants:hospital_settings')

    from apps.core.models import HospitalConfig
    config = HospitalConfig.load()
    return render(request, 'tenants/onboarding/settings.html', {'config': config, 'tenant': tenant})
