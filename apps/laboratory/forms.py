from collections import OrderedDict

from django import forms

from apps.core.form_helpers import style_form, SELECT
from apps.laboratory.models import LabTestRequest, TestCatalog, TestCategory
from apps.patients.models import Patient


def tests_by_category():
    groups = OrderedDict()
    for test in TestCatalog.objects.filter(is_active=True).select_related('category').order_by(
        'category__name', 'name'
    ):
        groups.setdefault(test.category.name, []).append(test)
    return groups.items()


class LabTestRequestForm(forms.ModelForm):
    tests = forms.ModelMultipleChoiceField(
        queryset=TestCatalog.objects.filter(is_active=True).order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        label='Tests to order',
    )

    class Meta:
        model = LabTestRequest
        fields = ['patient', 'priority', 'clinical_notes']
        widgets = {
            'clinical_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Clinical indication, symptoms, or notes for the lab…'}),
            'priority': forms.Select(attrs={'class': SELECT}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and getattr(user, 'role', None) == 'doctor':
            from apps.clinical.doctor_scope import doctor_patient_queryset
            self.fields['patient'].queryset = doctor_patient_queryset(user).order_by('full_name')
        else:
            self.fields['patient'].queryset = Patient.objects.all().order_by('full_name')
        self.fields['priority'].choices = LabTestRequest.PRIORITY_CHOICES
        style_form(self)

    def selected_test_ids(self):
        value = self['tests'].value()
        if not value:
            return set()
        return {int(pk) for pk in value}


class TestCatalogForm(forms.ModelForm):
    new_category = forms.CharField(
        required=False,
        label='Or new category',
        help_text='Leave blank if you selected a category above.',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Blood Tests'}),
    )

    class Meta:
        model = TestCatalog
        fields = [
            'category', 'code', 'name', 'description', 'sample_type',
            'price', 'turnaround_hours', 'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'code': forms.TextInput(attrs={'placeholder': 'e.g. CBC'}),
            'sample_type': forms.TextInput(attrs={'placeholder': 'blood, urine, swab…'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = TestCategory.objects.all().order_by('name')
        self.fields['category'].required = False
        self.fields['category'].empty_label = '— Select category —'
        self.order_fields([
            'category', 'new_category', 'code', 'name', 'description',
            'sample_type', 'price', 'turnaround_hours', 'is_active',
        ])
        style_form(self)

    def clean_code(self):
        code = self.cleaned_data['code'].strip().upper()
        qs = TestCatalog.objects.filter(code__iexact=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A test with this code already exists.')
        return code

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        new_category = (cleaned.get('new_category') or '').strip()
        if new_category:
            cleaned['category'], _ = TestCategory.objects.get_or_create(name=new_category)
        elif not category:
            raise forms.ValidationError('Select a category or enter a new category name.')
        return cleaned

