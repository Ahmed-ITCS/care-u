from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class Ward(TimeStampedModel):
    WARD_TYPES = [
        ('general', 'General'), ('icu', 'ICU'), ('pediatric', 'Pediatric'),
        ('maternity', 'Maternity'), ('private', 'Private'), ('emergency', 'Emergency'),
    ]

    name = models.CharField(max_length=100)
    ward_type = models.CharField(max_length=20, choices=WARD_TYPES, default='general')
    floor = models.CharField(max_length=10, blank=True)
    department = models.ForeignKey('core.Department', on_delete=models.SET_NULL, null=True)
    capacity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def occupied_beds(self):
        return self.beds.filter(status='occupied').count()

    @property
    def vacant_beds(self):
        return self.beds.filter(status='vacant').count()


class Bed(TimeStampedModel):
    STATUS_CHOICES = [
        ('vacant', 'Vacant'), ('occupied', 'Occupied'), ('maintenance', 'Maintenance'),
    ]

    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds')
    bed_number = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='vacant', db_index=True)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        unique_together = ['ward', 'bed_number']
        ordering = ['ward', 'bed_number']

    def __str__(self):
        return f'{self.ward.name} - Bed {self.bed_number}'


class Visit(TimeStampedModel):
    VISIT_TYPES = [('opd', 'OPD'), ('ipd', 'IPD'), ('emergency', 'Emergency')]
    STATUS_CHOICES = [
        ('open', 'Open'), ('in_progress', 'In Progress'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='visits')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='visits')
    appointment = models.ForeignKey(
        'appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True, related_name='visits'
    )
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPES, default='opd')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    visit_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-visit_date']

    def __str__(self):
        return f'{self.patient.mr_number} - {self.visit_type} @ {self.visit_date.date()}'


class OPDVisit(TimeStampedModel):
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='opd_details')
    chief_complaint = models.TextField()
    examination = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    diagnosis_code = models.CharField(max_length=20, blank=True, help_text='ICD-10 code placeholder')
    treatment_plan = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'OPD: {self.visit.patient.mr_number}'


class Admission(TimeStampedModel):
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='admissions')
    visit = models.OneToOneField(Visit, on_delete=models.CASCADE, related_name='admission')
    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='admissions')
    admitting_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='admissions'
    )
    admission_date = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()
    expected_discharge = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_active and self.bed.status != 'occupied':
            self.bed.status = 'occupied'
            self.bed.save(update_fields=['status'])

    def __str__(self):
        return f'Admission: {self.patient.mr_number} - {self.bed}'


class Discharge(TimeStampedModel):
    admission = models.OneToOneField(Admission, on_delete=models.CASCADE, related_name='discharge')
    discharged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    discharge_date = models.DateTimeField(auto_now_add=True)
    summary = models.TextField()
    instructions = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        admission = self.admission
        admission.is_active = False
        admission.save(update_fields=['is_active'])
        bed = admission.bed
        bed.status = 'vacant'
        bed.save(update_fields=['status'])

    def __str__(self):
        return f'Discharge: {self.admission.patient.mr_number}'


class Transfer(TimeStampedModel):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='transfers')
    from_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='transfers_from')
    to_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='transfers_to')
    transferred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason = models.TextField(blank=True)
    transfer_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.from_bed.status = 'vacant'
        self.from_bed.save(update_fields=['status'])
        self.to_bed.status = 'occupied'
        self.to_bed.save(update_fields=['status'])
        self.admission.bed = self.to_bed
        self.admission.save(update_fields=['bed'])

    def __str__(self):
        return f'Transfer: {self.admission.patient.mr_number}'


class NursingNote(TimeStampedModel):
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='nursing_notes')
    nurse = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.TextField()
    vitals_summary = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Nursing note: {self.admission.patient.mr_number}'


class Prescription(TimeStampedModel):
    STATUS_CHOICES = [('active', 'Active'), ('dispensed', 'Dispensed'), ('cancelled', 'Cancelled')]

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Rx: {self.visit.patient.mr_number} by Dr.{self.doctor}'


class PrescriptionItem(TimeStampedModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    drug_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    instructions = models.TextField(blank=True)
    is_dispensed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.drug_name} - {self.dosage}'


class LabOrder(TimeStampedModel):
    STATUS_CHOICES = [
        ('ordered', 'Ordered'), ('collected', 'Sample Collected'),
        ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ]

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='lab_orders')
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    test_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ordered')
    notes = models.TextField(blank=True)
    lab_request = models.ForeignKey(
        'laboratory.LabTestRequest', on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f'Lab order: {self.test_name} for {self.visit.patient.mr_number}'


class RadiologyOrder(TimeStampedModel):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='radiology_orders')
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    study_name = models.CharField(max_length=200)
    body_part = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, default='ordered')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Radiology: {self.study_name} for {self.visit.patient.mr_number}'


class Referral(TimeStampedModel):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='referrals')
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='referrals_made'
    )
    referred_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='referrals_received'
    )
    specialty = models.CharField(max_length=100)
    reason = models.TextField()
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f'Referral: {self.visit.patient.mr_number} to {self.specialty}'


class ProcedureNote(TimeStampedModel):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='procedure_notes')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    procedure_name = models.CharField(max_length=200)
    notes = models.TextField()
    outcome = models.TextField(blank=True)

    def __str__(self):
        return f'{self.procedure_name} - {self.visit.patient.mr_number}'


class Diagnosis(TimeStampedModel):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='diagnoses')
    icd10_code = models.CharField(max_length=20, blank=True)
    description = models.CharField(max_length=300)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Diagnoses'

    def __str__(self):
        return f'{self.icd10_code} - {self.description}'
