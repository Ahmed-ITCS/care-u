from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):
    """Check if user has one of the required roles."""
    required_roles = []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        roles = getattr(view, 'required_roles', self.required_roles)
        if not roles:
            return True
        return request.user.role in roles or request.user.role == 'admin'


class IsAdmin(RolePermission):
    required_roles = ['admin']


class IsHospitalOwner(BasePermission):
    """Hospital owner — the account created at registration (is_superuser)."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_superuser
        )


class IsDoctor(RolePermission):
    required_roles = ['admin', 'doctor']


class IsReceptionist(RolePermission):
    required_roles = ['admin', 'receptionist']


class IsNurse(RolePermission):
    required_roles = ['admin', 'nurse', 'doctor']


class IsAccountant(RolePermission):
    required_roles = ['admin', 'accountant']


class IsPharmacist(RolePermission):
    required_roles = ['admin', 'pharmacist']


class IsLabTech(RolePermission):
    required_roles = ['admin', 'lab_tech']


class IsPatient(RolePermission):
    required_roles = ['patient']


class IsClinicalStaff(RolePermission):
    required_roles = ['admin', 'doctor', 'nurse']


class IsStaffMember(RolePermission):
    required_roles = ['admin', 'doctor', 'nurse', 'receptionist', 'accountant', 'pharmacist', 'lab_tech']
