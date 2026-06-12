"""
Hospital (tenant) lifecycle services — run in public schema context.
"""
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)


def _ensure_tenant_domains(hospital, base_domain='localhost'):
    """
    Create Domain rows for tenant resolution.
    Subfolder middleware looks up domain=subdomain slug (e.g. gph-islamabad).
    Subdomain middleware looks up domain=subdomain.base_domain (e.g. gph-islamabad.localhost).
    """
    from apps.tenants.models import Domain

    subdomain = hospital.subdomain
    domain_host = f'{subdomain}.{base_domain}'

    Domain.objects.get_or_create(
        domain=subdomain,
        defaults={'tenant': hospital, 'is_primary': True},
    )
    Domain.objects.get_or_create(
        domain=domain_host,
        defaults={'tenant': hospital, 'is_primary': False},
    )


@transaction.atomic
def create_hospital_tenant(registration_data, approve=True):
    """
    Create a new hospital tenant: schema, domain, admin user, seed data.
    Called from public schema during hospital registration.
    """
    from apps.tenants.models import Hospital, SubscriptionPlan, HospitalRegistration

    subdomain = registration_data['subdomain'].lower().strip()
    schema_name = Hospital._sanitize_schema_name(subdomain)

    if Hospital.objects.filter(subdomain=subdomain).exists():
        raise ValueError(f'Subdomain "{subdomain}" is already taken.')

    trial_plan = SubscriptionPlan.objects.filter(name='trial').first()

    hospital = Hospital(
        name=registration_data['hospital_name'],
        subdomain=subdomain,
        schema_name=schema_name,
        email=registration_data['admin_email'],
        address=registration_data.get('address', ''),
        phone=registration_data.get('admin_phone', ''),
        status='active' if approve else 'pending',
        plan=trial_plan,
    )
    hospital.setup_trial(days=14)
    hospital.save()  # auto_create_schema=True creates PostgreSQL schema

    # TENANT: Domain records for routing (subfolder + subdomain)
    _ensure_tenant_domains(hospital, base_domain=registration_data.get('base_domain', 'localhost'))

    # Create tenant admin user and seed data inside the new schema
    with schema_context(hospital.schema_name):
        _setup_tenant_schema(hospital, registration_data)

    reg = HospitalRegistration.objects.create(
        hospital=hospital,
        admin_name=registration_data['admin_name'],
        admin_email=registration_data['admin_email'],
        admin_phone=registration_data.get('admin_phone', ''),
        hospital_name=registration_data['hospital_name'],
        subdomain=subdomain,
        address=registration_data.get('address', ''),
        is_processed=True,
    )

    logger.info(f'Created tenant: {hospital.name} (schema={schema_name})')
    return hospital, reg


def _setup_tenant_schema(hospital, registration_data):
    """Initialize tenant schema with admin user and default data."""
    from apps.users.models import User, Role, StaffProfile
    from apps.core.models import HospitalConfig, Department

    # Hospital branding config inside tenant schema
    HospitalConfig.objects.update_or_create(
        pk=1,
        defaults={
            'name': hospital.name,
            'address': hospital.address,
            'phone': hospital.phone,
            'email': hospital.email,
            'currency': hospital.currency,
            'tax_rate': hospital.tax_rate,
        },
    )

    # Create hospital admin user
    admin_username = registration_data.get('admin_username') or registration_data['admin_email'].split('@')[0]
    password = registration_data.get('admin_password', 'changeme123')

    user = User.objects.create_user(
        username=admin_username,
        email=registration_data['admin_email'],
        password=password,
        first_name=registration_data['admin_name'].split()[0] if registration_data['admin_name'] else '',
        last_name=' '.join(registration_data['admin_name'].split()[1:]) if registration_data['admin_name'] else '',
        role=Role.ADMIN,
        phone=registration_data.get('admin_phone', ''),
        is_verified=True,
        is_staff=True,
        is_superuser=True,
    )
    StaffProfile.objects.create(user=user, cnic='')

    from apps.tenants.auth import sync_user_to_index
    sync_user_to_index(hospital, user)

    # Default departments
    departments = [
        ('General Medicine', 'GM'),
        ('Surgery', 'SUR'),
        ('Pediatrics', 'PED'),
        ('Radiology', 'RAD'),
        ('Pathology', 'PATH'),
    ]
    for name, code in departments:
        Department.objects.get_or_create(code=code, defaults={'name': name})


def run_tenant_onboarding(hospital, onboarding_data):
    """Complete onboarding wizard — seed departments, services, inventory."""
    from django_tenants.utils import schema_context

    with schema_context(hospital.schema_name):
        from apps.core.models import Department, HospitalConfig
        from apps.core.management.commands.seed_hospital_data import Command as SeedCommand

        config = HospitalConfig.load()
        if onboarding_data.get('departments'):
            for dept in onboarding_data['departments']:
                Department.objects.get_or_create(
                    code=dept.get('code', dept['name'][:3].upper()),
                    defaults={'name': dept['name']},
                )

        if onboarding_data.get('primary_color'):
            config.name = hospital.name
            hospital.primary_color = onboarding_data['primary_color']
            hospital.save(update_fields=['primary_color'])

        # Seed test catalog, drugs, services
        SeedCommand().handle()

    hospital.onboarding_completed = True
    hospital.save(update_fields=['onboarding_completed'])


def upgrade_hospital_subscription(hospital, plan, paid_until, status='active'):
    """
    Apply or extend a hospital's SaaS subscription (platform admin action).
    Replaces manual Django shell upgrades.
    """
    hospital.plan = plan
    hospital.paid_until = paid_until
    hospital.status = status
    if status == 'active' and plan.name != 'trial':
        hospital.trial_ends = None
    hospital.save(update_fields=['plan', 'paid_until', 'status', 'trial_ends', 'updated_at'])
    logger.info('Upgraded tenant %s to plan=%s paid_until=%s', hospital.subdomain, plan.name, paid_until)
    return hospital


def extend_hospital_subscription(hospital, months=1):
    """Extend paid_until by N months from today or current expiry (whichever is later)."""
    from datetime import timedelta

    today = timezone.now().date()
    base = hospital.paid_until if hospital.paid_until and hospital.paid_until >= today else today
    hospital.paid_until = base + timedelta(days=30 * months)
    if hospital.status in ('trial', 'expired', 'suspended'):
        hospital.status = 'active'
    hospital.save(update_fields=['paid_until', 'status', 'updated_at'])
    logger.info('Extended tenant %s subscription until %s', hospital.subdomain, hospital.paid_until)
    return hospital


def get_tenant_usage_stats(hospital):
    """Aggregate usage stats for super admin dashboard."""
    from django_tenants.utils import schema_context

    stats = {'patients': 0, 'appointments': 0, 'staff': 0, 'invoices': 0}
    try:
        with schema_context(hospital.schema_name):
            from apps.patients.models import Patient
            from apps.appointments.models import Appointment
            from apps.users.models import User
            from apps.billing.models import Invoice

            stats['patients'] = Patient.objects.count()
            stats['appointments'] = Appointment.objects.count()
            stats['staff'] = User.objects.exclude(role='patient').count()
            stats['invoices'] = Invoice.objects.count()
    except Exception as e:
        logger.warning(f'Could not fetch stats for {hospital.schema_name}: {e}')
    return stats
