from datetime import datetime, timedelta, time

from apps.appointments.models import Appointment, DoctorAvailabilityException, DoctorSchedule


def _add_minutes(t, minutes):
    dt = datetime.combine(datetime.today(), t) + timedelta(minutes=minutes)
    return dt.time()


def get_working_windows(doctor, date):
    """Return (start, end, slot_duration) windows for a doctor on a given date."""
    profile = getattr(doctor, 'doctor_profile', None)
    if not profile or not profile.is_on_duty:
        return []

    exception = DoctorAvailabilityException.objects.filter(doctor=doctor, date=date).first()
    if exception and not exception.is_available:
        return []

    day_of_week = date.weekday()
    schedules = DoctorSchedule.objects.filter(
        doctor=doctor, day_of_week=day_of_week, is_active=True,
    )
    if not schedules.exists():
        return []

    windows = []
    for schedule in schedules:
        start, end = schedule.start_time, schedule.end_time
        if exception and exception.is_available and exception.start_time and exception.end_time:
            start = max(start, exception.start_time)
            end = min(end, exception.end_time)
        if start < end:
            windows.append((start, end, schedule.slot_duration))
    return windows


def get_available_slots(doctor, date, slot_duration=None, exclude_appointment_id=None):
    """Generate bookable time slots for a doctor on a date, excluding taken appointments."""
    windows = get_working_windows(doctor, date)
    if not windows:
        return []

    booked_qs = Appointment.objects.filter(
        doctor=doctor,
        scheduled_date=date,
        status__in=['scheduled', 'confirmed', 'in_progress'],
    )
    if exclude_appointment_id:
        booked_qs = booked_qs.exclude(pk=exclude_appointment_id)
    booked = set(booked_qs.values_list('scheduled_time', flat=True))

    slots = []
    for start, end, duration in windows:
        step = slot_duration or duration or 15
        current = start
        while current < end:
            if current not in booked:
                slots.append(current)
            current = _add_minutes(current, step)
    return sorted(set(slots))


def format_slot(t):
    return t.strftime('%H:%M')


def get_doctor_duty_status(doctor, date=None, time=None):
    """Return on-duty and slot availability for a doctor."""
    profile = getattr(doctor, 'doctor_profile', None)
    if not profile:
        return {'on_duty': False, 'available': False, 'reason': 'Not a doctor profile'}

    if not profile.is_on_duty:
        return {'on_duty': False, 'available': False, 'reason': 'Off duty'}

    if date is None:
        return {'on_duty': True, 'available': True, 'reason': ''}

    exception = DoctorAvailabilityException.objects.filter(doctor=doctor, date=date).first()
    if exception:
        if not exception.is_available:
            return {
                'on_duty': True,
                'available': False,
                'reason': exception.reason or 'Unavailable today',
            }
        if time and exception.start_time and exception.end_time:
            if not (exception.start_time <= time < exception.end_time):
                return {'on_duty': True, 'available': False, 'reason': 'Outside custom hours today'}

    day_of_week = date.weekday()
    schedules = DoctorSchedule.objects.filter(
        doctor=doctor, day_of_week=day_of_week, is_active=True,
    )
    if not schedules.exists():
        return {'on_duty': True, 'available': False, 'reason': 'No schedule for this day'}

    if time is None:
        return {'on_duty': True, 'available': True, 'reason': ''}

    for schedule in schedules:
        if schedule.start_time <= time < schedule.end_time:
            return {'on_duty': True, 'available': True, 'reason': ''}

    return {'on_duty': True, 'available': False, 'reason': 'Outside working hours'}


def is_doctor_available(doctor, date, time):
    return get_doctor_duty_status(doctor, date, time)['available']


def doctors_with_status(doctors, date=None, time=None):
    """Attach availability status to each doctor for booking UI."""
    result = []
    for doctor in doctors:
        status = get_doctor_duty_status(doctor, date, time)
        result.append({'doctor': doctor, **status})
    return result
