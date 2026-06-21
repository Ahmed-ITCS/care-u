import pytest
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.clinical.doctor_scope import doctor_can_access_patient, doctor_patient_queryset
from apps.laboratory.models import LabTestRequest, LabTestRequestItem, TestCatalog, TestCategory
from apps.patients.models import Patient
from apps.users.models import Role, User


@pytest.fixture
def other_doctor(db):
    user = User.objects.create_user(
        username='otherdoc', password='testpass123',
        role=Role.DOCTOR, email='otherdoc@test.com',
    )
    from apps.users.models import DoctorProfile
    DoctorProfile.objects.create(user=user, specialty='Cardiology', license_number='DOC-2')
    return user


@pytest.fixture
def appointment_type(db):
    from apps.appointments.models import AppointmentType
    return AppointmentType.objects.create(name='Consultation', duration_minutes=30)


@pytest.fixture
def patient_a(db, receptionist_user):
    return Patient.objects.create(
        cnic='12345-1111111-1',
        first_name='Ali',
        last_name='Khan',
        phone='03001111111',
        registered_by=receptionist_user,
    )


@pytest.fixture
def patient_b(db, receptionist_user):
    return Patient.objects.create(
        cnic='12345-2222222-2',
        first_name='Sara',
        last_name='Ahmed',
        phone='03002222222',
        registered_by=receptionist_user,
    )


@pytest.mark.django_db
class TestDoctorScope:
    def test_doctor_sees_only_linked_patients(self, doctor_user, patient_a, patient_b, appointment_type):
        Appointment.objects.create(
            patient=patient_a,
            doctor=doctor_user,
            appointment_type=appointment_type,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
        )
        qs = doctor_patient_queryset(doctor_user)
        assert patient_a in qs
        assert patient_b not in qs
        assert doctor_can_access_patient(doctor_user, patient_a)
        assert not doctor_can_access_patient(doctor_user, patient_b)

    def test_doctor_outstanding_bills(
        self, doctor_user, patient_a, patient_b, appointment_type, receptionist_user,
    ):
        from apps.billing.models import Invoice
        from apps.clinical.doctor_scope import doctor_patients_with_outstanding_bills

        Appointment.objects.create(
            patient=patient_a,
            doctor=doctor_user,
            appointment_type=appointment_type,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
        )
        Appointment.objects.create(
            patient=patient_b,
            doctor=doctor_user,
            appointment_type=appointment_type,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
        )
        Invoice.objects.create(
            patient=patient_a,
            total_amount=5000,
            amount_paid=2000,
            status='partial',
            created_by=receptionist_user,
        )
        Invoice.objects.create(
            patient=patient_b,
            total_amount=1000,
            amount_paid=1000,
            status='paid',
            created_by=receptionist_user,
        )
        rows = doctor_patients_with_outstanding_bills(doctor_user)
        assert len(rows) == 1
        assert rows[0]['patient'].pk == patient_a.pk
        assert rows[0]['balance_due'] == 3000


@pytest.mark.django_db
class TestDoctorWebViews:
    def test_doctor_calendar_shows_only_own_appointments(
        self, client, tenant_prefix, doctor_user, other_doctor, patient_a, patient_b, appointment_type,
    ):
        Appointment.objects.create(
            patient=patient_a,
            doctor=doctor_user,
            appointment_type=appointment_type,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
        )
        Appointment.objects.create(
            patient=patient_b,
            doctor=other_doctor,
            appointment_type=appointment_type,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
        )
        client.force_login(doctor_user)
        response = client.get(f'{tenant_prefix}/appointments/calendar/')
        assert response.status_code == 200
        assert patient_a.full_name in response.content.decode()
        assert patient_b.full_name not in response.content.decode()

    def test_doctor_cannot_view_unlinked_patient(
        self, client, tenant_prefix, doctor_user, patient_b,
    ):
        client.force_login(doctor_user)
        response = client.get(f'{tenant_prefix}/patients/{patient_b.pk}/')
        assert response.status_code == 302
        assert response.url.endswith('/patients/')

    def test_doctor_can_order_lab_for_own_patient(
        self, client, tenant_prefix, doctor_user, patient_a, appointment_type,
    ):
        Appointment.objects.create(
            patient=patient_a,
            doctor=doctor_user,
            appointment_type=appointment_type,
            scheduled_date=timezone.now().date(),
            scheduled_time=timezone.now().time(),
        )
        category = TestCategory.objects.create(name='Blood')
        test = TestCatalog.objects.create(
            category=category, name='CBC', code='CBC', price=500,
        )
        client.force_login(doctor_user)
        url = f'{tenant_prefix}/laboratory/requests/new/?patient={patient_a.pk}'
        response = client.post(url, {
            'patient': patient_a.pk,
            'priority': 'normal',
            'clinical_notes': 'Routine check',
            'tests': [test.pk],
        })
        assert response.status_code == 302
        assert LabTestRequest.objects.filter(patient=patient_a, requested_by=doctor_user).exists()

    def test_doctor_cannot_order_lab_for_other_patient(
        self, client, tenant_prefix, doctor_user, patient_b,
    ):
        category = TestCategory.objects.create(name='Blood')
        test = TestCatalog.objects.create(
            category=category, name='CBC', code='CBC2', price=500,
        )
        client.force_login(doctor_user)
        url = f'{tenant_prefix}/laboratory/requests/new/?patient={patient_b.pk}'
        response = client.get(url)
        assert response.status_code == 302
