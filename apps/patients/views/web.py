from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404

from apps.patients.models import Patient


@login_required
def patient_list(request):
    patients = Patient.objects.all()[:100]
    q = request.GET.get('q', '')
    if q:
        patients = Patient.objects.filter(
            models.Q(mr_number__icontains=q) |
            models.Q(cnic__icontains=q) |
            models.Q(full_name__icontains=q) |
            models.Q(phone__icontains=q)
        )[:50]
    return render(request, 'patients/list.html', {'patients': patients, 'q': q})


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    return render(request, 'patients/detail.html', {'patient': patient})


@login_required
def patient_register(request):
    return render(request, 'patients/register.html')


@login_required
def patient_portal(request):
    if request.user.role != 'patient':
        return redirect('patients:list')
    patient = getattr(request.user, 'patient_profile', None)
    return render(request, 'patients/portal.html', {'patient': patient})
