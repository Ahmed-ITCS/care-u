from django import forms

from apps.tenants.limits import ALL_PLAN_MODULES, CORE_PLAN_MODULES, MODULE_LABELS
from apps.tenants.models import SubscriptionPlan

OPTIONAL_MODULES = sorted(ALL_PLAN_MODULES - CORE_PLAN_MODULES)


class SubscriptionPlanForm(forms.ModelForm):
    modules_mode = forms.ChoiceField(
        choices=[
            ('all', 'All ERP modules'),
            ('core', 'Core modules only (Patients, Appointments, Clinical, Billing)'),
            ('custom', 'Custom module selection'),
        ],
        label='Module access',
    )
    custom_modules = forms.MultipleChoiceField(
        choices=[(m, MODULE_LABELS.get(m, m.title())) for m in OPTIONAL_MODULES],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Premium modules',
        help_text='Included on top of core modules when using custom selection.',
    )

    class Meta:
        model = SubscriptionPlan
        fields = (
            'name', 'display_name', 'price_monthly', 'max_users', 'max_patients', 'is_active',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'e.g. premium'}),
            'display_name': forms.TextInput(attrs={'class': 'input input-bordered w-full'}),
            'price_monthly': forms.NumberInput(attrs={'class': 'input input-bordered w-full', 'step': '0.01'}),
            'max_users': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
            'max_patients': forms.NumberInput(attrs={'class': 'input input-bordered w-full'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name == 'custom_modules':
                continue
            if name == 'is_active':
                field.widget.attrs.setdefault('class', 'checkbox checkbox-primary')
                continue
            if name == 'modules_mode':
                field.widget.attrs.setdefault('class', 'select select-bordered w-full')
                continue
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'input input-bordered w-full'
        if self.instance.pk:
            mode = self.instance.modules_mode
            if isinstance(mode, list):
                self.initial['modules_mode'] = 'custom'
                self.initial['custom_modules'] = mode
            else:
                self.initial['modules_mode'] = mode

    def clean_name(self):
        name = self.cleaned_data['name'].strip().lower()
        if not name:
            raise forms.ValidationError('Plan slug is required.')
        qs = SubscriptionPlan.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('A plan with this slug already exists.')
        return name

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('modules_mode') == 'custom' and not cleaned.get('custom_modules'):
            self.add_error('custom_modules', 'Select at least one module for a custom plan.')
        return cleaned

    def save(self, commit=True):
        plan = super().save(commit=False)
        mode = self.cleaned_data['modules_mode']
        features = dict(plan.features or {})
        if mode == 'custom':
            features['modules'] = list(self.cleaned_data['custom_modules'])
        else:
            features['modules'] = mode
        plan.features = features
        if commit:
            plan.save()
        return plan
