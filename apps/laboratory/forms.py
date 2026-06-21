from django import forms

from apps.core.form_helpers import style_form
from apps.laboratory.models import LabTestRequest, TestCatalog
from apps.patients.models import Patient


class LabTestRequestForm(forms.ModelForm):
    tests = forms.ModelMultipleChoiceField(
        queryset=TestCatalog.objects.filter(is_active=True).order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        label='Tests to order',
    )

    class Meta:
        model = LabTestRequest
        fields = ['patient', 'priority', 'clinical_notes']
        widgets = {'clinical_notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and getattr(user, 'role', None) == 'doctor':
            from apps.clinical.doctor_scope import doctor_patient_queryset
            self.fields['patient'].queryset = doctor_patient_queryset(user).order_by('full_name')
        else:
            self.fields['patient'].queryset = Patient.objects.all().order_by('full_name')
        style_form(self)
