from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST

from apps.tenants.models import Hospital, PlatformUser, SubscriptionPlan
from apps.tenants.forms import SubscriptionPlanForm
from apps.tenants.services import (
    extend_hospital_subscription,
    get_tenant_usage_stats,
    upgrade_hospital_subscription,
)
from apps.tenants.decorators import platform_admin_required


@platform_admin_required
def platform_dashboard(request):
    """Super Admin dashboard — manage all hospitals."""
    hospitals = Hospital.objects.exclude(schema_name='public').select_related('plan')
    hospital_stats = []
    for h in hospitals[:50]:
        stats = get_tenant_usage_stats(h)
        hospital_stats.append({'hospital': h, 'stats': stats})

    summary = {
        'total': hospitals.count(),
        'active': hospitals.filter(status='active').count(),
        'trial': hospitals.filter(status='trial').count(),
        'suspended': hospitals.filter(status='suspended').count(),
    }
    return render(request, 'tenants/platform/dashboard.html', {
        'hospital_stats': hospital_stats,
        'summary': summary,
        'platform_user': request.platform_user,
    })


def platform_login(request):
    """Super Admin login — public schema only."""
    if request.session.get('platform_user_id'):
        return redirect('platform:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            user = PlatformUser.objects.get(username=username)
            if user.check_password(password) and user.is_active:
                request.session['platform_user_id'] = user.id
                return redirect('platform:dashboard')
        except PlatformUser.DoesNotExist:
            pass
        messages.error(request, 'Invalid platform admin credentials.')
    return render(request, 'tenants/platform/login.html')


def platform_logout(request):
    request.session.pop('platform_user_id', None)
    return redirect('tenants:landing')


@platform_admin_required
def hospital_detail(request, pk):
    hospital = get_object_or_404(Hospital.objects.select_related('plan'), pk=pk)
    stats = get_tenant_usage_stats(hospital)
    plan = hospital.plan
    limits = {
        'staff_limit': plan.max_users if plan else None,
        'patients_limit': plan.max_patients if plan else None,
        'modules': plan.module_labels() if plan else '—',
    }
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')
    today = timezone.now().date()
    suggested_paid_until = (
        hospital.paid_until if hospital.paid_until and hospital.paid_until >= today
        else today + timedelta(days=30)
    )
    return render(request, 'tenants/platform/hospital_detail.html', {
        'hospital': hospital,
        'stats': stats,
        'limits': limits,
        'plans': plans,
        'suggested_paid_until': suggested_paid_until,
        'platform_user': request.platform_user,
    })


@platform_admin_required
@require_POST
def hospital_suspend(request, pk):
    hospital = get_object_or_404(Hospital, pk=pk)
    action = request.POST.get('action')

    if action == 'suspend':
        hospital.status = 'suspended'
        hospital.save(update_fields=['status', 'updated_at'])
        messages.warning(request, f'{hospital.name} suspended.')
    elif action == 'activate':
        hospital.status = 'active'
        hospital.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'{hospital.name} activated.')
    elif action == 'upgrade':
        plan_id = request.POST.get('plan_id')
        paid_until_raw = request.POST.get('paid_until', '').strip()
        if not plan_id or not paid_until_raw:
            messages.error(request, 'Select a plan and a paid-until date.')
        else:
            try:
                plan = get_object_or_404(SubscriptionPlan, pk=plan_id, is_active=True)
                paid_until = datetime.strptime(paid_until_raw, '%Y-%m-%d').date()
                upgrade_hospital_subscription(hospital, plan, paid_until, status='active')
                messages.success(
                    request,
                    f'{hospital.name} upgraded to {plan.display_name} until {paid_until:%b %d, %Y}.',
                )
            except ValueError:
                messages.error(request, 'Invalid paid-until date.')
    elif action == 'extend':
        try:
            months = int(request.POST.get('months', '1'))
            if months < 1 or months > 36:
                raise ValueError
            extend_hospital_subscription(hospital, months=months)
            messages.success(
                request,
                f'{hospital.name} subscription extended until {hospital.paid_until:%b %d, %Y}.',
            )
        except (ValueError, TypeError):
            messages.error(request, 'Invalid extension period.')
    else:
        messages.error(request, 'Unknown action.')

    return redirect('platform:hospital_detail', pk=pk)


@platform_admin_required
def hospital_list(request):
    hospitals = Hospital.objects.exclude(schema_name='public').select_related('plan')
    status_filter = request.GET.get('status')
    if status_filter:
        hospitals = hospitals.filter(status=status_filter)
    return render(request, 'tenants/platform/hospital_list.html', {
        'hospitals': hospitals, 'platform_user': request.platform_user,
    })


@platform_admin_required
def plan_list(request):
    plans = SubscriptionPlan.objects.all().order_by('price_monthly')
    return render(request, 'tenants/platform/plan_list.html', {
        'plans': plans,
        'platform_user': request.platform_user,
    })


@platform_admin_required
def plan_create(request):
    if request.method == 'POST':
        form = SubscriptionPlanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Plan "{form.instance.display_name}" created.')
            return redirect('platform:plans')
    else:
        form = SubscriptionPlanForm()
    return render(request, 'tenants/platform/plan_form.html', {
        'form': form,
        'title': 'Create subscription plan',
        'platform_user': request.platform_user,
    })


@platform_admin_required
def plan_edit(request, pk):
    plan = get_object_or_404(SubscriptionPlan, pk=pk)
    if request.method == 'POST':
        form = SubscriptionPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f'Plan "{plan.display_name}" updated.')
            return redirect('platform:plans')
    else:
        form = SubscriptionPlanForm(instance=plan)
    return render(request, 'tenants/platform/plan_form.html', {
        'form': form,
        'plan': plan,
        'title': f'Edit {plan.display_name}',
        'platform_user': request.platform_user,
    })
