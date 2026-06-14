import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.management import call_command

from apps.users.models import Role

User = get_user_model()

TEST_SUBDOMAIN = 'test-hospital'
TEST_SCHEMA = 'test_hospital'


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Migrate database before tests."""
    from django.conf import settings
    from apps.tenants.sqlite_compat import run_migrations

    with django_db_blocker.unblock():
        if getattr(settings, 'USE_SQLITE', False):
            run_migrations()
        else:
            connection.set_schema_to_public()
            call_command('migrate_schemas', '--shared', interactive=False, verbosity=0)


@pytest.fixture
def test_tenant(db):
    """Isolated hospital tenant for ERP tests."""
    from django.conf import settings
    from apps.tenants.models import Hospital
    from apps.tenants.services import _ensure_tenant_domains

    if getattr(settings, 'USE_SQLITE', False):
        hospital, created = Hospital.objects.get_or_create(
            schema_name=TEST_SCHEMA,
            defaults={
                'name': 'Test Hospital',
                'subdomain': TEST_SUBDOMAIN,
                'email': 'test@hospital.com',
                'status': 'active',
            },
        )
        _ensure_tenant_domains(hospital)
        return hospital

    connection.set_schema_to_public()
    hospital, created = Hospital.objects.get_or_create(
        schema_name=TEST_SCHEMA,
        defaults={
            'name': 'Test Hospital',
            'subdomain': TEST_SUBDOMAIN,
            'email': 'test@hospital.com',
            'status': 'active',
        },
    )
    _ensure_tenant_domains(hospital)
    if created:
        call_command('migrate_schemas', schema_name=TEST_SCHEMA, interactive=False, verbosity=0)
    return hospital


@pytest.fixture(autouse=True)
def tenant_schema(test_tenant):
    """Run each test inside the test hospital schema (PostgreSQL) or shared DB (SQLite)."""
    from django.conf import settings

    if getattr(settings, 'USE_SQLITE', False):
        yield
        return
    connection.set_tenant(test_tenant)
    yield
    connection.set_schema_to_public()


@pytest.fixture
def tenant_prefix(test_tenant):
    return f'/h/{test_tenant.subdomain}'


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='testadmin', password='testpass123',
        role=Role.ADMIN, email='admin@test.com', is_staff=True, is_superuser=True,
    )


@pytest.fixture
def doctor_user(db):
    user = User.objects.create_user(
        username='testdoctor', password='testpass123',
        role=Role.DOCTOR, email='doctor@test.com', first_name='Test', last_name='Doctor',
    )
    from apps.users.models import DoctorProfile
    DoctorProfile.objects.create(
        user=user, specialty='General', license_number='TEST-001', consultation_fee=2000
    )
    return user


@pytest.fixture
def receptionist_user(db):
    return User.objects.create_user(
        username='testreception', password='testpass123',
        role=Role.RECEPTIONIST, email='reception@test.com',
    )
