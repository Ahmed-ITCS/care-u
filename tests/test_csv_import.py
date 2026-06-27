import csv
import io
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.import_data.services import parse_csv_file, run_import
from apps.hr.models import Shift, StaffShiftAssignment
from apps.clinical.models import Ward
from apps.laboratory.models import TestCategory
from apps.users.models import Role, User


SAMPLE_PATIENT_CSV = """cnic,first_name,last_name,phone,gender,city
35201-9999999-1,Test,Import,03009999999,M,Islamabad
3520188888881,Sara,Import,03008888888,F,Rawalpindi
"""

SAMPLE_ROSTER_CSV = """nurse_username,shift,date,ward,notes
nurse1,Morning,2026-06-28,General Ward,
"""


@pytest.fixture
def nurse_user(db):
    return User.objects.create_user(
        username='nurse1', password='testpass123', role=Role.NURSE,
        email='nurse1@test.com', first_name='Nurse', last_name='One',
    )


@pytest.mark.django_db
class TestCSVImport:
    def test_parse_csv_normalizes_headers(self):
        f = SimpleUploadedFile('test.csv', SAMPLE_PATIENT_CSV.encode('utf-8'), content_type='text/csv')
        rows = parse_csv_file(f)
        assert rows[0]['first_name'] == 'Test'
        assert rows[1]['last_name'] == 'Import'

    def test_import_patients(self, receptionist_user):
        f = SimpleUploadedFile('patients.csv', SAMPLE_PATIENT_CSV.encode('utf-8'), content_type='text/csv')
        result = run_import('patients', f, receptionist_user)
        assert result.created == 2
        assert not result.errors

        f2 = SimpleUploadedFile('patients.csv', SAMPLE_PATIENT_CSV.encode('utf-8'), content_type='text/csv')
        result2 = run_import('patients', f2, receptionist_user)
        assert result2.errors
        assert result2.created == 0

    def test_missing_columns_raises(self, receptionist_user):
        bad_csv = "first_name,last_name\nAhmed,Hassan\n"
        f = SimpleUploadedFile('bad.csv', bad_csv.encode('utf-8'), content_type='text/csv')
        with pytest.raises(ValueError, match='Missing required columns'):
            run_import('patients', f, receptionist_user)

    def test_import_patients_accepts_digits_only_cnic(self, receptionist_user):
        csv_data = """cnic,first_name,last_name,phone
9040301728253,Ali,Khan,03001234567
"""
        f = SimpleUploadedFile('patients.csv', csv_data.encode('utf-8'), content_type='text/csv')
        result = run_import('patients', f, receptionist_user)
        assert result.created == 1
        assert not result.errors

    def test_import_lab_tests_creates_category(self, admin_user):
        csv_data = """code,name,category,price
TSH,Thyroid Stimulating Hormone,Endocrinology,1500
"""
        f = SimpleUploadedFile('labs.csv', csv_data.encode('utf-8'), content_type='text/csv')
        result = run_import('lab_tests', f, admin_user)
        assert result.created == 1
        assert TestCategory.objects.filter(name='Endocrinology').exists()

    def test_import_shifts_and_roster(self, admin_user, nurse_user):
        shift_csv = """name,start_time,end_time
Morning,08:00,16:00
"""
        run_import('shifts', SimpleUploadedFile(
            'shifts.csv', shift_csv.encode('utf-8'), content_type='text/csv',
        ), admin_user)

        ward_csv = """name,ward_type,floor,capacity
General Ward,general,2,20
"""
        run_import('wards', SimpleUploadedFile(
            'wards.csv', ward_csv.encode('utf-8'), content_type='text/csv',
        ), admin_user)

        result = run_import('shift_roster', SimpleUploadedFile(
            'roster.csv', SAMPLE_ROSTER_CSV.encode('utf-8'), content_type='text/csv',
        ), admin_user)
        assert result.created == 1
        assert StaffShiftAssignment.objects.filter(staff=nurse_user).exists()
        assert Shift.objects.filter(name='Morning').exists()
        assert Ward.objects.filter(name='General Ward').exists()
