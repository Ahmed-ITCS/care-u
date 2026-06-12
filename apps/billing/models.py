from django.db import models
from django.conf import settings
from django.utils import timezone
from auditlog.registry import auditlog

from apps.core.models import TimeStampedModel


class ServiceCatalog(TimeStampedModel):
    CATEGORY_CHOICES = [
        ('consultation', 'Consultation'), ('procedure', 'Procedure'),
        ('lab', 'Laboratory'), ('radiology', 'Radiology'),
        ('room', 'Room Charge'), ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.code} - {self.name}'


class ServicePrice(TimeStampedModel):
    service = models.ForeignKey(ServiceCatalog, on_delete=models.CASCADE, related_name='prices')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField(default=timezone.now)
    effective_until = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ['-effective_from']

    def __str__(self):
        return f'{self.service.name}: PKR {self.price}'


class Invoice(TimeStampedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('pending', 'Pending'), ('partial', 'Partially Paid'),
        ('paid', 'Paid'), ('cancelled', 'Cancelled'), ('refunded', 'Refunded'),
    ]

    invoice_number = models.CharField(max_length=20, unique=True, db_index=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='invoices')
    visit = models.ForeignKey('clinical.Visit', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            year = timezone.now().year
            count = Invoice.objects.filter(invoice_number__startswith=f'INV-{year}').count() + 1
            self.invoice_number = f'INV-{year}-{count:05d}'
        super().save(*args, **kwargs)

    def recalculate(self):
        self.subtotal = sum(item.line_total for item in self.items.all())
        self.total_amount = self.subtotal + self.tax_amount - self.discount
        self.save(update_fields=['subtotal', 'total_amount'])

    def __str__(self):
        return f'{self.invoice_number} - {self.patient.mr_number}'


class InvoiceItem(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(ServiceCatalog, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=300)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f'{self.description} x{self.quantity}'


class Payment(TimeStampedModel):
    STATUS_CHOICES = [('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('refunded', 'Refunded')]
    METHOD_CHOICES = [
        ('cash', 'Cash'), ('card', 'Card'), ('online', 'Online'),
        ('stripe', 'Stripe'), ('paypal', 'PayPal'), ('insurance', 'Insurance'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='cash')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    transaction_id = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == 'completed':
            invoice = self.invoice
            invoice.amount_paid = invoice.payments.filter(status='completed').aggregate(
                total=models.Sum('amount')
            )['total'] or 0
            if invoice.amount_paid >= invoice.total_amount:
                invoice.status = 'paid'
            elif invoice.amount_paid > 0:
                invoice.status = 'partial'
            invoice.save(update_fields=['amount_paid', 'status'])

    def __str__(self):
        return f'Payment PKR {self.amount} for {self.invoice.invoice_number}'


class InsuranceClaim(TimeStampedModel):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('paid', 'Paid'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='insurance_claims')
    policy = models.ForeignKey('patients.PatientInsurance', on_delete=models.SET_NULL, null=True)
    claim_number = models.CharField(max_length=50, blank=True)
    claimed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    submitted_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Claim {self.claim_number or self.pk} - {self.invoice.invoice_number}'


class Refund(TimeStampedModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'Refund PKR {self.amount}'


class LedgerEntry(TimeStampedModel):
    ENTRY_TYPES = [('debit', 'Debit'), ('credit', 'Credit')]
    CATEGORY_CHOICES = [
        ('revenue', 'Revenue'), ('expense', 'Expense'), ('refund', 'Refund'), ('adjustment', 'Adjustment'),
    ]

    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=300)
    reference = models.CharField(max_length=100, blank=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = 'Ledger entries'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.entry_type} PKR {self.amount} - {self.description}'


auditlog.register(Invoice)
auditlog.register(Payment)
