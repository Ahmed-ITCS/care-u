from django import forms

from apps.core.cnic import format_cnic, is_valid_cnic
from apps.core.form_helpers import style_form
from apps.core.phone import PhoneField
from apps.patients.models import Patient


class PatientForm(forms.ModelForm):
    phone = PhoneField()

    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'cnic', 'date_of_birth', 'gender', 'blood_group',
            'phone', 'email', 'address', 'city', 'notes',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'cnic': forms.TextInput(attrs={
                'data-cnic-input': '',
                'placeholder': '12345-1234567-1',
                'autocomplete': 'off',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)

    def clean_cnic(self):
        cnic = format_cnic(self.cleaned_data['cnic'])
        if not is_valid_cnic(cnic):
            raise forms.ValidationError('CNIC must be in format 12345-1234567-1')
        return cnic
