"""Patch django-tenants URL resolver — match /h/{slug}/ from the path, not connection state."""


def _slug_and_prefix_from_path(path):
    """Parse h/{slug}/ from the path Django passes to TenantPrefixPattern.match."""
    from django_tenants.utils import get_subfolder_prefix

    parts = path.strip('/').split('/')
    subfolder_prefix = get_subfolder_prefix()  # 'h'
    if len(parts) < 2 or parts[0] != subfolder_prefix:
        return None, None
    slug = parts[1]
    prefix = f'{subfolder_prefix}/{slug}/'
    return slug, prefix


def patch_tenant_urlresolvers():
    from django.db import connection
    from django_tenants import urlresolvers as dt_urlresolvers
    from django_tenants.utils import get_subfolder_prefix, get_public_schema_name

    from apps.tenants.db import resolve_domain_subfolder

    def safe_tenant_prefix(self):
        """Used by reverse() — derive prefix from connection tenant."""
        schema = getattr(connection, 'schema_name', get_public_schema_name())
        if schema == get_public_schema_name():
            return '/'
        slug = resolve_domain_subfolder(connection)
        if not slug:
            return '/'
        subfolder_prefix = get_subfolder_prefix()
        if subfolder_prefix:
            return f'{subfolder_prefix}/{slug}/'
        return f'{slug}/'

    def safe_match(self, path):
        """Used when resolving incoming requests — always read slug from the URL path."""
        slug, prefix = _slug_and_prefix_from_path(path)
        if not slug or not prefix:
            return None
        if path.startswith(prefix):
            # Keep connection.tenant.domain_subfolder in sync for the rest of the request
            resolve_domain_subfolder(connection, path_hint=f'/{path}')
            return path[len(prefix):], (), {}
        return None

    dt_urlresolvers.TenantPrefixPattern.tenant_prefix = property(safe_tenant_prefix)
    dt_urlresolvers.TenantPrefixPattern.match = safe_match
