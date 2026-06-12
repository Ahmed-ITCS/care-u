from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from apps.clinical.models import Visit, Ward, Bed, Admission


@login_required
def visit_list(request):
    visits = Visit.objects.select_related('patient', 'doctor').order_by('-visit_date')[:50]
    if request.user.role == 'doctor':
        visits = visits.filter(doctor=request.user)
    return render(request, 'clinical/visits.html', {'visits': visits})


@login_required
def visit_detail(request, pk):
    visit = get_object_or_404(Visit.objects.select_related('patient', 'doctor'), pk=pk)
    return render(request, 'clinical/visit_detail.html', {'visit': visit})


@login_required
def ward_list(request):
    wards = Ward.objects.filter(is_active=True).prefetch_related('beds')
    return render(request, 'clinical/wards.html', {'wards': wards})


@login_required
def vitals_chart(request):
    return render(request, 'clinical/vitals.html')
