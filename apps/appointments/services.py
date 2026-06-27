from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.appointments.models import Appointment, QueueEntry

ACTIVE_APPOINTMENT_STATUSES = ('scheduled', 'confirmed', 'in_progress')
QUEUE_ACTIVE_STATUSES = ('waiting', 'called', 'in_consultation')


def _next_token(for_date):
    last = QueueEntry.objects.filter(
        appointment__scheduled_date=for_date,
    ).order_by('-token_number').first()
    return (last.token_number + 1) if last else 1


def _get_queue_entry(appointment):
    try:
        return appointment.queue_entry
    except QueueEntry.DoesNotExist:
        return None


def ensure_queue_entry(appointment):
    """Create a queue entry for today's active appointments (idempotent)."""
    if appointment.status in ('cancelled', 'no_show', 'completed'):
        return None
    today = timezone.localdate()
    if appointment.scheduled_date != today:
        return None
    existing = _get_queue_entry(appointment)
    if existing:
        return existing
    priority = 1 if appointment.appointment_type.code == 'EMRG' else 0
    return QueueEntry.objects.create(
        appointment=appointment,
        token_number=_next_token(today),
        priority=priority,
    )


def _update_queue_status(appointment, status):
    entry = _get_queue_entry(appointment)
    if not entry:
        if status == 'completed':
            return
        entry = ensure_queue_entry(appointment)
        if not entry:
            return
    if entry.status == status:
        return
    entry.status = status
    entry.save(update_fields=['status', 'updated_at'])


def _update_appointment_status(appointment, status):
    if appointment.status == status or appointment.status in ('cancelled', 'no_show'):
        return
    appointment.status = status
    appointment.save(update_fields=['status', 'updated_at'])


def sync_queue_on_appointment_save(appointment, created=False):
    if appointment.status in ('cancelled', 'no_show'):
        _update_queue_status(appointment, 'skipped')
        return
    if appointment.status == 'completed':
        _update_queue_status(appointment, 'completed')
        return
    if appointment.scheduled_date == timezone.localdate():
        if appointment.status in ACTIVE_APPOINTMENT_STATUSES:
            ensure_queue_entry(appointment)


def sync_today_appointments_to_queue():
    """Backfill queue entries for today's appointments that are missing one."""
    today = timezone.localdate()
    has_entry = QueueEntry.objects.filter(appointment_id=OuterRef('pk'))
    missing = Appointment.objects.filter(
        scheduled_date=today,
        status__in=ACTIVE_APPOINTMENT_STATUSES,
    ).annotate(has_queue=Exists(has_entry)).filter(has_queue=False)
    for appt in missing:
        ensure_queue_entry(appt)


def _resolve_appointment_for_visit(visit):
    if visit.appointment_id:
        return visit.appointment
    if not visit.doctor_id:
        return None
    today = timezone.localdate()
    return (
        Appointment.objects.filter(
            patient=visit.patient,
            doctor=visit.doctor,
            scheduled_date=today,
            status__in=ACTIVE_APPOINTMENT_STATUSES,
        )
        .order_by('scheduled_time')
        .first()
    )


def sync_queue_from_visit(visit):
    appointment = _resolve_appointment_for_visit(visit)
    if not appointment:
        return
    if not visit.appointment_id:
        from apps.clinical.models import Visit
        Visit.objects.filter(pk=visit.pk).update(appointment_id=appointment.pk)
        visit.appointment_id = appointment.pk

    if visit.status == 'in_progress':
        _update_queue_status(appointment, 'in_consultation')
        _update_appointment_status(appointment, 'in_progress')
    elif visit.status == 'completed':
        _update_queue_status(appointment, 'completed')
        _update_appointment_status(appointment, 'completed')
    elif visit.status == 'cancelled':
        _update_queue_status(appointment, 'skipped')


def create_queue_entry(appointment):
    """Backward-compatible alias for ensure_queue_entry."""
    return ensure_queue_entry(appointment)
