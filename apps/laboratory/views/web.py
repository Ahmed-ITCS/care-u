from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.laboratory.models import LabTestRequest


@login_required
def request_list(request):
    requests = LabTestRequest.objects.select_related('patient').order_by('-created_at')[:50]
    if request.user.role == 'lab_tech':
        requests = requests.filter(status__in=['requested', 'collected', 'in_progress'])
    return render(request, 'laboratory/requests.html', {'lab_requests': requests})


@login_required
def result_list(request):
    requests = LabTestRequest.objects.filter(status='completed').select_related('patient')[:50]
    return render(request, 'laboratory/results.html', {'lab_requests': requests})
