from django import forms
from django.contrib.auth import get_user_model

from apps.clinical.models import Visit
from apps.core.form_helpers import style_form
from apps.patients.models import Patient
from apps.users.models import Role

User = get_user_model()


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['patient', 'doctor', 'visit_type', 'notes']
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.all().order_by('full_name')
        self.fields['doctor'].queryset = User.objects.filter(role=Role.DOCTOR, is_active=True)
        style_form(self)
