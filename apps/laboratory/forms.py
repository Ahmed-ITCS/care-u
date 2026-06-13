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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.all().order_by('full_name')
        style_form(self)
