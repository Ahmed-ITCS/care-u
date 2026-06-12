from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.hr.models import Attendance, LeaveRequest, PayrollRun


@login_required
def attendance_list(request):
    records = Attendance.objects.select_related('staff').order_by('-date')[:50]
    return render(request, 'hr/attendance.html', {'records': records})


@login_required
def leave_list(request):
    leaves = LeaveRequest.objects.select_related('staff').order_by('-created_at')[:50]
    if request.user.role != 'admin':
        leaves = leaves.filter(staff=request.user)
    return render(request, 'hr/leaves.html', {'leaves': leaves})


@login_required
def payroll_list(request):
    payrolls = PayrollRun.objects.order_by('-year', '-month')[:12]
    return render(request, 'hr/payroll.html', {'payrolls': payrolls})
