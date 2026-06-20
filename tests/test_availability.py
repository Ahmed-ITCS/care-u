import pytest
from datetime import time, date

from apps.users.models import Role


@pytest.mark.django_db
class TestDoctorAvailability:
    def test_off_duty_doctor_unavailable(self, doctor_user):
        from apps.appointments.availability import get_doctor_duty_status

        doctor_user.doctor_profile.is_on_duty = False
        doctor_user.doctor_profile.save()
        status = get_doctor_duty_status(doctor_user, date(2026, 6, 23), time(10, 0))
        assert status['on_duty'] is False
        assert status['available'] is False

    def test_on_duty_with_schedule(self, doctor_user):
        from apps.appointments.models import DoctorSchedule
        from apps.appointments.availability import is_doctor_available

        doctor_user.doctor_profile.is_on_duty = True
        doctor_user.doctor_profile.save()
        DoctorSchedule.objects.create(
            doctor=doctor_user,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(17, 0),
        )
        monday = date(2026, 6, 22)
        assert is_doctor_available(doctor_user, monday, time(10, 0)) is True
        assert is_doctor_available(doctor_user, monday, time(18, 0)) is False

    def test_available_slots_exclude_booked(self, doctor_user, receptionist_user):
        from apps.appointments.models import DoctorSchedule, Appointment, AppointmentType
        from apps.appointments.availability import get_available_slots
        from apps.patients.models import Patient

        doctor_user.doctor_profile.is_on_duty = True
        doctor_user.doctor_profile.save()
        DoctorSchedule.objects.create(
            doctor=doctor_user,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(10, 0),
            slot_duration=15,
        )
        monday = date(2026, 6, 22)
        slots = get_available_slots(doctor_user, monday, slot_duration=15)
        assert time(9, 0) in slots
        assert time(9, 15) in slots

        patient = Patient.objects.create(
            cnic='35202-7777777-1', first_name='Slot', last_name='Test',
            phone='03007777777', registered_by=receptionist_user,
        )
        appt_type = AppointmentType.objects.filter(code='OPD').first()
        if not appt_type:
            appt_type = AppointmentType.objects.create(name='OPD', code='OPD', duration_minutes=15)
        Appointment.objects.create(
            patient=patient, doctor=doctor_user, appointment_type=appt_type,
            scheduled_date=monday, scheduled_time=time(9, 0),
        )
        slots_after = get_available_slots(doctor_user, monday, slot_duration=15)
        assert time(9, 0) not in slots_after
        assert time(9, 15) in slots_after
