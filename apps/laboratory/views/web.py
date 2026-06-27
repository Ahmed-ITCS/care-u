from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse

from apps.core.decorators import roles_required
from apps.core.list_filters import filter_list_context
from apps.clinical.doctor_scope import doctor_can_access_patient, doctor_lab_request_queryset
from apps.laboratory.filters import LabTestRequestFilter
from apps.laboratory.forms import LabTestRequestForm
from apps.laboratory.models import LabTestRequest, LabTestRequestItem
from apps.patients.models import Patient


@login_required
def request_list(request):
    queryset = LabTestRequest.objects.select_related('patient').order_by('-created_at')
    if request.user.role == 'doctor':
        queryset = doctor_lab_request_queryset(request.user)
    elif request.user.role == 'lab_tech':
        queryset = queryset.filter(status__in=['requested', 'collected', 'in_progress'])
    ctx = filter_list_context(
        request, queryset, LabTestRequestFilter, limit=50, clear_url=reverse('laboratory:requests'),
    )
    ctx['lab_requests'] = ctx.pop('items')
    return render(request, 'laboratory/requests.html', ctx)


@login_required
@roles_required('doctor', 'nurse', 'receptionist', 'admin', 'lab_tech')
def request_create(request):
    patient_pk = request.GET.get('patient') or request.POST.get('patient')
    initial_patient = None
    if patient_pk:
        initial_patient = Patient.objects.filter(pk=patient_pk).first()
        if request.user.role == 'doctor' and initial_patient and not doctor_can_access_patient(
            request.user, initial_patient
        ):
            messages.error(request, 'You can only order labs for your own patients.')
            return redirect('patients:list')

    if request.method == 'POST':
        form = LabTestRequestForm(request.POST, user=request.user)
        if form.is_valid():
            patient = form.cleaned_data['patient']
            if request.user.role == 'doctor' and not doctor_can_access_patient(request.user, patient):
                messages.error(request, 'You can only order labs for your own patients.')
            else:
                tests = form.cleaned_data.pop('tests')
                lab_request = form.save(commit=False)
                lab_request.requested_by = request.user
                lab_request.save()
                for test in tests:
                    LabTestRequestItem.objects.create(request=lab_request, test=test)
                messages.success(request, f'Lab request {lab_request.request_number} created.')
                if request.user.role == 'doctor' and patient:
                    return redirect('patients:detail', pk=patient.pk)
                return redirect('laboratory:requests')
        messages.error(request, 'Please correct the errors below.')
    else:
        initial = {'patient': initial_patient.pk} if initial_patient else {}
        form = LabTestRequestForm(initial=initial, user=request.user)
    if initial_patient and request.user.role == 'doctor':
        back_href = reverse('patients:detail', kwargs={'pk': initial_patient.pk})
    else:
        back_href = reverse('laboratory:requests')
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'New Lab Request',
        'back_href': back_href,
        'submit_label': 'Submit Request',
    })


@login_required
def result_list(request):
    queryset = LabTestRequest.objects.filter(status='completed').select_related('patient').order_by('-created_at')
    if request.user.role == 'doctor':
        queryset = doctor_lab_request_queryset(request.user).filter(status='completed')
    ctx = filter_list_context(
        request, queryset, LabTestRequestFilter, limit=50, clear_url=reverse('laboratory:results'),
    )
    ctx['lab_requests'] = ctx.pop('items')
    return render(request, 'laboratory/results.html', ctx)
