from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.core.models import TimeStampedModel, SoftDeleteModel, ActiveManager


class DrugCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'Drug categories'

    def __str__(self):
        return self.name


class Drug(TimeStampedModel, SoftDeleteModel):
    category = models.ForeignKey(DrugCategory, on_delete=models.SET_NULL, null=True)
    generic_name = models.CharField(max_length=200, db_index=True)
    brand_name = models.CharField(max_length=200, blank=True)
    strength = models.CharField(max_length=50, blank=True)
    form = models.CharField(max_length=50, blank=True, help_text='Tablet, Syrup, Injection, etc.')
    barcode = models.CharField(max_length=50, blank=True, help_text='Barcode placeholder')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['generic_name']

    def __str__(self):
        return f'{self.generic_name} {self.strength}'

    @property
    def total_stock(self):
        return self.batches.filter(quantity__gt=0, expiry_date__gt=timezone.now().date()).aggregate(
            total=models.Sum('quantity')
        )['total'] or 0


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class DrugBatch(TimeStampedModel):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=50)
    expiry_date = models.DateField(db_index=True)
    quantity = models.PositiveIntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ['drug', 'batch_number']
        ordering = ['expiry_date']

    def __str__(self):
        return f'{self.drug} - Batch {self.batch_number} (Qty: {self.quantity})'


class StockMovement(TimeStampedModel):
    MOVEMENT_TYPES = [
        ('in', 'Stock In'), ('out', 'Stock Out'), ('adjustment', 'Adjustment'), ('expired', 'Expired'),
    ]

    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='stock_movements')
    batch = models.ForeignKey(DrugBatch, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.PositiveIntegerField()
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f'{self.movement_type}: {self.drug} x{self.quantity}'


class PurchaseOrder(TimeStampedModel):
    STATUS_CHOICES = [
        ('draft', 'Draft'), ('ordered', 'Ordered'), ('received', 'Received'), ('cancelled', 'Cancelled'),
    ]

    po_number = models.CharField(max_length=20, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    order_date = models.DateField(default=timezone.now)
    expected_delivery = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.po_number:
            year = timezone.now().year
            count = PurchaseOrder.objects.filter(po_number__startswith=f'PO-{year}').count() + 1
            self.po_number = f'PO-{year}-{count:05d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.po_number


class PurchaseOrderItem(TimeStampedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    batch_number = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f'{self.purchase_order.po_number} - {self.drug}'


class Dispense(TimeStampedModel):
    STATUS_CHOICES = [('pending', 'Pending'), ('dispensed', 'Dispensed'), ('partial', 'Partial'), ('cancelled', 'Cancelled')]

    prescription = models.ForeignKey('clinical.Prescription', on_delete=models.CASCADE, related_name='dispenses')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='dispenses')
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Dispense: {self.patient.mr_number}'


class DispenseItem(TimeStampedModel):
    dispense = models.ForeignKey(Dispense, on_delete=models.CASCADE, related_name='items')
    prescription_item = models.ForeignKey(
        'clinical.PrescriptionItem', on_delete=models.SET_NULL, null=True, blank=True
    )
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT)
    batch = models.ForeignKey(DrugBatch, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f'{self.drug} x{self.quantity}'
