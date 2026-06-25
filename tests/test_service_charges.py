import pytest
from decimal import Decimal

from apps.billing.models import ServiceCatalog, ServicePrice
from apps.billing.services import get_current_service_price, set_service_price


@pytest.mark.django_db
class TestServiceCharges:
    def test_set_service_price_creates_and_updates(self):
        service = ServiceCatalog.objects.create(
            code='TEST-CONS',
            name='Test Consultation',
            category='consultation',
        )
        set_service_price(service, Decimal('1500'))
        assert get_current_service_price(service) == Decimal('1500')
        assert ServicePrice.objects.filter(service=service, is_current=True).count() == 1

        set_service_price(service, Decimal('2000'))
        assert get_current_service_price(service) == Decimal('2000')
        assert ServicePrice.objects.filter(service=service).count() == 2
        assert ServicePrice.objects.filter(service=service, is_current=True).count() == 1

    def test_set_service_price_no_op_when_unchanged(self):
        service = ServiceCatalog.objects.create(
            code='TEST-LAB',
            name='Test Lab',
            category='lab',
        )
        set_service_price(service, Decimal('500'))
        set_service_price(service, Decimal('500'))
        assert ServicePrice.objects.filter(service=service).count() == 1

    def test_receptionist_can_view_charges_read_only(
        self, client, tenant_prefix, receptionist_user, admin_user,
    ):
        from apps.billing.models import ServiceCatalog
        from apps.billing.services import set_service_price

        service = ServiceCatalog.objects.create(
            code='VIEW-TEST', name='View Test', category='consultation',
        )
        set_service_price(service, Decimal('999'))
        client.force_login(receptionist_user)
        response = client.get(f'{tenant_prefix}/billing/charges/')
        assert response.status_code == 200
        assert b'View Test' in response.content
        assert b'Add Charge' not in response.content
        response = client.get(f'{tenant_prefix}/billing/charges/new/')
        assert response.status_code == 302
