import csv
import io
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.import_data.services import parse_csv_file, run_import


SAMPLE_PATIENT_CSV = """cnic,first_name,last_name,phone,gender,city
35201-9999999-1,Test,Import,03009999999,M,Islamabad
35201-8888888-1,Sara,Import,03008888888,F,Rawalpindi
"""


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
