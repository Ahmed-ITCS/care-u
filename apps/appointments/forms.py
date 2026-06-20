from django import forms
from django.contrib.auth import get_user_model

from apps.appointments.availability import get_available_slots, is_doctor_available
from apps.appointments.models import Appointment, AppointmentType, DoctorAvailabilityException, DoctorSchedule
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
            'scheduled_time': forms.Select(attrs={'id': 'id_scheduled_time'}),
            'reason': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.all().order_by('full_name')
        self.fields['doctor'].queryset = User.objects.filter(
            role=Role.DOCTOR, is_active=True, doctor_profile__is_on_duty=True,
        ).select_related('doctor_profile').order_by('last_name', 'first_name')
        self.fields['appointment_type'].queryset = AppointmentType.objects.filter(is_active=True)
        self.fields['scheduled_time'].choices = [('', 'Select doctor and date first')]
        if self.instance.pk:
            self.fields['status'].required = True
        else:
            self.fields.pop('status', None)
        style_form(self)
        self._populate_slot_choices()

    def _populate_slot_choices(self):
        doctor = self.data.get('doctor') or (self.instance.doctor_id if self.instance.pk else None)
        date_str = self.data.get('scheduled_date') or (
            self.instance.scheduled_date.isoformat() if self.instance.pk and self.instance.scheduled_date else None
        )
        if not doctor or not date_str:
            return
        try:
            from datetime import datetime
            appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            doctor_user = User.objects.get(pk=doctor, role=Role.DOCTOR)
        except (ValueError, User.DoesNotExist):
            return

        type_id = self.data.get('appointment_type') or (self.instance.appointment_type_id if self.instance.pk else None)
        slot_duration = None
        if type_id:
            try:
                slot_duration = AppointmentType.objects.get(pk=type_id).duration_minutes
            except AppointmentType.DoesNotExist:
                pass

        exclude_id = self.instance.pk if self.instance.pk else None
        slots = get_available_slots(doctor_user, appt_date, slot_duration, exclude_id)
        current = self.instance.scheduled_time if self.instance.pk else None
        choices = [('', 'Choose a time slot')]
        for slot in slots:
            choices.append((slot.strftime('%H:%M'), slot.strftime('%I:%M %p')))
        if current and current not in slots:
            choices.append((current.strftime('%H:%M'), current.strftime('%I:%M %p') + ' (current)'))
        self.fields['scheduled_time'].choices = choices

    def clean(self):
        cleaned = super().clean()
        doctor = cleaned.get('doctor')
        scheduled_date = cleaned.get('scheduled_date')
        scheduled_time = cleaned.get('scheduled_time')
        if doctor and scheduled_date and scheduled_time:
            type_obj = cleaned.get('appointment_type')
            duration = type_obj.duration_minutes if type_obj else None
            exclude_id = self.instance.pk if self.instance.pk else None
            slots = get_available_slots(doctor, scheduled_date, duration, exclude_id)
            if scheduled_time not in slots:
                if not is_doctor_available(doctor, scheduled_date, scheduled_time):
                    from apps.appointments.availability import get_doctor_duty_status
                    status = get_doctor_duty_status(doctor, scheduled_date, scheduled_time)
                    raise forms.ValidationError(
                        f'Dr. {doctor.get_full_name()} is not available: {status["reason"]}'
                    )
                raise forms.ValidationError(
                    f'That time slot is not available. Pick one of the listed times for '
                    f'{scheduled_date.strftime("%b %d, %Y")}.'
                )
        return cleaned


class DoctorScheduleForm(forms.ModelForm):
    class Meta:
        model = DoctorSchedule
        fields = ['day_of_week', 'start_time', 'end_time', 'slot_duration', 'is_active']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)


class DoctorAvailabilityExceptionForm(forms.ModelForm):
    class Meta:
        model = DoctorAvailabilityException
        fields = ['date', 'is_available', 'reason', 'start_time', 'end_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'reason': forms.TextInput(attrs={'placeholder': 'Leave, conference, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)
