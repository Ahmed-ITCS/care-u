from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class TestCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Test categories'

    def __str__(self):
        return self.name


class TestCatalog(TimeStampedModel):
    category = models.ForeignKey(TestCategory, on_delete=models.CASCADE, related_name='tests')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    sample_type = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    turnaround_hours = models.PositiveIntegerField(default=24)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f'{self.code} - {self.name}'


class LabTestRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ('requested', 'Requested'), ('collected', 'Sample Collected'),
        ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled'),
    ]

    request_number = models.CharField(max_length=20, unique=True, db_index=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='lab_requests')
    visit = models.ForeignKey('clinical.Visit', on_delete=models.SET_NULL, null=True, blank=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested', db_index=True)
    priority = models.CharField(max_length=10, default='normal')
    clinical_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.request_number:
            from django.utils import timezone
            year = timezone.now().year
            count = LabTestRequest.objects.filter(
                request_number__startswith=f'LAB-{year}'
            ).count() + 1
            self.request_number = f'LAB-{year}-{count:05d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.request_number} - {self.patient.mr_number}'


class LabTestRequestItem(TimeStampedModel):
    request = models.ForeignKey(LabTestRequest, on_delete=models.CASCADE, related_name='items')
    test = models.ForeignKey(TestCatalog, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f'{self.request.request_number} - {self.test.name}'


class SampleCollection(TimeStampedModel):
    request_item = models.OneToOneField(
        LabTestRequestItem, on_delete=models.CASCADE, related_name='sample'
    )
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    sample_id = models.CharField(max_length=50, blank=True)
    collection_notes = models.TextField(blank=True)

    def __str__(self):
        return f'Sample for {self.request_item.test.name}'


class TestResult(TimeStampedModel):
    request_item = models.OneToOneField(
        LabTestRequestItem, on_delete=models.CASCADE, related_name='result'
    )
    result_value = models.TextField()
    unit = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=100, blank=True)
    is_abnormal = models.BooleanField(default=False)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='verified_results'
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Result: {self.request_item.test.name}'


class LabReport(TimeStampedModel):
    request = models.OneToOneField(LabTestRequest, on_delete=models.CASCADE, related_name='report')
    pdf_file = models.FileField(upload_to='lab/reports/', blank=True, null=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    is_final = models.BooleanField(default=False)

    def __str__(self):
        return f'Report: {self.request.request_number}'
