import pytest
from datetime import time, timedelta

from django.utils import timezone

from apps.appointments.models import Appointment, AppointmentType, QueueEntry
from apps.clinical.models import Visit
from apps.patients.models import Patient


def _appt_type():
    appt_type = AppointmentType.objects.filter(code='OPD').first()
    if not appt_type:
        appt_type = AppointmentType.objects.create(name='OPD', code='OPD', duration_minutes=15)
    return appt_type


def _patient(receptionist_user):
    return Patient.objects.create(
        cnic='35202-8888888-1', first_name='Queue', last_name='Patient',
        phone='03008888888', registered_by=receptionist_user,
    )


@pytest.mark.django_db
class TestQueueSync:
    def test_today_booking_auto_enqueues(self, doctor_user, receptionist_user):
        today = timezone.localdate()
        patient = _patient(receptionist_user)
        appt = Appointment.objects.create(
            patient=patient, doctor=doctor_user, appointment_type=_appt_type(),
            scheduled_date=today, scheduled_time=time(10, 0),
        )
        entry = QueueEntry.objects.get(appointment=appt)
        assert entry.status == 'waiting'
        assert entry.token_number == 1

    def test_future_booking_no_queue(self, doctor_user, receptionist_user):
        patient = _patient(receptionist_user)
        future = timezone.localdate() + timedelta(days=7)
        appt = Appointment.objects.create(
            patient=patient, doctor=doctor_user, appointment_type=_appt_type(),
            scheduled_date=future, scheduled_time=time(10, 0),
        )
        assert not QueueEntry.objects.filter(appointment=appt).exists()

    def test_cancelled_appointment_skips_queue(self, doctor_user, receptionist_user):
        today = timezone.localdate()
        patient = _patient(receptionist_user)
        appt = Appointment.objects.create(
            patient=patient, doctor=doctor_user, appointment_type=_appt_type(),
            scheduled_date=today, scheduled_time=time(11, 0),
        )
        appt.status = 'cancelled'
        appt.save(update_fields=['status'])
        entry = QueueEntry.objects.get(appointment=appt)
        assert entry.status == 'skipped'

    def test_visit_in_progress_moves_queue_to_consultation(self, doctor_user, receptionist_user):
        today = timezone.localdate()
        patient = _patient(receptionist_user)
        appt = Appointment.objects.create(
            patient=patient, doctor=doctor_user, appointment_type=_appt_type(),
            scheduled_date=today, scheduled_time=time(12, 0),
        )
        visit = Visit.objects.create(
            patient=patient, doctor=doctor_user, visit_type='opd', status='in_progress',
        )
        entry = QueueEntry.objects.get(appointment=appt)
        appt.refresh_from_db()
        visit.refresh_from_db()
        assert entry.status == 'in_consultation'
        assert appt.status == 'in_progress'
        assert visit.appointment_id == appt.pk

    def test_visit_completed_dequeues(self, doctor_user, receptionist_user):
        today = timezone.localdate()
        patient = _patient(receptionist_user)
        appt = Appointment.objects.create(
            patient=patient, doctor=doctor_user, appointment_type=_appt_type(),
            scheduled_date=today, scheduled_time=time(13, 0),
        )
        visit = Visit.objects.create(
            patient=patient, doctor=doctor_user, appointment=appt,
            visit_type='opd', status='in_progress',
        )
        visit.status = 'completed'
        visit.save(update_fields=['status'])
        entry = QueueEntry.objects.get(appointment=appt)
        appt.refresh_from_db()
        assert entry.status == 'completed'
        assert appt.status == 'completed'

    def test_sync_today_backfill(self, doctor_user, receptionist_user):
        from apps.appointments.services import sync_today_appointments_to_queue

        today = timezone.localdate()
        patient = _patient(receptionist_user)
        appt = Appointment.objects.create(
            patient=patient, doctor=doctor_user, appointment_type=_appt_type(),
            scheduled_date=today, scheduled_time=time(14, 0),
        )
        QueueEntry.objects.filter(appointment=appt).delete()
        sync_today_appointments_to_queue()
        assert QueueEntry.objects.filter(appointment=appt, status='waiting').exists()
