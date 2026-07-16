from django import forms

from apps.tenants.limits import BASE_MODULES, MODULE_LABELS, SELECTABLE_MODULES
from apps.tenants.models import SubscriptionPlan, DemoRequest

INPUT = 'input input-bordered w-full'
SELECT = 'select select-bordered w-full'
TEXTAREA = 'textarea textarea-bordered w-full'


class SubscriptionPlanForm(forms.ModelForm):
    modules_mode = forms.ChoiceField(
        choices=[
            ('all', 'All ERP modules'),
            ('core', 'Core only (Patients, Appointments, Clinical, Billing)'),
            ('custom', 'Custom — pick modules individually'),
        ],
        label='Module access',
        widget=forms.Select(attrs={'class': SELECT}),
    )
    selected_modules = forms.MultipleChoiceField(
        choices=[(m, MODULE_LABELS.get(m, m.title())) for m in SELECTABLE_MODULES],
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Included modules',
        help_text='Dashboard, staff management, and notifications are always included.',
    )

    class Meta:
        model = SubscriptionPlan
        fields = (
            'name', 'display_name', 'description', 'price_monthly',
            'max_users', 'max_patients', 'trial_days', 'support_level',
            'sort_order', 'is_featured', 'is_active',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT, 'placeholder': 'e.g. premium'}),
            'display_name': forms.TextInput(attrs={'class': INPUT}),
            'description': forms.Textarea(attrs={'class': TEXTAREA, 'rows': 3}),
            'price_monthly': forms.NumberInput(attrs={'class': INPUT, 'step': '0.01', 'min': '0'}),
            'max_users': forms.NumberInput(attrs={'class': INPUT, 'min': '0'}),
            'max_patients': forms.NumberInput(attrs={'class': INPUT, 'min': '0'}),
            'trial_days': forms.NumberInput(attrs={'class': INPUT, 'min': '1', 'placeholder': 'e.g. 14'}),
            'support_level': forms.Select(attrs={'class': SELECT}),
            'sort_order': forms.NumberInput(attrs={'class': INPUT, 'min': '0'}),
        }
        help_texts = {
            'max_users': 'Use 0 for unlimited staff.',
            'max_patients': 'Use 0 for unlimited patients.',
            'trial_days': 'Only used for trial-type plans (e.g. free trial).',
            'sort_order': 'Lower numbers appear first on the pricing page.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['is_active'].widget.attrs.setdefault('class', 'checkbox checkbox-primary')
        self.fields['is_featured'].widget.attrs.setdefault('class', 'checkbox checkbox-primary')
        if self.instance.pk:
            features = self.instance.features or {}
            mode = features.get('modules', 'all')
            if isinstance(mode, list):
                self.initial['modules_mode'] = 'custom'
                if features.get('explicit_modules'):
                    self.initial['selected_modules'] = mode
                else:
                    from apps.tenants.limits import resolve_allowed_modules
                    allowed = resolve_allowed_modules(self.instance) - BASE_MODULES
                    self.initial['selected_modules'] = sorted(allowed)
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
        if cleaned.get('modules_mode') == 'custom' and not cleaned.get('selected_modules'):
            self.add_error('selected_modules', 'Select at least one module for a custom plan.')
        return cleaned

    def save(self, commit=True):
        plan = super().save(commit=False)
        mode = self.cleaned_data['modules_mode']
        features = dict(plan.features or {})
        if mode == 'custom':
            features['modules'] = list(self.cleaned_data['selected_modules'])
            features['explicit_modules'] = True
        else:
            features['modules'] = mode
            features.pop('explicit_modules', None)
        plan.features = features
        if commit:
            plan.save()
            if plan.is_featured:
                SubscriptionPlan.objects.exclude(pk=plan.pk).update(is_featured=False)
        return plan


class DemoRequestForm(forms.ModelForm):
    """'Book a Demo' lead form shown in the landing-page modal."""

    class Meta:
        model = DemoRequest
        fields = ['name', 'hospital_name', 'email', 'phone', 'team_size', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT, 'placeholder': 'Dr. Jane Doe', 'autocomplete': 'name',
            }),
            'hospital_name': forms.TextInput(attrs={
                'class': INPUT, 'placeholder': 'City General Hospital', 'autocomplete': 'organization',
            }),
            'email': forms.EmailInput(attrs={
                'class': INPUT, 'placeholder': 'you@hospital.com', 'autocomplete': 'email',
            }),
            'phone': forms.TextInput(attrs={
                'class': INPUT, 'placeholder': '+92 3XX XXXXXXX', 'autocomplete': 'tel',
            }),
            'team_size': forms.Select(attrs={'class': SELECT}, choices=[
                ('', 'Team size (optional)'),
                ('1-10', '1–10 staff'),
                ('11-50', '11–50 staff'),
                ('51-200', '51–200 staff'),
                ('200+', '200+ staff'),
            ]),
            'message': forms.Textarea(attrs={
                'class': TEXTAREA, 'rows': 3,
                'placeholder': 'Anything specific you want to see? (optional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['hospital_name'].required = True
        self.fields['email'].required = True
        self.fields['phone'].required = False
        self.fields['team_size'].required = False
        self.fields['message'].required = False
