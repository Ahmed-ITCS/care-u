from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.core.models import TimeStampedModel


class AppointmentType(TimeStampedModel):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)
    duration_minutes = models.PositiveIntegerField(default=15)
    color = models.CharField(max_length=7, default='#1E40AF')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class DoctorSchedule(TimeStampedModel):
    DAYS = [(i, d) for i, d in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])]

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='schedules'
    )
    day_of_week = models.IntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=15)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['doctor', 'day_of_week', 'start_time']
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f'{self.doctor} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}'


class DoctorAvailabilityException(TimeStampedModel):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='availability_exceptions'
    )
    date = models.DateField()
    is_available = models.BooleanField(default=False)
    reason = models.CharField(max_length=200, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        unique_together = ['doctor', 'date']

    def __str__(self):
        status = 'Available' if self.is_available else 'Unavailable'
        return f'{self.doctor} - {self.date} ({status})'


class Appointment(TimeStampedModel):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'), ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'), ('completed', 'Completed'),
        ('cancelled', 'Cancelled'), ('no_show', 'No Show'),
    ]
    SOURCE_CHOICES = [('online', 'Online'), ('walk_in', 'Walk-in'), ('phone', 'Phone')]

    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments'
    )
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.PROTECT)
    scheduled_date = models.DateField(db_index=True)
    scheduled_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', db_index=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='walk_in')
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='booked_appointments'
    )
    reminder_sent_24h = models.BooleanField(default=False)
    reminder_sent_2h = models.BooleanField(default=False)

    class Meta:
        ordering = ['scheduled_date', 'scheduled_time']
        indexes = [
            models.Index(fields=['doctor', 'scheduled_date', 'scheduled_time']),
            models.Index(fields=['patient', 'status']),
        ]

    def clean(self):
        conflict = Appointment.objects.filter(
            doctor=self.doctor,
            scheduled_date=self.scheduled_date,
            scheduled_time=self.scheduled_time,
            status__in=['scheduled', 'confirmed', 'in_progress'],
        ).exclude(pk=self.pk)
        if conflict.exists():
            raise ValidationError('Doctor already has an appointment at this time')

    def __str__(self):
        return f'{self.patient.mr_number} with Dr.{self.doctor} on {self.scheduled_date}'


class QueueEntry(TimeStampedModel):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'), ('called', 'Called'),
        ('in_consultation', 'In Consultation'), ('completed', 'Completed'), ('skipped', 'Skipped'),
    ]

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='queue_entry')
    token_number = models.PositiveIntegerField()
    priority = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    called_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-priority', 'token_number']
        verbose_name_plural = 'Queue entries'

    def __str__(self):
        return f'Token #{self.token_number} - {self.appointment.patient.mr_number}'
