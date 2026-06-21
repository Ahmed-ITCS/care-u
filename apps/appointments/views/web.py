from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.appointments.availability import doctors_with_status, get_available_slots, format_slot
from apps.appointments.filters import AppointmentFilter
from apps.appointments.forms import (
    AppointmentForm, DoctorAvailabilityExceptionForm, DoctorScheduleForm,
)
from apps.appointments.models import Appointment, DoctorAvailabilityException, DoctorSchedule, QueueEntry
from apps.core.decorators import roles_required
from apps.core.list_filters import filter_list_context, filters_active
from apps.users.models import Role, User


@login_required
def appointment_list(request):
    queryset = Appointment.objects.select_related(
        'patient', 'doctor', 'appointment_type'
    ).order_by('scheduled_date', 'scheduled_time')
    if not filters_active(request):
        today = timezone.now().date()
        queryset = queryset.filter(scheduled_date__gte=today)
    ctx = filter_list_context(
        request, queryset, AppointmentFilter, limit=50, clear_url=reverse('appointments:list'),
    )
    ctx['appointments'] = ctx.pop('items')
    return render(request, 'appointments/list.html', ctx)


@login_required
@roles_required('receptionist', 'admin')
def appointment_create(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.booked_by = request.user
            appt.save()
            messages.success(request, 'Appointment booked.')
            return redirect('appointments:list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = AppointmentForm()
    doctors = User.objects.filter(
        role=Role.DOCTOR, is_active=True, doctor_profile__is_on_duty=True,
    ).select_related('doctor_profile')
    return render(request, 'appointments/book.html', {
        'form': form,
        'title': 'Book Appointment',
        'doctors_status': doctors_with_status(doctors),
        'exclude_appointment_id': None,
    })


@login_required
@roles_required('receptionist', 'admin', 'doctor')
def appointment_edit(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if request.user.role == 'doctor' and appt.doctor_id != request.user.pk:
        messages.error(request, 'You can only edit your own appointments.')
        return redirect('appointments:doctor_calendar')
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appt)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated.')
            return redirect('appointments:list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = AppointmentForm(instance=appt)
    doctors = User.objects.filter(
        role=Role.DOCTOR, is_active=True, doctor_profile__is_on_duty=True,
    ).select_related('doctor_profile')
    date_val = form['scheduled_date'].value() or appt.scheduled_date
    time_val = form['scheduled_time'].value() or appt.scheduled_time
    if isinstance(date_val, str) and date_val:
        try:
            date_val = datetime.strptime(date_val, '%Y-%m-%d').date()
        except ValueError:
            date_val = appt.scheduled_date
    if isinstance(time_val, str) and time_val:
        try:
            time_val = datetime.strptime(time_val, '%H:%M').time()
        except ValueError:
            time_val = appt.scheduled_time
    return render(request, 'appointments/book.html', {
        'form': form,
        'title': 'Edit Appointment',
        'doctors_status': doctors_with_status(doctors, date_val, time_val),
        'exclude_appointment_id': appt.pk,
    })


@login_required
@require_GET
@roles_required('receptionist', 'admin')
def doctor_availability_api(request):
    """JSON endpoint for live doctor availability during booking."""
    date_str = request.GET.get('date')
    time_str = request.GET.get('time')
    date = None
    time = None
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if time_str:
        try:
            time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            pass

    doctors = User.objects.filter(
        role=Role.DOCTOR, is_active=True, doctor_profile__is_on_duty=True,
    ).select_related('doctor_profile')
    payload = []
    for entry in doctors_with_status(doctors, date, time):
        doctor = entry['doctor']
        profile = getattr(doctor, 'doctor_profile', None)
        slot_count = 0
        if date and entry['on_duty']:
            slot_count = len(get_available_slots(doctor, date))
        payload.append({
            'id': doctor.pk,
            'name': doctor.get_full_name(),
            'specialty': profile.specialty if profile else '',
            'on_duty': entry['on_duty'],
            'available': entry['available'],
            'reason': entry['reason'],
            'slot_count': slot_count,
        })
    return JsonResponse({'doctors': payload})


@login_required
@require_GET
@roles_required('receptionist', 'admin', 'doctor')
def doctor_slots_api(request):
    """Return available appointment time slots for a doctor on a given date."""
    doctor_id = request.GET.get('doctor')
    date_str = request.GET.get('date')
    type_id = request.GET.get('appointment_type')
    exclude_id = request.GET.get('exclude')

    if not doctor_id or not date_str:
        return JsonResponse({'slots': [], 'message': 'Select a doctor and date.'})

    try:
        appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        doctor = User.objects.get(pk=doctor_id, role=Role.DOCTOR, is_active=True)
    except (ValueError, User.DoesNotExist):
        return JsonResponse({'slots': [], 'message': 'Invalid doctor or date.'})

    slot_duration = None
    if type_id:
        from apps.appointments.models import AppointmentType
        try:
            slot_duration = AppointmentType.objects.get(pk=type_id).duration_minutes
        except AppointmentType.DoesNotExist:
            pass

    exclude_pk = int(exclude_id) if exclude_id else None
    slots = get_available_slots(doctor, appt_date, slot_duration, exclude_pk)
    message = ''
    if not slots:
        from apps.appointments.availability import get_doctor_duty_status
        status = get_doctor_duty_status(doctor, appt_date)
        message = status['reason'] or 'No available slots on this date.'

    return JsonResponse({
        'slots': [{'value': format_slot(s), 'label': s.strftime('%I:%M %p')} for s in slots],
        'message': message,
    })


@login_required
@roles_required('doctor')
def doctor_availability(request):
    """Doctor manages on-duty status, weekly schedule, and date exceptions."""
    doctor = request.user
    profile = getattr(doctor, 'doctor_profile', None)
    if not profile:
        messages.error(request, 'Doctor profile not found.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_duty':
            profile.is_on_duty = not profile.is_on_duty
            profile.save(update_fields=['is_on_duty', 'updated_at'])
            state = 'on duty' if profile.is_on_duty else 'off duty'
            messages.success(request, f'You are now {state}.')
            return redirect('appointments:doctor_availability')
        if action == 'add_schedule':
            form = DoctorScheduleForm(request.POST)
            if form.is_valid():
                schedule = form.save(commit=False)
                schedule.doctor = doctor
                schedule.save()
                messages.success(request, 'Schedule slot added.')
            else:
                messages.error(request, 'Could not add schedule slot.')
            return redirect('appointments:doctor_availability')
        if action == 'delete_schedule':
            schedule = get_object_or_404(DoctorSchedule, pk=request.POST.get('schedule_id'), doctor=doctor)
            schedule.delete()
            messages.success(request, 'Schedule slot removed.')
            return redirect('appointments:doctor_availability')
        if action == 'add_exception':
            form = DoctorAvailabilityExceptionForm(request.POST)
            if form.is_valid():
                exception = form.save(commit=False)
                exception.doctor = doctor
                exception.save()
                messages.success(request, 'Availability exception saved.')
            else:
                messages.error(request, 'Could not save exception.')
            return redirect('appointments:doctor_availability')
        if action == 'delete_exception':
            exception = get_object_or_404(
                DoctorAvailabilityException, pk=request.POST.get('exception_id'), doctor=doctor,
            )
            exception.delete()
            messages.success(request, 'Exception removed.')
            return redirect('appointments:doctor_availability')

    schedules = DoctorSchedule.objects.filter(doctor=doctor).order_by('day_of_week', 'start_time')
    exceptions = DoctorAvailabilityException.objects.filter(
        doctor=doctor, date__gte=timezone.now().date(),
    ).order_by('date')
    return render(request, 'appointments/doctor_availability.html', {
        'profile': profile,
        'schedules': schedules,
        'exceptions': exceptions,
        'schedule_form': DoctorScheduleForm(),
        'exception_form': DoctorAvailabilityExceptionForm(),
    })


@login_required
@roles_required('doctor')
def doctor_calendar(request):
    today = timezone.now().date()
    appointments = Appointment.objects.filter(
        doctor=request.user,
        scheduled_date__gte=today,
    ).select_related('patient', 'doctor').order_by('scheduled_date', 'scheduled_time')[:100]
    return render(request, 'appointments/calendar.html', {'appointments': appointments})


@login_required
def queue_board(request):
    today = timezone.now().date()
    if request.method == 'POST':
        entry_id = request.POST.get('entry_id')
        action = request.POST.get('action')
        entry = get_object_or_404(QueueEntry, pk=entry_id)
        if action == 'call':
            entry.status = 'called'
            entry.called_at = timezone.now()
            entry.save(update_fields=['status', 'called_at', 'updated_at'])
            messages.success(request, f'Called token #{entry.token_number}.')
        elif action == 'complete':
            entry.status = 'completed'
            entry.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Marked as completed.')
        return redirect('appointments:queue')

    queue = QueueEntry.objects.filter(
        created_at__date=today,
        status__in=['waiting', 'called', 'in_consultation'],
    ).select_related('appointment__patient', 'appointment__doctor')
    return render(request, 'appointments/queue.html', {'queue': queue})


@login_required
def my_appointments(request):
    if request.user.role == 'patient':
        appointments = Appointment.objects.filter(patient__user_account=request.user)
    else:
        appointments = Appointment.objects.filter(doctor=request.user)
    return render(request, 'appointments/my_appointments.html', {'appointments': appointments})
