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
