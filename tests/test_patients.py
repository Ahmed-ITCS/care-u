import pytest

from apps.core.cnic import format_cnic
from apps.core.phone import format_phone, split_phone
from apps.patients.forms import PatientForm
from apps.patients.models import Patient


class TestCnicFormatting:
    def test_format_digits_only(self):
        assert format_cnic('9040301728253') == '90403-0172825-3'

    def test_format_already_formatted(self):
        assert format_cnic('90403-0172825-3') == '90403-0172825-3'

    def test_format_ignores_invalid_length(self):
        assert format_cnic('12345') == '12345'


class TestPhoneFormatting:
    def test_split_local_pakistani_number(self):
        assert split_phone('03001234567') == ('+92', '03001234567')

    def test_split_international_number(self):
        assert split_phone('+15551234567') == ('+1', '5551234567')

    def test_format_pakistani_without_leading_zero(self):
        assert format_phone('+92', '3001234567') == '03001234567'

    def test_format_international_number(self):
        assert format_phone('+971', '501234567') == '+971501234567'


@pytest.mark.django_db
class TestPatientForm:
    def test_cnic_auto_formats_on_submit(self):
        form = PatientForm(data={
            'first_name': 'Ali',
            'last_name': 'Khan',
            'cnic': '9040301728253',
            'phone_0': '+92',
            'phone_1': '3001234567',
            'city': 'Islamabad',
        })
        assert form.is_valid(), form.errors
        assert form.cleaned_data['cnic'] == '90403-0172825-3'
        assert form.cleaned_data['phone'] == '03001234567'

    def test_phone_prefills_on_edit(self, receptionist_user):
        patient = Patient.objects.create(
            cnic='12345-9999999-1',
            first_name='Sara',
            last_name='Ali',
            phone='03009998888',
            registered_by=receptionist_user,
        )
        form = PatientForm(instance=patient)
        assert form.initial['phone'] == '03009998888'
        assert form['phone'].value() == '03009998888'


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
