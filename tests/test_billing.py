import pytest
from decimal import Decimal


@pytest.mark.django_db
class TestBillingFlow:
    def test_invoice_from_visit(self, receptionist_user, doctor_user):
        from apps.patients.models import Patient
        from apps.clinical.models import Visit
        from apps.billing.services import create_invoice_from_visit

        patient = Patient.objects.create(
            cnic='35202-5555555-1', first_name='Bill', last_name='Test',
            phone='03005555555', registered_by=receptionist_user,
        )
        visit = Visit.objects.create(patient=patient, doctor=doctor_user, visit_type='opd')
        invoice = create_invoice_from_visit(visit.id, receptionist_user)

        assert invoice.invoice_number.startswith('INV-')
        assert invoice.total_amount > 0
        assert invoice.items.count() >= 1

    def test_record_payment(self, receptionist_user, doctor_user):
        from apps.patients.models import Patient
        from apps.clinical.models import Visit
        from apps.billing.services import create_invoice_from_visit, record_payment

        patient = Patient.objects.create(
            cnic='35202-6666666-1', first_name='Pay', last_name='Test',
            phone='03006666666', registered_by=receptionist_user,
        )
        visit = Visit.objects.create(patient=patient, doctor=doctor_user, visit_type='opd')
        invoice = create_invoice_from_visit(visit.id, receptionist_user)
        payment = record_payment(invoice, invoice.total_amount, 'cash', receptionist_user)

        invoice.refresh_from_db()
        assert payment.status == 'completed'
        assert invoice.status == 'paid'
