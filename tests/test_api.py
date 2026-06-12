import pytest
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestAuthAPI:
    def test_login_success(self, admin_user, tenant_prefix):
        client = APIClient()
        response = client.post(f'{tenant_prefix}/api/v1/auth/login/', {
            'username': 'testadmin', 'password': 'testpass123',
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_failure(self, admin_user, tenant_prefix):
        client = APIClient()
        response = client.post(f'{tenant_prefix}/api/v1/auth/login/', {
            'username': 'testadmin', 'password': 'wrongpassword',
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_endpoint(self, admin_user, tenant_prefix):
        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f'{tenant_prefix}/api/v1/me/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'testadmin'


@pytest.mark.django_db
class TestPatientAPI:
    def test_create_patient(self, receptionist_user, tenant_prefix):
        client = APIClient()
        client.force_authenticate(user=receptionist_user)
        response = client.post(f'{tenant_prefix}/api/v1/patients/', {
            'cnic': '35202-1234567-1',
            'first_name': 'Ahmed',
            'last_name': 'Hassan',
            'phone': '03001234567',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['mr_number'].startswith('CARE-U-')

    def test_patient_search(self, receptionist_user, tenant_prefix):
        from apps.patients.models import Patient
        Patient.objects.create(
            cnic='35202-9999999-1', first_name='Search', last_name='Test',
            phone='03009999999', registered_by=receptionist_user,
        )
        client = APIClient()
        client.force_authenticate(user=receptionist_user)
        response = client.get(f'{tenant_prefix}/api/v1/patients/?search=Search')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 1
