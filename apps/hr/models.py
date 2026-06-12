from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class Shift(TimeStampedModel):
    name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.name} ({self.start_time}-{self.end_time})'


class StaffShiftAssignment(TimeStampedModel):
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shift_assignments')
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['staff', 'date', 'shift']

    def __str__(self):
        return f'{self.staff} - {self.shift} on {self.date}'


class Attendance(TimeStampedModel):
    STATUS_CHOICES = [
        ('present', 'Present'), ('absent', 'Absent'),
        ('late', 'Late'), ('half_day', 'Half Day'), ('leave', 'On Leave'),
    ]

    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['staff', 'date']
        ordering = ['-date']

    def __str__(self):
        return f'{self.staff} - {self.date} ({self.status})'


class LeaveRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled'),
    ]
    LEAVE_TYPES = [
        ('annual', 'Annual'), ('sick', 'Sick'), ('emergency', 'Emergency'), ('unpaid', 'Unpaid'),
    ]

    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='approved_leaves'
    )
    approval_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.staff} - {self.leave_type} ({self.start_date} to {self.end_date})'


class PayrollRun(TimeStampedModel):
    STATUS_CHOICES = [('draft', 'Draft'), ('processed', 'Processed'), ('paid', 'Paid')]

    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['month', 'year']
        ordering = ['-year', '-month']

    def __str__(self):
        return f'Payroll {self.month}/{self.year}'


class PayrollItem(TimeStampedModel):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='items')
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.net_salary = self.basic_salary + self.allowances + self.commission - self.deductions
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.staff} - PKR {self.net_salary}'


class DoctorCommission(TimeStampedModel):
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='commissions')
    invoice = models.ForeignKey('billing.Invoice', on_delete=models.CASCADE, related_name='doctor_commissions')
    procedure_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    payroll_item = models.ForeignKey(PayrollItem, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.commission_amount = self.procedure_amount * self.commission_rate / 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Commission: Dr.{self.doctor} - PKR {self.commission_amount}'
