import re
import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    DOCTOR = 'doctor', 'Doctor'
    NURSE = 'nurse', 'Nurse/Staff'
    PATIENT = 'patient', 'Patient'
    ACCOUNTANT = 'accountant', 'Accountant'
    PHARMACIST = 'pharmacist', 'Pharmacist'
    LAB_TECH = 'lab_tech', 'Lab Technician'
    RECEPTIONIST = 'receptionist', 'Receptionist'


CNIC_REGEX = re.compile(r'^\d{5}-\d{7}-\d$')


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECEPTIONIST)
    phone = models.CharField(max_length=20, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_clinical_staff(self):
        return self.role in (Role.ADMIN, Role.DOCTOR, Role.NURSE)

    @property
    def is_staff_member(self):
        return self.role != Role.PATIENT


class StaffProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    cnic = models.CharField(max_length=15, blank=True)
    photo = models.ImageField(upload_to='staff/photos/', blank=True, null=True)
    department = models.ForeignKey(
        'core.Department', on_delete=models.SET_NULL, null=True, blank=True
    )
    qualifications = models.TextField(blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f'Staff: {self.user.get_full_name()}'


class DoctorProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bio = models.TextField(blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'Dr. {self.user.get_full_name()} - {self.specialty}'


class OTPVerification(TimeStampedModel):
    PURPOSE_CHOICES = [
        ('login', 'Login'),
        ('password_reset', 'Password Reset'),
        ('registration', 'Registration'),
    ]
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='email')
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def generate(cls, user, purpose='login', channel='email'):
        code = f'{secrets.randbelow(10**6):06d}'
        otp = cls.objects.create(
            user=user,
            code=code,
            purpose=purpose,
            channel=channel,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        return otp

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def verify(self, code):
        if self.is_valid() and self.code == code:
            self.is_used = True
            self.save(update_fields=['is_used'])
            return True
        return False
