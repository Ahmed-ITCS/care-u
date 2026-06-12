from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from apps.pharmacy.models import DrugBatch, StockMovement, Dispense, DispenseItem


def get_fifo_batch(drug, quantity_needed):
    batches = DrugBatch.objects.filter(
        drug=drug, quantity__gt=0, expiry_date__gt=timezone.now().date()
    ).order_by('expiry_date')
    allocations = []
    remaining = quantity_needed
    for batch in batches:
        if remaining <= 0:
            break
        take = min(batch.quantity, remaining)
        allocations.append((batch, take))
        remaining -= take
    if remaining > 0:
        raise ValueError(f'Insufficient stock for {drug.generic_name}')
    return allocations


@transaction.atomic
def dispense_prescription(dispense, user):
    prescription = dispense.prescription
    total = Decimal('0')

    for item in prescription.items.filter(is_dispensed=False):
        drug = None
        from apps.pharmacy.models import Drug
        drug = Drug.objects.filter(generic_name__iexact=item.drug_name).first()
        if not drug:
            continue

        allocations = get_fifo_batch(drug, item.quantity)
        for batch, qty in allocations:
            DispenseItem.objects.create(
                dispense=dispense,
                prescription_item=item,
                drug=drug,
                batch=batch,
                quantity=qty,
                unit_price=drug.unit_price,
            )
            batch.quantity -= qty
            batch.save(update_fields=['quantity'])
            StockMovement.objects.create(
                drug=drug, batch=batch, movement_type='out',
                quantity=qty, reference=f'Dispense #{dispense.id}',
                performed_by=user,
            )
            total += drug.unit_price * qty

        item.is_dispensed = True
        item.save(update_fields=['is_dispensed'])

    dispense.status = 'dispensed'
    dispense.total_amount = total
    dispense.dispensed_by = user
    dispense.save()
    prescription.status = 'dispensed'
    prescription.save(update_fields=['status'])
    return dispense


@transaction.atomic
def receive_purchase_order(po, user):
    from apps.pharmacy.models import PurchaseOrder
    total = Decimal('0')
    for item in po.items.all():
        batch, _ = DrugBatch.objects.get_or_create(
            drug=item.drug,
            batch_number=item.batch_number or f'BATCH-{po.po_number}-{item.id}',
            defaults={
                'expiry_date': item.expiry_date or timezone.now().date().replace(year=timezone.now().year + 2),
                'quantity': 0,
                'purchase_price': item.unit_price,
                'supplier': po.supplier,
            },
        )
        batch.quantity += item.quantity
        batch.save(update_fields=['quantity'])
        StockMovement.objects.create(
            drug=item.drug, batch=batch, movement_type='in',
            quantity=item.quantity, reference=po.po_number, performed_by=user,
        )
        total += item.line_total

    po.status = 'received'
    po.total_amount = total
    po.save(update_fields=['status', 'total_amount'])
