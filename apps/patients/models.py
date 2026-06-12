import re
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from auditlog.registry import auditlog

from apps.core.models import TimeStampedModel, SoftDeleteModel, ActiveManager


CNIC_REGEX = re.compile(r'^\d{5}-\d{7}-\d$')


class InsuranceProvider(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Patient(TimeStampedModel, SoftDeleteModel):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'), ('O+', 'O+'), ('O-', 'O-'),
    ]

    mr_number = models.CharField(max_length=20, unique=True, db_index=True)
    cnic = models.CharField(max_length=15, unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200, db_index=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True)
    phone = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Islamabad')
    photo = models.ImageField(upload_to='patients/photos/', blank=True, null=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='registered_patients'
    )
    user_account = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_profile'
    )
    notes = models.TextField(blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mr_number']),
            models.Index(fields=['cnic']),
            models.Index(fields=['phone']),
            models.Index(fields=['full_name']),
        ]

    def save(self, *args, **kwargs):
        self.full_name = f'{self.first_name} {self.last_name}'.strip()
        if not self.mr_number:
            self.mr_number = self._generate_mr_number()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_mr_number(cls):
        year = timezone.now().year
        prefix = f'CARE-U-{year}-'
        with transaction.atomic():
            last = cls.all_objects.filter(
                mr_number__startswith=prefix
            ).select_for_update().order_by('-mr_number').first()
            if last:
                seq = int(last.mr_number.split('-')[-1]) + 1
            else:
                seq = 1
            return f'{prefix}{seq:05d}'

    def __str__(self):
        return f'{self.mr_number} - {self.full_name}'


class PatientInsurance(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='insurance_policies')
    provider = models.ForeignKey(InsuranceProvider, on_delete=models.CASCADE)
    policy_number = models.CharField(max_length=50)
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valid_from = models.DateField()
    valid_until = models.DateField()
    is_primary = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.patient.mr_number} - {self.provider.name}'


class EmergencyContact(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)

    def __str__(self):
        return f'{self.name} ({self.relationship})'


class Allergy(TimeStampedModel):
    SEVERITY_CHOICES = [('mild', 'Mild'), ('moderate', 'Moderate'), ('severe', 'Severe')]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='allergies')
    allergen = models.CharField(max_length=200)
    reaction = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='mild')
    noted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.patient.mr_number} - {self.allergen}'


class ChronicCondition(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='chronic_conditions')
    condition = models.CharField(max_length=200)
    diagnosed_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.patient.mr_number} - {self.condition}'


class MedicalHistory(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_history')
    title = models.CharField(max_length=200)
    description = models.TextField()
    recorded_date = models.DateField(default=timezone.now)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = 'Medical histories'

    def __str__(self):
        return f'{self.patient.mr_number} - {self.title}'


class FamilyHistory(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='family_history')
    relation = models.CharField(max_length=50)
    condition = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.patient.mr_number} - {self.relation}: {self.condition}'


class VitalSign(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    blood_pressure_systolic = models.PositiveSmallIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveSmallIntegerField(null=True, blank=True)
    pulse = models.PositiveSmallIntegerField(null=True, blank=True)
    respiratory_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    oxygen_saturation = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.patient.mr_number} vitals @ {self.created_at}'


class PatientDocument(TimeStampedModel):
    DOC_TYPES = [
        ('report', 'Report'), ('scan', 'Scan'), ('prescription', 'Prescription'),
        ('lab_result', 'Lab Result'), ('other', 'Other'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=20, choices=DOC_TYPES, default='other')
    file = models.FileField(upload_to='patients/documents/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.patient.mr_number} - {self.title}'


auditlog.register(Patient)
