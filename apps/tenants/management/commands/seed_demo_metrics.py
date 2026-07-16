"""
Seed today's operational demo data so the executive dashboard KPIs are populated.

Usage:
    python manage.py seed_demo_metrics
    python manage.py seed_demo_metrics --subdomain gph-islamabad

Safe to run once per tenant. If today's data already exists it will skip.
"""
from datetime import time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tenants.models import Hospital
from apps.tenants.sqlite_compat import tenant_schema_context
from apps.users.models import Role


class Command(BaseCommand):
    help = 'Seed today-dated operational demo data (patients, queue, labs, beds, pharmacy, billing).'

    def add_arguments(self, parser):
        parser.add_argument('--subdomain', default='gph-islamabad')

    def handle(self, *args, **options):
        subdomain = options['subdomain'].lower().strip()
        hospital = Hospital.objects.filter(subdomain=subdomain).first()
        if not hospital:
            self.stderr.write(self.style.ERROR(f'Hospital "{subdomain}" not found.'))
            raise SystemExit(1)

        today = timezone.now().date()
        with tenant_schema_context(hospital.schema_name):
            from apps.patients.models import Patient
            if Patient.objects.filter(created_at__date=today).exists():
                self.stdout.write(self.style.WARNING(
                    'Today\'s demo data already present — skipping.'
                ))
                return

            self._seed(hospital, today)
            self._print_summary(today)

    def _seed(self, hospital, today):
        from apps.users.models import User
        from apps.patients.models import Patient
        from apps.appointments.models import (
            Appointment, AppointmentType, QueueEntry,
        )
        from apps.clinical.models import Visit, Prescription, Ward, Bed
        from apps.laboratory.models import LabTestRequest
        from apps.pharmacy.models import Dispense, Drug, DrugBatch, Supplier
        from apps.billing.models import Invoice
        from apps.billing.services import create_invoice_from_visit, record_payment

        doctor = User.objects.filter(role=Role.DOCTOR).first()
        receptionist = User.objects.filter(role=Role.RECEPTIONIST).first()
        pharmacist = User.objects.filter(role=Role.PHARMACIST).first()
        lab_tech = User.objects.filter(role=Role.LAB_TECH).first()
        admin = User.objects.filter(role=Role.ADMIN).first()
        booked_by = receptionist or admin

        male_names = ['Bilal', 'Hassan', 'Imran', 'Kashif', 'Omer', 'Rehan', 'Tariq', 'Waqas']
        female_names = ['Ayesha', 'Madiha', 'Nabila', 'Rabia', 'Sadia', 'Zainab']
        last_names = ['Ahmed', 'Bhatti', 'Chaudhry', 'Farooq', 'Gill', 'Hussain', 'Javed', 'Khan']

        def new_patient(i):
            first = (male_names + female_names)[i % (len(male_names) + len(female_names))]
            last = last_names[i % len(last_names)]
            gender = 'M' if i % 2 == 0 else 'F'
            cnic = f'35201-{1000000 + i}-{(i % 9) + 1}'
            p, _ = Patient.objects.get_or_create(
                cnic=cnic,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'phone': f'0300{1000000 + i}'[:11],
                    'gender': gender,
                    'city': 'Islamabad',
                    'registered_by': booked_by,
                },
            )
            return p

        # ── Patients registered today ──
        patients = [new_patient(i) for i in range(12)]
        self.stdout.write(f'  Patients today: {len(patients)}')

        appt_type = AppointmentType.objects.filter(code='OPD').first()
        # ── Appointments + live queue today ──
        slots = [time(9, 0), time(9, 30), time(10, 0), time(10, 30),
                 time(11, 0), time(11, 30), time(14, 0), time(15, 0)]
        queue_waiting = 0
        for i, patient in enumerate(patients[:8]):
            appt, _ = Appointment.objects.get_or_create(
                patient=patient, doctor=doctor,
                scheduled_date=today, scheduled_time=slots[i],
                defaults={
                    'appointment_type': appt_type,
                    'status': 'scheduled',
                    'source': 'walk_in',
                    'booked_by': booked_by,
                    'reason': 'General consultation',
                },
            )
            if i < 4:  # first four are currently waiting
                QueueEntry.objects.get_or_create(
                    appointment=appt,
                    defaults={'token_number': i + 1, 'status': 'waiting', 'priority': 0},
                )
                queue_waiting += 1
            elif i < 6:  # a couple already in consultation / completed
                QueueEntry.objects.get_or_create(
                    appointment=appt,
                    defaults={'token_number': i + 1, 'status': 'completed', 'priority': 0},
                )
        self.stdout.write(f'  Appointments today: 8 | Queue waiting: {queue_waiting}')

        # ── Pending lab reports (incl. urgent/STAT) ──
        pending_lab = 0
        for i, patient in enumerate(patients[:6]):
            priority = 'stat' if i == 0 else ('urgent' if i == 1 else 'normal')
            status = ['requested', 'collected', 'in_progress'][i % 3]
            LabTestRequest.objects.get_or_create(
                patient=patient, requested_by=doctor,
                defaults={'status': status, 'priority': priority},
            )
            pending_lab += 1
        self.stdout.write(f'  Pending lab reports: {pending_lab}')

        # ── Bed occupancy ──
        occupied = 0
        for bed in Bed.objects.all()[:3]:
            bed.status = 'occupied'
            bed.save(update_fields=['status'])
            occupied += 1
        self.stdout.write(f'  Beds occupied: {occupied}/{Bed.objects.count()}')

        # ── Pharmacy sales + revenue today ──
        dispenses = 0
        revenue_invoices = 0
        drug = Drug.objects.first()
        for i, patient in enumerate(patients[6:9]):
            visit, _ = Visit.objects.get_or_create(
                patient=patient, doctor=doctor, visit_type='opd',
                defaults={'status': 'completed', 'notes': 'Consultation'},
            )
            rx = Prescription.objects.create(visit=visit, doctor=doctor, status='dispensed')
            if drug:
                Dispense.objects.create(
                    prescription=rx, patient=patient,
                    dispensed_by=pharmacist, status='dispensed',
                    total_amount=Decimal(str(450 + i * 150)),
                )
                dispenses += 1
            invoice = create_invoice_from_visit(visit.id, booked_by)
            record_payment(invoice, invoice.total_amount, 'cash', booked_by)
            revenue_invoices += 1
        self.stdout.write(f'  Pharmacy dispenses today: {dispenses} | Paid invoices today: {revenue_invoices}')

        # ── Critical alerts components ──
        # overdue invoice
        overdue_patient = patients[9]
        v = Visit.objects.create(patient=overdue_patient, doctor=doctor, visit_type='opd', status='completed')
        inv = create_invoice_from_visit(v.id, booked_by)
        inv.due_date = today - timedelta(days=15)
        inv.status = 'pending'
        inv.save(update_fields=['due_date', 'status'])

        # low-stock + expiring-soon batches
        supplier = Supplier.objects.first() or Supplier.objects.create(name='Demo Supplier', phone='+92-51-0000000')
        if drug:
            DrugBatch.objects.create(
                drug=drug, batch_number='LOW-001', supplier=supplier,
                expiry_date=today + timedelta(days=300), quantity=4,
            )
            DrugBatch.objects.create(
                drug=drug, batch_number='EXP-001', supplier=supplier,
                expiry_date=today + timedelta(days=12), quantity=40,
            )
        self.stdout.write('  Critical alerts: overdue invoice + low stock + expiring batch + urgent labs')

    def _print_summary(self, today):
        from django.db.models import Sum
        from apps.patients.models import Patient
        from apps.appointments.models import QueueEntry
        from apps.laboratory.models import LabTestRequest
        from apps.billing.models import Payment

        revenue = Payment.objects.filter(
            created_at__date=today, status='completed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        self.stdout.write(self.style.SUCCESS('\nToday\'s demo metrics seeded!\n'))
        self.stdout.write(f'  Patients today:   {Patient.objects.filter(created_at__date=today).count()}')
        self.stdout.write(f'  Queue waiting:    {QueueEntry.objects.filter(status="waiting", created_at__date=today).count()}')
        self.stdout.write(f'  Revenue today:    PKR {revenue}')
        self.stdout.write(f'  Pending labs:     {LabTestRequest.objects.filter(status__in=["requested","collected","in_progress"]).count()}')
        self.stdout.write('\nRefresh the dashboard to see the populated KPIs.')
