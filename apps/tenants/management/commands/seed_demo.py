"""
Seed a full demo environment — public schema + demo hospital tenant.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --subdomain khawar
    python manage.py seed_demo --tenant-only --subdomain khawar
"""
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from datetime import time
from apps.tenants.sqlite_compat import tenant_schema_context

from apps.tenants.models import Hospital
from apps.tenants.services import create_hospital_tenant

User = get_user_model()

DEMO_PATIENTS = [
    ('35201-1234567-1', 'Ahmed', 'Hassan', '03001234567', 'M'),
    ('35201-2345678-1', 'Fatima', 'Khan', '03009876543', 'F'),
    ('35201-3456789-1', 'Ali', 'Raza', '03005551234', 'M'),
    ('35201-4567890-1', 'Sana', 'Malik', '03006667890', 'F'),
    ('35201-5678901-1', 'Usman', 'Sheikh', '03004443322', 'M'),
]


class Command(BaseCommand):
    help = 'Seed demo data: plans, platform admin, hospital, staff, catalog, patients'

    def add_arguments(self, parser):
        parser.add_argument(
            '--subdomain', default='gph-islamabad',
            help='Demo hospital subdomain (default: gph-islamabad)',
        )
        parser.add_argument(
            '--tenant-only', action='store_true',
            help='Only seed tenant data for an existing hospital',
        )
        parser.add_argument(
            '--migrate', action='store_true',
            help='Run migrate_schemas before seeding',
        )

    def handle(self, *args, **options):
        subdomain = options['subdomain'].lower().strip()

        if options['migrate']:
            from apps.tenants.sqlite_compat import run_migrations
            run_migrations(self.stdout)

        if not options['tenant_only']:
            self._seed_public()

        hospital = self._ensure_hospital(subdomain, options['tenant_only'])
        self._seed_tenant(hospital)
        self._print_summary(hospital)

    def _seed_public(self):
        self.stdout.write('Seeding public schema…')
        call_command('setup_public_tenant', verbosity=0)
        call_command('seed_plans', verbosity=0)
        call_command(
            'create_platform_admin',
            username='superadmin',
            email='admin@care-u.com',
            password='superadmin123',
            verbosity=0,
        )

    def _ensure_hospital(self, subdomain, tenant_only):
        hospital = Hospital.objects.filter(subdomain=subdomain).first()
        if hospital:
            self.stdout.write(f'Using existing hospital: {hospital.name} ({subdomain})')
            return hospital

        if tenant_only:
            self.stderr.write(self.style.ERROR(f'Hospital "{subdomain}" not found. Omit --tenant-only to create it.'))
            raise SystemExit(1)

        self.stdout.write(f'Creating demo hospital: {subdomain}…')
        hospital, _ = create_hospital_tenant({
            'hospital_name': 'General Practice Hospital Islamabad',
            'subdomain': subdomain,
            'admin_email': 'admin@gph.com.pk',
            'admin_name': 'Hospital Admin',
            'admin_username': 'admin',
            'admin_password': 'admin123',
            'address': 'F-8 Markaz, Islamabad',
            'base_domain': settings.BASE_DOMAIN,
        }, approve=True)
        return hospital

    def _seed_tenant(self, hospital):
        self.stdout.write(f'Seeding tenant schema: {hospital.schema_name}…')
        with tenant_schema_context(hospital.schema_name):
            call_command('seed_hospital_data', verbosity=0)
            call_command('seed_roles', verbosity=0)
            self._seed_patients()
            self._seed_doctor_schedules()
            self._seed_appointments()
            self._seed_billing()

        call_command('sync_user_index', verbosity=0)

    def _seed_patients(self):
        from apps.patients.models import Patient
        from apps.users.models import Role

        receptionist = User.objects.filter(role=Role.RECEPTIONIST).first()
        if not receptionist:
            receptionist = User.objects.filter(role=Role.ADMIN).first()

        created = 0
        for cnic, first, last, phone, gender in DEMO_PATIENTS:
            _, was_created = Patient.objects.get_or_create(
                cnic=cnic,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'phone': phone,
                    'gender': gender,
                    'city': 'Islamabad',
                    'registered_by': receptionist,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(f'  Patients: {created} created, {Patient.objects.count()} total')

    def _seed_doctor_schedules(self):
        from apps.appointments.models import DoctorSchedule
        from apps.users.models import Role

        doctor = User.objects.filter(role=Role.DOCTOR).first()
        if not doctor:
            return

        profile = getattr(doctor, 'doctor_profile', None)
        if profile and not profile.is_on_duty:
            profile.is_on_duty = True
            profile.save(update_fields=['is_on_duty', 'updated_at'])

        slots = [
            (0, time(9, 0), time(13, 0)),
            (0, time(14, 0), time(17, 0)),
            (1, time(9, 0), time(17, 0)),
            (2, time(9, 0), time(17, 0)),
            (3, time(9, 0), time(17, 0)),
            (4, time(9, 0), time(13, 0)),
        ]
        created = 0
        for day, start, end in slots:
            _, was_created = DoctorSchedule.objects.get_or_create(
                doctor=doctor,
                day_of_week=day,
                start_time=start,
                defaults={'end_time': end, 'slot_duration': 15, 'is_active': True},
            )
            if was_created:
                created += 1
        self.stdout.write(f'  Doctor schedules: {created} created, {DoctorSchedule.objects.filter(doctor=doctor).count()} total')

    def _seed_appointments(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.appointments.models import Appointment, AppointmentType
        from apps.patients.models import Patient
        from apps.users.models import Role

        doctor = User.objects.filter(role=Role.DOCTOR).first()
        receptionist = User.objects.filter(role=Role.RECEPTIONIST).first()
        appt_type = AppointmentType.objects.filter(code='OPD').first()
        patients = list(Patient.objects.all()[:3])
        if not (doctor and receptionist and appt_type and patients):
            return

        today = timezone.now().date()
        slots = [time(10, 0), time(11, 0), time(14, 30)]
        created = 0
        for i, patient in enumerate(patients):
            appt_date = today + timedelta(days=i)
            appt_time = slots[i % len(slots)]
            _, was_created = Appointment.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                scheduled_date=appt_date,
                scheduled_time=appt_time,
                defaults={
                    'appointment_type': appt_type,
                    'status': 'scheduled',
                    'source': 'walk_in',
                    'booked_by': receptionist,
                    'reason': 'Routine checkup',
                },
            )
            if was_created:
                created += 1
        self.stdout.write(f'  Appointments: {created} created, {Appointment.objects.count()} total')

    def _seed_billing(self):
        from apps.billing.models import Invoice
        from apps.billing.services import create_invoice_from_visit, record_payment
        from apps.clinical.models import Visit
        from apps.patients.models import Patient
        from apps.users.models import Role

        doctor = User.objects.filter(role=Role.DOCTOR).first()
        receptionist = User.objects.filter(role=Role.RECEPTIONIST).first()
        patients = list(Patient.objects.all()[:3])
        if not (doctor and receptionist and patients):
            return

        created = 0
        for patient in patients:
            visit, visit_created = Visit.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                visit_type='opd',
                defaults={'status': 'completed', 'notes': 'General consultation'},
            )
            if not Invoice.objects.filter(visit=visit).exists():
                invoice = create_invoice_from_visit(visit.id, receptionist)
                created += 1
                if patient == patients[0]:
                    record_payment(invoice, invoice.total_amount, 'cash', receptionist)
                elif patient == patients[1]:
                    record_payment(invoice, invoice.total_amount / 2, 'cash', receptionist)

        self.stdout.write(f'  Invoices: {created} created, {Invoice.objects.count()} total')

    def _print_summary(self, hospital):
        from django.conf import settings
        host = settings.BASE_DOMAIN if settings.BASE_DOMAIN != 'localhost' else 'localhost:8000'
        scheme = 'https' if getattr(settings, 'USE_HTTPS', False) else 'http'
        prefix = f'/h/{hospital.subdomain}'
        self.stdout.write(self.style.SUCCESS('\nDemo environment ready!\n'))
        self.stdout.write(f'Platform admin:  {scheme}://{host}/platform/login/')
        self.stdout.write('                 superadmin / superadmin123\n')
        self.stdout.write(f'Hospital ERP:    {scheme}://{host}{prefix}/')
        self.stdout.write('                 admin / admin123')
        self.stdout.write('                 doctor1 / doctor123')
        self.stdout.write('                 reception1 / reception123\n')
        self.stdout.write(f'Unified login:   {scheme}://{host}/login/')
        self.stdout.write('                 (username or email for any hospital user)\n')
