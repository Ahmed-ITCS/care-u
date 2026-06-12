import pytest
from apps.core.permissions import RolePermission
from apps.users.models import Role
from rest_framework.test import APIRequestFactory


@pytest.mark.django_db
class TestPermissions:
    def test_admin_has_access(self, admin_user):
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = admin_user
        perm = RolePermission()
        perm.required_roles = [Role.DOCTOR]
        assert perm.has_permission(request, None) is True

    def test_receptionist_denied_doctor_only(self, receptionist_user):
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = receptionist_user
        perm = RolePermission()
        perm.required_roles = [Role.DOCTOR]
        assert perm.has_permission(request, None) is False

    def test_doctor_has_clinical_access(self, doctor_user):
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = doctor_user
        perm = RolePermission()
        perm.required_roles = [Role.DOCTOR]
        assert perm.has_permission(request, None) is True
