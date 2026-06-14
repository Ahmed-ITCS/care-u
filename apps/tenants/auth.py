"""
Unified authentication — find the user's hospital from credentials alone.
"""
import logging

from django.contrib.auth import authenticate
from django_tenants.utils import get_public_schema_name

from apps.tenants.sqlite_compat import tenant_schema_context

logger = logging.getLogger(__name__)


def resolve_hospital_instance(tenant_or_hospital):
    """
    Return a real Hospital model instance (with pk) for public-schema FK writes.
    schema_context() sets connection.tenant to FakeTenant, which has no pk.
    """
    if tenant_or_hospital is None:
        return None
    if getattr(tenant_or_hospital, 'pk', None):
        return tenant_or_hospital
    schema_name = getattr(tenant_or_hospital, 'schema_name', None)
    if not schema_name or schema_name == 'public':
        return None
    from apps.tenants.models import Hospital

    with tenant_schema_context(get_public_schema_name()):
        return Hospital.objects.filter(schema_name=schema_name).first()


def resolve_tenant_and_authenticate(identifier, password):
    """
    Given username or email + password, find the hospital and authenticate the user.
    Returns (hospital, user) or None.
    """
    from apps.tenants.models import TenantUserIndex

    identifier = (identifier or '').strip()
    if not identifier or not password:
        return None

    with tenant_schema_context(get_public_schema_name()):
        qs = TenantUserIndex.objects.filter(is_active=True).select_related('hospital')
        if '@' in identifier:
            entries = qs.filter(email__iexact=identifier)
        else:
            entries = qs.filter(username__iexact=identifier)

        candidates = list(entries)

    for entry in candidates:
        hospital = entry.hospital
        if hospital.schema_name == 'public' or not hospital.is_active_tenant:
            continue
        with tenant_schema_context(hospital.schema_name):
            user = authenticate(username=entry.username, password=password)
            if user and user.is_active:
                return hospital, user

    return None


def sync_user_to_index(hospital, user):
    """Register or update a tenant user in the public login index."""
    from apps.tenants.models import TenantUserIndex

    hospital = resolve_hospital_instance(hospital)
    if not hospital:
        return

    with tenant_schema_context(get_public_schema_name()):
        TenantUserIndex.objects.update_or_create(
            hospital=hospital,
            username=user.username,
            defaults={
                'email': (user.email or '').lower(),
                'is_active': user.is_active,
            },
        )


def remove_user_from_index(hospital, username):
    from apps.tenants.models import TenantUserIndex

    hospital = resolve_hospital_instance(hospital)
    if not hospital:
        return

    with tenant_schema_context(get_public_schema_name()):
        TenantUserIndex.objects.filter(hospital=hospital, username=username).delete()
