from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from apps.hr.decorators import admin_required
from apps.hr.filters import AttendanceFilter, LeaveRequestFilter, PayrollRunFilter, StaffShiftAssignmentFilter
from apps.hr.forms import (
    AttendanceForm, LeaveRequestForm, LeaveApprovalForm, PayrollRunForm,
    ShiftForm, StaffShiftAssignmentForm,
)
from apps.hr.models import Attendance, LeaveRequest, PayrollRun, Shift, StaffShiftAssignment
from apps.hr.services import process_payroll, approve_leave, reject_leave
from apps.core.list_filters import filter_list_context
from apps.users.models import Role


@login_required
@admin_required
def attendance_list(request):
    queryset = Attendance.objects.select_related('staff').order_by('-date')
    ctx = filter_list_context(
        request, queryset, AttendanceFilter, limit=100, clear_url=reverse('hr:attendance'),
    )
    ctx['records'] = ctx.pop('items')
    ctx['is_admin'] = True
    return render(request, 'hr/attendance.html', ctx)


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
    queryset = LeaveRequest.objects.select_related('staff', 'approved_by').order_by('-created_at')
    if not is_admin:
        queryset = queryset.filter(staff=request.user)
    ctx = filter_list_context(
        request, queryset, LeaveRequestFilter, limit=100,
        exclude_fields=() if is_admin else ('staff',),
        clear_url=reverse('hr:leaves'),
    )
    ctx['leaves'] = ctx.pop('items')
    ctx['is_admin'] = is_admin
    ctx['approval_form'] = LeaveApprovalForm()
    return render(request, 'hr/leaves.html', ctx)


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
    queryset = PayrollRun.objects.prefetch_related('items').order_by('-year', '-month')
    ctx = filter_list_context(
        request, queryset, PayrollRunFilter, limit=24, clear_url=reverse('hr:payroll'),
    )
    ctx['payrolls'] = ctx.pop('items')
    return render(request, 'hr/payroll.html', ctx)


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


@login_required
@admin_required
def roster_list(request):
    if not request.GET:
        return redirect(f"{reverse('hr:roster')}?date={timezone.localdate().isoformat()}")

    queryset = StaffShiftAssignment.objects.select_related(
        'staff', 'shift', 'ward',
    ).order_by('-date', 'shift__start_time')
    ctx = filter_list_context(
        request, queryset, StaffShiftAssignmentFilter, limit=100, clear_url=reverse('hr:roster'),
    )
    ctx['assignments'] = ctx.pop('items')
    ctx['is_admin'] = True
    ctx['shift_count'] = Shift.objects.filter(is_active=True).count()
    return render(request, 'hr/roster.html', ctx)


@login_required
@admin_required
def roster_create(request):
    if not Shift.objects.filter(is_active=True).exists():
        messages.warning(request, 'Create at least one shift before assigning staff.')
        return redirect('hr:shifts')

    if request.method == 'POST':
        form = StaffShiftAssignmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Shift assignment saved.')
            date = form.cleaned_data['date'].isoformat()
            return redirect(f"{reverse('hr:roster')}?date={date}")
        messages.error(request, 'Please correct the errors below.')
    else:
        initial = {'date': timezone.localdate()}
        date_param = request.GET.get('date')
        if date_param:
            initial['date'] = date_param
        form = StaffShiftAssignmentForm(initial=initial)
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'Assign Shift',
        'subtitle': 'Assign a nurse to a shift and optional ward',
        'back_url': 'hr:roster',
        'submit_label': 'Save Assignment',
    })


@login_required
@admin_required
def roster_delete(request, pk):
    assignment = get_object_or_404(StaffShiftAssignment, pk=pk)
    if request.method == 'POST':
        date = assignment.date.isoformat()
        assignment.delete()
        messages.success(request, 'Shift assignment removed.')
        return redirect(f"{reverse('hr:roster')}?date={date}")
    return redirect('hr:roster')


@login_required
@admin_required
def shift_list(request):
    shifts = Shift.objects.order_by('start_time')
    if request.method == 'POST':
        form = ShiftForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Shift created.')
            return redirect('hr:shifts')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ShiftForm()
    return render(request, 'hr/shifts.html', {
        'shifts': shifts,
        'form': form,
        'is_admin': True,
    })


@login_required
def my_roster(request):
    if request.user.role != Role.NURSE:
        messages.error(request, 'This page is for nursing staff only.')
        return redirect('core:dashboard')

    today = timezone.localdate()
    upcoming = StaffShiftAssignment.objects.filter(
        staff=request.user,
        date__gte=today,
    ).select_related('shift', 'ward').order_by('date', 'shift__start_time')[:30]
    recent = StaffShiftAssignment.objects.filter(
        staff=request.user,
        date__lt=today,
    ).select_related('shift', 'ward').order_by('-date', 'shift__start_time')[:10]

    return render(request, 'hr/my_roster.html', {
        'upcoming': upcoming,
        'recent': recent,
    })
