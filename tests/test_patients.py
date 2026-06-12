import pytest
from apps.patients.models import Patient


@pytest.mark.django_db
class TestPatientModel:
    def test_mr_number_generation(self, receptionist_user):
        patient = Patient.objects.create(
            cnic='12345-1234567-1',
            first_name='Ali',
            last_name='Khan',
            phone='03001234567',
            registered_by=receptionist_user,
        )
        assert patient.mr_number.startswith('CARE-U-')
        assert patient.full_name == 'Ali Khan'

    def test_cnic_unique(self, receptionist_user):
        Patient.objects.create(
            cnic='12345-1234567-2', first_name='A', last_name='B',
            phone='03001111111', registered_by=receptionist_user,
        )
        with pytest.raises(Exception):
            Patient.objects.create(
                cnic='12345-1234567-2', first_name='C', last_name='D',
                phone='03002222222', registered_by=receptionist_user,
            )

    def test_soft_delete(self, receptionist_user):
        patient = Patient.objects.create(
            cnic='12345-1234567-3', first_name='X', last_name='Y',
            phone='03003333333', registered_by=receptionist_user,
        )
        patient.delete()
        assert Patient.objects.count() == 0
        assert Patient.all_objects.count() == 1
