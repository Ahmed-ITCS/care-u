import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from apps.core.services.dashboard import (
    get_dashboard_stat_cards,
    get_dashboard_kpis,
    get_revenue_chart_data,
    get_appointment_status_chart,
    get_patient_demographics,
)


@login_required
def dashboard(request):
    context = {
        'stat_cards': get_dashboard_stat_cards(request.user),
        'kpis': get_dashboard_kpis(request.user),
        'role': request.user.role,
    }
    if request.user.role == 'doctor':
        from apps.clinical.doctor_scope import doctor_patients_with_outstanding_bills
        context['doctor_outstanding_bills'] = doctor_patients_with_outstanding_bills(
            request.user, limit=15,
        )
    if request.user.role in ('admin', 'accountant'):
        context['revenue_chart_json'] = json.dumps(get_revenue_chart_data())
        context['appointment_chart_json'] = json.dumps(get_appointment_status_chart())
    return render(request, 'core/dashboard.html', context)


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'CARE-U'})


@login_required
def revenue_chart_api(request):
    return JsonResponse(get_revenue_chart_data())


@login_required
def appointment_chart_api(request):
    return JsonResponse(get_appointment_status_chart())


@login_required
def demographics_chart_api(request):
    return JsonResponse(get_patient_demographics())
