from decimal import Decimal
from django.db import transaction

from apps.billing.models import Invoice, InvoiceItem, Payment, ServiceCatalog, ServicePrice, LedgerEntry


def get_service_price(service_code):
    service = ServiceCatalog.objects.filter(code=service_code, is_active=True).first()
    if not service:
        return Decimal('0')
    price = service.prices.filter(is_current=True).first()
    return price.price if price else Decimal('0')


@transaction.atomic
def create_invoice_from_visit(visit_id, user):
    from apps.clinical.models import Visit
    visit = Visit.objects.select_related('patient', 'doctor').get(pk=visit_id)

    invoice = Invoice.objects.create(
        patient=visit.patient,
        visit=visit,
        created_by=user,
        status='pending',
    )

    consultation_fee = Decimal('2000')
    if visit.doctor and hasattr(visit.doctor, 'doctor_profile'):
        consultation_fee = visit.doctor.doctor_profile.consultation_fee

    InvoiceItem.objects.create(
        invoice=invoice,
        description=f'Consultation - Dr. {visit.doctor.get_full_name() if visit.doctor else "N/A"}',
        quantity=1,
        unit_price=consultation_fee,
    )

    for lab_order in visit.lab_orders.all():
        InvoiceItem.objects.create(
            invoice=invoice,
            description=f'Lab: {lab_order.test_name}',
            quantity=1,
            unit_price=Decimal('500'),
        )

    invoice.recalculate()

    LedgerEntry.objects.create(
        entry_type='credit',
        category='revenue',
        amount=invoice.total_amount,
        description=f'Invoice {invoice.invoice_number}',
        reference=invoice.invoice_number,
        invoice=invoice,
        created_by=user,
    )

    return invoice


@transaction.atomic
def record_payment(invoice, amount, method, user, transaction_id=''):
    payment = Payment.objects.create(
        invoice=invoice,
        amount=amount,
        method=method,
        status='completed',
        transaction_id=transaction_id,
        received_by=user,
    )

    LedgerEntry.objects.create(
        entry_type='debit',
        category='revenue',
        amount=amount,
        description=f'Payment for {invoice.invoice_number}',
        reference=payment.transaction_id or str(payment.id),
        invoice=invoice,
        created_by=user,
    )

    return payment
