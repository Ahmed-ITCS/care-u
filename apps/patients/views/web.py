from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from apps.core.decorators import roles_required
from apps.patients.forms import PatientForm
from apps.patients.models import Patient
from apps.tenants.limits import check_patient_limit, SubscriptionLimitExceeded


@login_required
@roles_required('receptionist', 'doctor', 'nurse', 'admin')
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
@roles_required('receptionist', 'admin')
def patient_register(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            try:
                check_patient_limit()
            except SubscriptionLimitExceeded as exc:
                messages.error(request, str(exc.detail))
            else:
                patient = form.save(commit=False)
                patient.registered_by = request.user
                patient.save()
                messages.success(request, f'Patient {patient.full_name} registered ({patient.mr_number}).')
                return redirect('patients:detail', pk=patient.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientForm()
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'Register Patient',
        'subtitle': 'Add a new patient record',
        'back_url': 'patients:list',
        'submit_label': 'Register Patient',
    })


@login_required
@roles_required('receptionist', 'admin')
def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient updated.')
            return redirect('patients:detail', pk=patient.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientForm(instance=patient)
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': f'Edit {patient.full_name}',
        'back_href': reverse('patients:detail', kwargs={'pk': patient.pk}),
        'submit_label': 'Save Changes',
    })


@login_required
def patient_portal(request):
    if request.user.role != 'patient':
        return redirect('patients:list')
    patient = getattr(request.user, 'patient_profile', None)
    return render(request, 'patients/portal.html', {'patient': patient})
