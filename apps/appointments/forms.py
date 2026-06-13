from django import forms
from django.contrib.auth import get_user_model

from apps.appointments.models import Appointment, AppointmentType
from apps.core.form_helpers import style_form
from apps.patients.models import Patient
from apps.users.models import Role

User = get_user_model()


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'patient', 'doctor', 'appointment_type', 'scheduled_date', 'scheduled_time',
            'status', 'source', 'reason', 'notes',
        ]
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time'}),
            'reason': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.all().order_by('full_name')
        self.fields['doctor'].queryset = User.objects.filter(role=Role.DOCTOR, is_active=True)
        self.fields['appointment_type'].queryset = AppointmentType.objects.filter(is_active=True)
        if self.instance.pk:
            self.fields['status'].required = True
        else:
            self.fields.pop('status', None)
        style_form(self)
