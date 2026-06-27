from django import forms
from django.contrib.auth import get_user_model

from apps.core.form_helpers import style_form
from apps.hr.models import Attendance, LeaveRequest, PayrollRun, Shift, StaffShiftAssignment
from apps.users.models import Role

User = get_user_model()

INPUT = 'input input-bordered w-full focus:border-primary'
SELECT = 'select select-bordered w-full'
TEXTAREA = 'textarea textarea-bordered w-full'


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['staff', 'date', 'check_in', 'check_out', 'status', 'notes']
        widgets = {
            'staff': forms.Select(attrs={'class': SELECT}),
            'date': forms.DateInput(attrs={'class': INPUT, 'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'class': INPUT, 'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'class': INPUT, 'type': 'time'}),
            'status': forms.Select(attrs={'class': SELECT}),
            'notes': forms.Textarea(attrs={'class': TEXTAREA, 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['staff'].queryset = User.objects.exclude(role='patient').filter(is_active=True)


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': SELECT}),
            'start_date': forms.DateInput(attrs={'class': INPUT, 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': INPUT, 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': TEXTAREA, 'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and end < start:
            raise forms.ValidationError('End date must be on or after start date.')
        return cleaned


class LeaveApprovalForm(forms.Form):
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': TEXTAREA, 'rows': 2, 'placeholder': 'Optional notes'}),
    )


class PayrollRunForm(forms.ModelForm):
    class Meta:
        model = PayrollRun
        fields = ['month', 'year']
        widgets = {
            'month': forms.NumberInput(attrs={'class': INPUT, 'min': 1, 'max': 12}),
            'year': forms.NumberInput(attrs={'class': INPUT, 'min': 2020, 'max': 2100}),
        }


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ['name', 'start_time', 'end_time', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Morning Shift'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)


class StaffShiftAssignmentForm(forms.ModelForm):
    class Meta:
        model = StaffShiftAssignment
        fields = ['staff', 'shift', 'ward', 'date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.clinical.models import Ward

        self.fields['staff'].queryset = User.objects.filter(
            role=Role.NURSE, is_active=True,
        ).order_by('first_name', 'last_name')
        self.fields['staff'].label = 'Nurse'
        self.fields['shift'].queryset = Shift.objects.filter(is_active=True).order_by('start_time')
        self.fields['ward'].queryset = Ward.objects.filter(is_active=True).order_by('name')
        self.fields['ward'].required = False
        self.fields['ward'].empty_label = 'No specific ward'
        style_form(self)
