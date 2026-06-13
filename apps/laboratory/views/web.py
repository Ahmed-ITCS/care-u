from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from apps.core.decorators import roles_required
from apps.laboratory.forms import LabTestRequestForm
from apps.laboratory.models import LabTestRequest, LabTestRequestItem
from apps.laboratory.models import TestCatalog


@login_required
def request_list(request):
    requests = LabTestRequest.objects.select_related('patient').order_by('-created_at')[:50]
    if request.user.role == 'lab_tech':
        requests = requests.filter(status__in=['requested', 'collected', 'in_progress'])
    return render(request, 'laboratory/requests.html', {'lab_requests': requests})


@login_required
@roles_required('doctor', 'nurse', 'receptionist', 'admin')
def request_create(request):
    if request.method == 'POST':
        form = LabTestRequestForm(request.POST)
        if form.is_valid():
            tests = form.cleaned_data.pop('tests')
            lab_request = form.save(commit=False)
            lab_request.requested_by = request.user
            lab_request.save()
            for test in tests:
                LabTestRequestItem.objects.create(request=lab_request, test=test)
            messages.success(request, f'Lab request {lab_request.request_number} created.')
            return redirect('laboratory:requests')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = LabTestRequestForm()
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'New Lab Request',
        'back_url': 'laboratory:requests',
        'submit_label': 'Submit Request',
    })


@login_required
def result_list(request):
    requests = LabTestRequest.objects.filter(status='completed').select_related('patient')[:50]
    return render(request, 'laboratory/results.html', {'lab_requests': requests})
