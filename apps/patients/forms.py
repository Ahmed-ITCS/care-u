import re

from django import forms

from apps.core.form_helpers import style_form
from apps.patients.models import Patient

CNIC_PATTERN = re.compile(r'^\d{5}-\d{7}-\d$')


class PatientForm(forms.ModelForm):
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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)

    def clean_cnic(self):
        cnic = self.cleaned_data['cnic'].strip()
        if not CNIC_PATTERN.match(cnic):
            raise forms.ValidationError('CNIC must be in format 12345-1234567-1')
        return cnic
