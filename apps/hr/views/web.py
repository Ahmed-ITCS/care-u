from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.hr.decorators import admin_required
from apps.hr.forms import AttendanceForm, LeaveRequestForm, LeaveApprovalForm, PayrollRunForm
from apps.hr.models import Attendance, LeaveRequest, PayrollRun
from apps.hr.services import process_payroll, approve_leave, reject_leave
from apps.users.models import Role


@login_required
@admin_required
def attendance_list(request):
    records = Attendance.objects.select_related('staff').order_by('-date')
    date_filter = request.GET.get('date')
    if date_filter:
        records = records.filter(date=date_filter)
    return render(request, 'hr/attendance.html', {
        'records': records[:100],
        'date_filter': date_filter,
        'is_admin': True,
    })


@login_required
@admin_required
def attendance_create(request):
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance recorded.')
            return redirect('hr:attendance')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = AttendanceForm(initial={'date': timezone.localdate()})
    return render(request, 'hr/attendance_form.html', {'form': form, 'title': 'Record Attendance'})


@login_required
@admin_required
def attendance_edit(request, pk):
    record = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance updated.')
            return redirect('hr:attendance')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = AttendanceForm(instance=record)
    return render(request, 'hr/attendance_form.html', {'form': form, 'title': 'Edit Attendance'})


@login_required
def leave_list(request):
    is_admin = request.user.role == Role.ADMIN
    leaves = LeaveRequest.objects.select_related('staff', 'approved_by').order_by('-created_at')
    if not is_admin:
        leaves = leaves.filter(staff=request.user)
    status_filter = request.GET.get('status')
    if status_filter:
        leaves = leaves.filter(status=status_filter)
    return render(request, 'hr/leaves.html', {
        'leaves': leaves[:100],
        'is_admin': is_admin,
        'status_filter': status_filter,
        'approval_form': LeaveApprovalForm(),
    })


@login_required
def leave_create(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.staff = request.user
            leave.save()
            messages.success(request, 'Leave request submitted.')
            return redirect('hr:leaves')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = LeaveRequestForm()
    return render(request, 'hr/leave_form.html', {'form': form})


@login_required
@admin_required
def leave_approve(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk, status='pending')
    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST)
        if form.is_valid():
            approve_leave(leave, request.user, form.cleaned_data['notes'])
            messages.success(request, f'Leave approved for {leave.staff.get_full_name()}.')
            return redirect('hr:leaves')
    return redirect('hr:leaves')


@login_required
@admin_required
def leave_reject(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk, status='pending')
    if request.method == 'POST':
        form = LeaveApprovalForm(request.POST)
        if form.is_valid():
            reject_leave(leave, request.user, form.cleaned_data['notes'])
            messages.warning(request, f'Leave rejected for {leave.staff.get_full_name()}.')
            return redirect('hr:leaves')
    return redirect('hr:leaves')


@login_required
@admin_required
def payroll_list(request):
    payrolls = PayrollRun.objects.prefetch_related('items').order_by('-year', '-month')
    return render(request, 'hr/payroll.html', {'payrolls': payrolls[:24]})


@login_required
@admin_required
def payroll_create(request):
    if request.method == 'POST':
        form = PayrollRunForm(request.POST)
        if form.is_valid():
            if PayrollRun.objects.filter(
                month=form.cleaned_data['month'],
                year=form.cleaned_data['year'],
            ).exists():
                messages.error(request, 'Payroll for this month already exists.')
            else:
                form.save()
                messages.success(request, 'Payroll run created.')
                return redirect('hr:payroll')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        now = timezone.localdate()
        form = PayrollRunForm(initial={'month': now.month, 'year': now.year})
    return render(request, 'hr/payroll_form.html', {'form': form})


@login_required
@admin_required
def payroll_detail(request, pk):
    payroll = get_object_or_404(PayrollRun.objects.prefetch_related('items__staff'), pk=pk)
    return render(request, 'hr/payroll_detail.html', {'payroll': payroll})


@login_required
@admin_required
def payroll_process(request, pk):
    payroll = get_object_or_404(PayrollRun, pk=pk)
    if payroll.status != 'draft':
        messages.error(request, 'This payroll run has already been processed.')
    elif request.method == 'POST':
        process_payroll(payroll, request.user)
        payroll.refresh_from_db()
        messages.success(request, f'Payroll processed — total PKR {payroll.total_amount:,.0f}.')
        return redirect('hr:payroll_detail', pk=pk)
    return redirect('hr:payroll_detail', pk=pk)
