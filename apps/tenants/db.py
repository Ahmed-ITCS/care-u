"""
django-tenants connection hooks — keep domain_subfolder on every set_tenant().
"""
from django.db import connection
from django_tenants.utils import get_public_schema_name


def _lookup_subdomain(schema_name):
    """Public-schema lookup without ORM (avoids recursive set_tenant calls)."""
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT subdomain FROM public.tenants_hospital WHERE schema_name = %s LIMIT 1',
            [schema_name],
        )
        row = cursor.fetchone()
    return row[0] if row else None


def resolve_domain_subfolder(db_connection=None, path_hint=None):
    """
    Return the subfolder slug for the current tenant connection.
    Never raises; never requires domain_subfolder to already exist.
    """
    db_connection = db_connection or connection
    tenant = getattr(db_connection, 'tenant', None)
    schema = (
        getattr(tenant, 'schema_name', None)
        or getattr(db_connection, 'schema_name', None)
        or 'public'
    )
    if schema == get_public_schema_name():
        return None

    slug = getattr(tenant, 'domain_subfolder', None) if tenant else None
    if not slug and tenant and getattr(tenant, 'subdomain', None):
        slug = tenant.subdomain
    if not slug:
        slug = _lookup_subdomain(schema)
    if not slug and path_hint:
        slug = _slug_from_path(path_hint)
    if not slug:
        slug = schema.replace('_', '-')

    if tenant is not None:
        tenant.domain_subfolder = slug
    return slug


def _slug_from_path(path):
    """Extract tenant slug from /h/{slug}/..."""
    if not path:
        return None
    parts = path.strip('/').split('/')
    # h/{slug}/...
    if len(parts) >= 2 and parts[0] == 'h':
        return parts[1] or None
    return None


def ensure_tenant_domain_subfolder(db_connection=None, tenant=None, path_hint=None):
    """Guarantee domain_subfolder on connection.tenant (works for FakeTenant)."""
    db_connection = db_connection or connection
    if tenant is None:
        tenant = getattr(db_connection, 'tenant', None)
    slug = resolve_domain_subfolder(db_connection, path_hint=path_hint)
    return slug


def extra_set_tenant(db_connection, tenant):
    """Called by django-tenants on every connection.set_tenant()."""
    if getattr(db_connection, '_in_extra_set_tenant', False):
        return
    db_connection._in_extra_set_tenant = True
    try:
        resolve_domain_subfolder(db_connection)
    finally:
        db_connection._in_extra_set_tenant = False
