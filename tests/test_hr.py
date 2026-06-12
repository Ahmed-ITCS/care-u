import pytest
from django.test import Client
from rest_framework import status
from rest_framework.test import APIClient

from apps.hr.models import Attendance, LeaveRequest, PayrollRun
from apps.users.models import Role


@pytest.mark.django_db
class TestHRWeb:
    def test_admin_attendance_create(self, admin_user, receptionist_user, tenant_prefix):
        client = Client()
        client.force_login(admin_user)
        url = f'{tenant_prefix}/hr/attendance/new/'
        response = client.post(url, {
            'staff': receptionist_user.pk,
            'date': '2026-06-12',
            'status': 'present',
            'check_in': '09:00',
            'check_out': '17:00',
            'notes': '',
        })
        assert response.status_code == 302
        assert Attendance.objects.filter(staff=receptionist_user).exists()

    def test_staff_leave_request(self, doctor_user, tenant_prefix):
        client = Client()
        client.force_login(doctor_user)
        url = f'{tenant_prefix}/hr/leaves/new/'
        response = client.post(url, {
            'leave_type': 'annual',
            'start_date': '2026-07-01',
            'end_date': '2026-07-05',
            'reason': 'Family trip',
        })
        assert response.status_code == 302
        assert LeaveRequest.objects.filter(staff=doctor_user, status='pending').exists()


@pytest.mark.django_db
class TestHRAPI:
    def test_leave_api_create(self, doctor_user, tenant_prefix):
        client = APIClient()
        client.force_authenticate(user=doctor_user)
        url = f'{tenant_prefix}/api/v1/leave-requests/'
        response = client.post(url, {
            'leave_type': 'sick',
            'start_date': '2026-07-10',
            'end_date': '2026-07-11',
            'reason': 'Flu',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['staff'] == doctor_user.pk
        assert response.data['status'] == 'pending'

    def test_payroll_process_api(self, admin_user, tenant_prefix):
        run = PayrollRun.objects.create(month=6, year=2026)
        client = APIClient()
        client.force_authenticate(user=admin_user)
        url = f'{tenant_prefix}/api/v1/payroll/{run.pk}/process/'
        response = client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'processed'
