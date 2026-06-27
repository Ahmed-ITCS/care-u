import pytest
from django.db import connection

from apps.tenants.limits import (
    SubscriptionLimitExceeded,
    check_patient_limit,
    check_staff_limit,
    is_module_allowed,
    resolve_allowed_modules,
    CORE_PLAN_MODULES,
    ALL_PLAN_MODULES,
)
from apps.tenants.models import SubscriptionPlan


@pytest.fixture
def basic_plan(db):
    connection.set_schema_to_public()
    plan, _ = SubscriptionPlan.objects.update_or_create(
        name='test-basic',
        defaults={
            'display_name': 'Test Basic',
            'price_monthly': 1000,
            'max_users': 2,
            'max_patients': 3,
            'features': {'modules': 'core'},
            'is_active': True,
        },
    )
    return plan


@pytest.fixture
def premium_plan(db):
    connection.set_schema_to_public()
    plan, _ = SubscriptionPlan.objects.update_or_create(
        name='test-premium',
        defaults={
            'display_name': 'Test Premium',
            'price_monthly': 5000,
            'max_users': 50,
            'max_patients': 10000,
            'features': {'modules': 'all'},
            'is_active': True,
        },
    )
    return plan


@pytest.fixture
def tenant_with_plan(test_tenant, premium_plan):
    connection.set_schema_to_public()
    test_tenant.plan = premium_plan
    test_tenant.status = 'active'
    test_tenant.save(update_fields=['plan', 'status', 'updated_at'])
    connection.set_tenant(test_tenant)
    return test_tenant


@pytest.mark.django_db
class TestPlanModules:
    def test_core_plan_modules(self, basic_plan):
        assert resolve_allowed_modules(basic_plan) == CORE_PLAN_MODULES
        assert is_module_allowed(basic_plan, 'laboratory') is False
        assert is_module_allowed(basic_plan, 'patients') is True

    def test_all_plan_modules(self, premium_plan):
        assert resolve_allowed_modules(premium_plan) == ALL_PLAN_MODULES
        assert is_module_allowed(premium_plan, 'hr') is True

    def test_custom_plan_modules(self, db):
        connection.set_schema_to_public()
        plan = SubscriptionPlan.objects.create(
            name='custom-lab-pharmacy',
            display_name='Lab + Pharmacy',
            max_users=10,
            max_patients=500,
            features={'modules': ['laboratory', 'pharmacy']},
        )
        allowed = resolve_allowed_modules(plan)
        assert 'laboratory' in allowed
        assert 'pharmacy' in allowed
        assert 'hr' not in allowed
        assert 'patients' in allowed

    def test_explicit_custom_modules(self, db):
        connection.set_schema_to_public()
        plan = SubscriptionPlan.objects.create(
            name='lab-only-explicit',
            display_name='Lab Only',
            features={'modules': ['laboratory'], 'explicit_modules': True},
        )
        allowed = resolve_allowed_modules(plan)
        assert 'laboratory' in allowed
        assert 'patients' not in allowed
        assert 'billing' not in allowed


@pytest.mark.django_db
class TestStaffLimit:
    def test_blocks_at_max_staff(self, tenant_with_plan, basic_plan, admin_user, doctor_user):
        connection.set_schema_to_public()
        tenant_with_plan.plan = basic_plan
        tenant_with_plan.save(update_fields=['plan', 'updated_at'])
        connection.set_tenant(tenant_with_plan)

        with pytest.raises(SubscriptionLimitExceeded):
            check_staff_limit()

    def test_allows_under_limit(self, tenant_with_plan, admin_user):
        connection.set_tenant(tenant_with_plan)
        check_staff_limit()

    def test_unlimited_staff_skips_check(self, tenant_with_plan, premium_plan, admin_user, doctor_user):
        connection.set_schema_to_public()
        premium_plan.max_users = 0
        premium_plan.save(update_fields=['max_users'])
        tenant_with_plan.plan = premium_plan
        tenant_with_plan.save(update_fields=['plan', 'updated_at'])
        connection.set_tenant(tenant_with_plan)
        check_staff_limit()


@pytest.mark.django_db
class TestPatientLimit:
    def test_blocks_at_max_patients(self, tenant_with_plan, basic_plan, receptionist_user):
        connection.set_schema_to_public()
        tenant_with_plan.plan = basic_plan
        tenant_with_plan.save(update_fields=['plan', 'updated_at'])
        connection.set_tenant(tenant_with_plan)

        from apps.patients.models import Patient
        for i in range(3):
            Patient.objects.create(
                cnic=f'35202-111111{i}-1',
                first_name=f'P{i}',
                last_name='Test',
                phone=f'0300111111{i}',
                registered_by=receptionist_user,
            )
        with pytest.raises(SubscriptionLimitExceeded):
            check_patient_limit()


@pytest.mark.django_db
class TestAPIEnforcement:
    def test_patient_create_blocked_at_limit(
        self, tenant_with_plan, basic_plan, admin_user, receptionist_user, tenant_prefix,
    ):
        connection.set_schema_to_public()
        tenant_with_plan.plan = basic_plan
        tenant_with_plan.save(update_fields=['plan', 'updated_at'])
        connection.set_tenant(tenant_with_plan)

        from apps.patients.models import Patient
        from rest_framework.test import APIClient

        for i in range(3):
            Patient.objects.create(
                cnic=f'35202-222222{i}-1',
                first_name=f'Api{i}',
                last_name='Test',
                phone=f'0300222222{i}',
                registered_by=receptionist_user,
            )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.post(f'{tenant_prefix}/api/v1/patients/', {
            'cnic': '35202-9999999-1',
            'first_name': 'Blocked',
            'last_name': 'Patient',
            'phone': '03009999999',
            'gender': 'male',
        }, format='json')
        assert response.status_code == 403

    def test_staff_create_blocked_at_limit(
        self, tenant_with_plan, basic_plan, admin_user, doctor_user, tenant_prefix,
    ):
        connection.set_schema_to_public()
        tenant_with_plan.plan = basic_plan
        tenant_with_plan.save(update_fields=['plan', 'updated_at'])
        connection.set_tenant(tenant_with_plan)

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.post(f'{tenant_prefix}/api/v1/users/', {
            'username': 'newstaff',
            'email': 'new@test.com',
            'first_name': 'New',
            'last_name': 'Staff',
            'role': 'nurse',
            'password': 'testpass123',
        }, format='json')
        assert response.status_code == 403

    def test_module_blocked_for_basic_plan(
        self, tenant_with_plan, basic_plan, admin_user, tenant_prefix,
    ):
        connection.set_schema_to_public()
        tenant_with_plan.plan = basic_plan
        tenant_with_plan.save(update_fields=['plan', 'updated_at'])
        connection.set_tenant(tenant_with_plan)

        from rest_framework.test import APIClient

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f'{tenant_prefix}/api/v1/lab-requests/')
        assert response.status_code == 403
