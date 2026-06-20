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


def _index_candidates(identifier, hospital_subdomain=None):
    from apps.tenants.models import Hospital, TenantUserIndex

    identifier = (identifier or '').strip()
    subdomain = (hospital_subdomain or '').strip().lower()

    with tenant_schema_context(get_public_schema_name()):
        if subdomain:
            hospital = Hospital.objects.filter(subdomain=subdomain).first()
            if not hospital:
                return [], 'invalid_hospital'
            qs = TenantUserIndex.objects.filter(
                is_active=True, hospital=hospital,
            ).select_related('hospital')
        else:
            qs = TenantUserIndex.objects.filter(is_active=True).select_related('hospital')

        if '@' in identifier:
            entries = list(qs.filter(email__iexact=identifier))
        else:
            entries = list(qs.filter(username__iexact=identifier))

    return entries, None


def resolve_tenant_and_authenticate(identifier, password, hospital_subdomain=None):
    """
    Given username or email + password, find the hospital and authenticate the user.
    Returns (hospital, user, error_code) where error_code is None on success.
    """
    identifier = (identifier or '').strip()
    if not identifier or not password:
        return None, None, 'invalid'

    entries, lookup_error = _index_candidates(identifier, hospital_subdomain)
    if lookup_error:
        return None, None, lookup_error
    if not entries:
        return None, None, 'invalid'

    matches = []
    for entry in entries:
        hospital = entry.hospital
        if hospital.schema_name == 'public' or not hospital.is_active_tenant:
            continue
        with tenant_schema_context(hospital.schema_name):
            user = authenticate(username=entry.username, password=password)
            if user and user.is_active:
                matches.append((hospital, user))

    if len(matches) == 1:
        return matches[0][0], matches[0][1], None
    if len(matches) > 1:
        return None, None, 'ambiguous'
    return None, None, 'invalid'


def admin_email_taken(email, exclude_hospital=None):
    """True if another hospital already registered this admin email."""
    from apps.tenants.models import TenantUserIndex

    email = (email or '').strip().lower()
    if not email:
        return False
    with tenant_schema_context(get_public_schema_name()):
        qs = TenantUserIndex.objects.filter(email__iexact=email)
        if exclude_hospital:
            hospital = resolve_hospital_instance(exclude_hospital)
            if hospital:
                qs = qs.exclude(hospital=hospital)
        return qs.exists()


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
