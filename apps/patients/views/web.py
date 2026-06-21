from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from apps.core.decorators import roles_required
from apps.core.list_filters import filter_list_context
from apps.clinical.doctor_scope import doctor_can_access_patient, doctor_patient_queryset
from apps.patients.filters import PatientFilter
from apps.patients.forms import PatientForm
from apps.patients.models import Patient
from apps.tenants.limits import check_patient_limit, SubscriptionLimitExceeded


@login_required
@roles_required('receptionist', 'doctor', 'nurse', 'admin')
def patient_list(request):
    outstanding_only = request.GET.get('outstanding') == '1'
    if request.user.role == 'doctor':
        queryset = doctor_patient_queryset(request.user)
        if outstanding_only:
            from apps.clinical.doctor_scope import doctor_outstanding_bills_queryset
            queryset = doctor_outstanding_bills_queryset(request.user)
        queryset = queryset.order_by('-created_at')
    else:
        queryset = Patient.objects.all().order_by('-created_at')
    ctx = filter_list_context(
        request, queryset, PatientFilter, limit=100, clear_url=reverse('patients:list'),
    )
    ctx['patients'] = ctx.pop('items')
    ctx['my_patients_view'] = request.user.role == 'doctor'
    ctx['outstanding_only'] = outstanding_only and request.user.role == 'doctor'
    return render(request, 'patients/list.html', ctx)


@login_required
def patient_detail(request, pk):
    from django.db.models import Sum
    from decimal import Decimal

    patient = get_object_or_404(Patient, pk=pk)
    if request.user.role == 'doctor' and not doctor_can_access_patient(request.user, patient):
        messages.error(request, 'This patient is not in your care list.')
        return redirect('patients:list')
    invoices = patient.invoices.order_by('-created_at')
    totals = invoices.aggregate(
        total_billed=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
    )
    total_billed = totals['total_billed'] or Decimal('0')
    total_paid = totals['total_paid'] or Decimal('0')
    lab_requests = patient.lab_requests.select_related('requested_by').order_by('-created_at')[:20]
    return render(request, 'patients/detail.html', {
        'patient': patient,
        'invoices': invoices,
        'total_billed': total_billed,
        'total_paid': total_paid,
        'balance_due': total_billed - total_paid,
        'lab_requests': lab_requests,
    })


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
