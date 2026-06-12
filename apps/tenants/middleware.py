"""
Tenant middleware — subscription enforcement, public-schema sessions, auth.
"""
from django.conf import settings
from django.db import connection
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.sessions.middleware import SessionMiddleware
from django_tenants.middleware.subfolder import TenantSubfolderMiddleware as DjangoTenantSubfolderMiddleware
from django_tenants.utils import get_public_schema_name

from apps.tenants.db import ensure_tenant_domain_subfolder, resolve_domain_subfolder


class TenantSubfolderMiddleware(DjangoTenantSubfolderMiddleware):
    """
    Resolve /h/{slug}/... and always attach domain_subfolder to the tenant.
    """

    def process_request(self, request):
        super().process_request(request)
        tenant = getattr(request, 'tenant', None)
        if not tenant or getattr(tenant, 'schema_name', 'public') == get_public_schema_name():
            return
        slug = _subfolder_from_request(request) or tenant.subdomain
        tenant.domain_subfolder = slug
        request._tenant_subfolder = slug
        request.tenant = tenant
        connection.set_tenant(tenant)


def _uses_db_session_backend():
    """Only database-backed sessions require switching to the public schema."""
    engine = settings.SESSION_ENGINE
    return 'db' in engine


def _subfolder_from_request(request):
    """Extract tenant slug from /h/{slug}/... when connection.tenant is incomplete."""
    prefix = getattr(settings, 'TENANT_SUBFOLDER_PREFIX', 'h/')
    if not prefix.endswith('/'):
        prefix = prefix + '/'
    path = request.path
    marker = '/' + prefix
    if not path.startswith(marker):
        return None
    slug = path[len(marker):].split('/')[0]
    return slug or None


def _active_tenant(request):
    """Prefer request.tenant (set by TenantSubfolderMiddleware) over connection.tenant."""
    rt = getattr(request, 'tenant', None)
    if rt and getattr(rt, 'schema_name', 'public') != get_public_schema_name():
        return rt
    ct = getattr(connection, 'tenant', None)
    if ct and getattr(ct, 'schema_name', 'public') != get_public_schema_name():
        return ct
    return rt or ct


def _ensure_domain_subfolder(tenant, request=None):
    """django-tenants urlresolvers require domain_subfolder on connection.tenant."""
    if not tenant or getattr(tenant, 'schema_name', 'public') == 'public':
        return tenant
    if getattr(tenant, 'domain_subfolder', None):
        return tenant
    rt = getattr(request, 'tenant', None) if request else None
    if rt and getattr(rt, 'domain_subfolder', None):
        tenant.domain_subfolder = rt.domain_subfolder
    elif request and getattr(request, '_tenant_subfolder', None):
        tenant.domain_subfolder = request._tenant_subfolder
    elif request:
        slug = _subfolder_from_request(request)
        if slug:
            tenant.domain_subfolder = slug
    elif getattr(tenant, 'subdomain', None):
        tenant.domain_subfolder = tenant.subdomain
    else:
        ensure_tenant_domain_subfolder(connection, tenant)
    return tenant


def _lookup_hospital_subdomain(schema_name):
    from apps.tenants.db import _lookup_subdomain
    return _lookup_subdomain(schema_name)


def _resolve_full_tenant(request):
    """
    Return a real Hospital with domain_subfolder for URL reversing.
    connection.tenant is often a FakeTenant (schema only) after session/auth I/O.
    """
    from django_tenants.utils import get_tenant_model

    tenant = _active_tenant(request)
    if not tenant:
        return None
    schema = getattr(tenant, 'schema_name', 'public')
    if schema == get_public_schema_name():
        return tenant

    Hospital = get_tenant_model()
    if getattr(tenant, 'pk', None) and getattr(tenant, 'subdomain', None):
        return _ensure_domain_subfolder(tenant, request)

    # FakeTenant or incomplete instance
    subdomain = _lookup_hospital_subdomain(schema) or _subfolder_from_request(request)
    if subdomain:
        rt = getattr(request, 'tenant', None)
        ensure_tenant_domain_subfolder(connection, tenant)
        if not getattr(tenant, 'domain_subfolder', None):
            tenant.domain_subfolder = (
                getattr(rt, 'domain_subfolder', None)
                or subdomain
            )
        hospital = Hospital.objects.filter(schema_name=schema).first()
        if hospital:
            hospital.domain_subfolder = tenant.domain_subfolder
            return hospital
        return tenant

    return _ensure_domain_subfolder(tenant, request)


def _restore_tenant(request):
    """Put full tenant back on the connection (required for {% url %} in tenant URLs)."""
    tenant = _resolve_full_tenant(request)
    if not tenant or getattr(tenant, 'schema_name', 'public') == get_public_schema_name():
        return
    tenant = _ensure_domain_subfolder(tenant, request)
    connection.set_tenant(tenant)
    request.tenant = tenant


def ensure_request_tenant(request):
    """Call from tenant views that need a reliable Hospital instance."""
    _restore_tenant(request)
    return request.tenant


class PublicSchemaSessionMiddleware(SessionMiddleware):
    """
    Database sessions live in the public schema (SHARED_APPS).
    Cache/file sessions do NOT need schema switching — switching breaks tenant URLs.
    """

    def process_request(self, request):
        if _uses_db_session_backend():
            connection.set_schema_to_public()
        try:
            super().process_request(request)
            request.session.load()
        finally:
            _restore_tenant(request)

    def process_response(self, request, response):
        if _uses_db_session_backend():
            connection.set_schema_to_public()
        try:
            return super().process_response(request, response)
        finally:
            _restore_tenant(request)


class TenantSubfolderGuardMiddleware:
    """
    Last middleware before the view — restores full tenant after session/auth/auditlog.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _restore_tenant(request)
        resolve_domain_subfolder(connection, path_hint=request.path)
        return self.get_response(request)


class PublicSchemaAuthGuardMiddleware:
    """
    Run before AuthenticationMiddleware. On the public schema, temporarily stash
    hospital auth session keys so get_user() does not query users_user (tenant-only).
    Keys are restored in process_response so /h/{tenant}/ logins keep working.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = _active_tenant(request)
        is_public = getattr(tenant, 'schema_name', 'public') == get_public_schema_name()
        request._stashed_tenant_auth = None

        if is_public:
            stashed = {}
            for key in ('_auth_user_id', '_auth_user_backend', '_auth_user_hash'):
                if key in request.session:
                    stashed[key] = request.session.pop(key)
            if stashed:
                request._stashed_tenant_auth = stashed
                request.session.modified = True

        response = self.get_response(request)

        stashed = getattr(request, '_stashed_tenant_auth', None)
        if stashed:
            request.session.update(stashed)
            request.session.modified = True

        return response


class TenantSessionAuthMiddleware:
    """
    Run after AuthenticationMiddleware.
    - Public schema: force AnonymousUser (users_user does not exist there).
    - Tenant schema: reject session if it belongs to a different hospital.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.contrib.auth.models import AnonymousUser

        tenant = _active_tenant(request)
        schema = getattr(tenant, 'schema_name', 'public')

        if schema == get_public_schema_name():
            request.user = AnonymousUser()
        else:
            session_tenant = request.session.get('tenant_subdomain')
            if session_tenant and getattr(tenant, 'subdomain', None) != session_tenant:
                request.user = AnonymousUser()

        return self.get_response(request)


class TenantAccessMiddleware:
    """TENANT: Enforce subscription status — block suspended/expired hospitals."""

    EXEMPT_PREFIXES = ('/static/', '/media/', '/admin/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = _active_tenant(request)

        if tenant and getattr(tenant, 'schema_name', 'public') != 'public':
            if not tenant.is_active_tenant:
                messages.error(request, 'This hospital account is suspended or expired. Please contact support.')
                return redirect('/suspended/')

        return self.get_response(request)
