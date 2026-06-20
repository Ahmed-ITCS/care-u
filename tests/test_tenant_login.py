import pytest

from apps.tenants.auth import resolve_tenant_and_authenticate, admin_email_taken
from apps.tenants.sqlite_compat import tenant_schema_context


@pytest.mark.django_db
class TestTenantLoginIsolation:
    def test_ambiguous_username_without_hospital_code(self):
        from apps.tenants.models import Hospital, TenantUserIndex
        from apps.tenants.services import create_hospital_tenant
        from django.contrib.auth import get_user_model

        User = get_user_model()

        h1, _ = create_hospital_tenant({
            'hospital_name': 'Hospital One',
            'subdomain': 'hospital-one',
            'admin_email': 'owner1@test.com',
            'admin_name': 'Owner One',
            'admin_username': 'admin',
            'admin_password': 'samepass123',
            'base_domain': 'localhost',
        }, approve=True)

        h2, _ = create_hospital_tenant({
            'hospital_name': 'Hospital Two',
            'subdomain': 'hospital-two',
            'admin_email': 'owner2@test.com',
            'admin_name': 'Owner Two',
            'admin_username': 'admin',
            'admin_password': 'samepass123',
            'base_domain': 'localhost',
        }, approve=True)

        hospital, user, error = resolve_tenant_and_authenticate('admin', 'samepass123')
        assert hospital is None
        assert error == 'ambiguous'

        hospital, user, error = resolve_tenant_and_authenticate(
            'admin', 'samepass123', hospital_subdomain='hospital-two',
        )
        assert error is None
        assert hospital.subdomain == 'hospital-two'
        assert user.username == 'admin'

    def test_email_login_picks_correct_hospital(self):
        from apps.tenants.services import create_hospital_tenant

        create_hospital_tenant({
            'hospital_name': 'Alpha Clinic',
            'subdomain': 'alpha-clinic',
            'admin_email': 'alpha@clinic.com',
            'admin_name': 'Alpha Admin',
            'admin_username': 'admin',
            'admin_password': 'pass111111',
            'base_domain': 'localhost',
        }, approve=True)

        create_hospital_tenant({
            'hospital_name': 'Beta Clinic',
            'subdomain': 'beta-clinic',
            'admin_email': 'beta@clinic.com',
            'admin_name': 'Beta Admin',
            'admin_username': 'admin',
            'admin_password': 'pass222222',
            'base_domain': 'localhost',
        }, approve=True)

        hospital, user, error = resolve_tenant_and_authenticate(
            'beta@clinic.com', 'pass222222', hospital_subdomain='beta-clinic',
        )
        assert error is None
        assert hospital.subdomain == 'beta-clinic'

    def test_admin_email_taken(self):
        from apps.tenants.services import create_hospital_tenant

        create_hospital_tenant({
            'hospital_name': 'Taken Email Hospital',
            'subdomain': 'taken-email',
            'admin_email': 'duplicate@test.com',
            'admin_name': 'Admin',
            'admin_username': 'admin',
            'admin_password': 'pass123456',
            'base_domain': 'localhost',
        }, approve=True)

        assert admin_email_taken('duplicate@test.com') is True
        assert admin_email_taken('new@test.com') is False
