from django.core.management.base import BaseCommand
from decimal import Decimal

from apps.core.models import HospitalConfig, Department
from apps.appointments.models import AppointmentType
from apps.laboratory.models import TestCategory, TestCatalog
from apps.pharmacy.models import DrugCategory, Drug, Supplier, DrugBatch
from apps.billing.models import ServiceCatalog, ServicePrice
from apps.clinical.models import Ward, Bed


class Command(BaseCommand):
    help = 'Seed hospital data: departments, tests, drugs, services, wards'

    def handle(self, *args, **options):
        HospitalConfig.load()

        appt_types = [
            ('OPD', 'OPD', 15, '#1E40AF'),
            ('Follow-up', 'FU', 10, '#059669'),
            ('Emergency', 'EMRG', 30, '#EF4444'),
            ('Procedure', 'PROC', 60, '#F59E0B'),
        ]
        for name, code, dur, color in appt_types:
            AppointmentType.objects.get_or_create(code=code, defaults={'name': name, 'duration_minutes': dur, 'color': color})

        categories = ['Blood Tests', 'Urine Tests', 'Radiology']
        for cat_name in categories:
            cat, _ = TestCategory.objects.get_or_create(name=cat_name)

        tests = [
            ('Blood Tests', 'CBC', 'Complete Blood Count', 800),
            ('Blood Tests', 'LFT', 'Liver Function Test', 1200),
            ('Blood Tests', 'RFT', 'Renal Function Test', 1000),
            ('Urine Tests', 'URINE', 'Urine R/E', 500),
            ('Radiology', 'XRAY', 'X-Ray Chest', 1500),
        ]
        for cat_name, code, name, price in tests:
            cat = TestCategory.objects.get(name=cat_name)
            TestCatalog.objects.get_or_create(code=code, defaults={'category': cat, 'name': name, 'price': price})

        services = [
            ('CONS', 'General Consultation', 'consultation', 2000),
            ('LAB', 'Lab Test (General)', 'lab', 500),
            ('XRAY-SVC', 'X-Ray Service', 'radiology', 1500),
            ('ROOM-GEN', 'General Ward (Daily)', 'room', 3000),
            ('PROC-GEN', 'Minor Procedure', 'procedure', 5000),
        ]
        for code, name, cat, price in services:
            svc, created = ServiceCatalog.objects.get_or_create(
                code=code, defaults={'name': name, 'category': cat}
            )
            if created or not svc.prices.filter(is_current=True).exists():
                ServicePrice.objects.create(service=svc, price=Decimal(str(price)))

        drug_cat, _ = DrugCategory.objects.get_or_create(name='General')
        drugs = [
            ('Paracetamol', 'Panadol', '500mg', 'Tablet', 5),
            ('Amoxicillin', 'Augmentin', '625mg', 'Tablet', 25),
            ('Omeprazole', 'Risek', '20mg', 'Capsule', 15),
            ('Metformin', 'Glucophage', '500mg', 'Tablet', 8),
        ]
        supplier, _ = Supplier.objects.get_or_create(name='Default Supplier', defaults={'phone': '+92-51-0000000'})
        for generic, brand, strength, form, price in drugs:
            drug, _ = Drug.objects.get_or_create(
                generic_name=generic, strength=strength,
                defaults={'category': drug_cat, 'brand_name': brand, 'form': form, 'unit_price': price}
            )
            DrugBatch.objects.get_or_create(
                drug=drug, batch_number='INIT-001',
                defaults={'expiry_date': '2027-12-31', 'quantity': 100, 'supplier': supplier}
            )

        ward, _ = Ward.objects.get_or_create(name='General Ward A', defaults={'ward_type': 'general', 'floor': '3', 'capacity': 10})
        for i in range(1, 6):
            Bed.objects.get_or_create(ward=ward, bed_number=str(i), defaults={'status': 'vacant', 'daily_rate': 3000})

        self.stdout.write(self.style.SUCCESS('Hospital data seeded successfully'))
