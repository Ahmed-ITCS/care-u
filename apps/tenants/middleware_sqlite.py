"""Tenant routing for SQLite (no PostgreSQL schema switching)."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.http import Http404
from django.urls import clear_url_caches, set_urlconf
from django_tenants.urlresolvers import get_subfolder_urlconf
from django_tenants.utils import (
    get_public_schema_name,
    get_subfolder_prefix,
    get_tenant_domain_model,
    get_tenant_model,
)


class SqliteSubfolderMiddleware:
    """
    Resolve /h/{slug}/... without PostgreSQL search_path.
    All tenant ERP tables live in the same SQLite file (single-hospital local dev).
    """

    TENANT_NOT_FOUND_EXCEPTION = Http404

    def __init__(self, get_response):
        self.get_response = get_response
        if not get_subfolder_prefix():
            raise ImproperlyConfigured(
                'SqliteSubfolderMiddleware requires TENANT_SUBFOLDER_PREFIX in settings'
            )

    def __call__(self, request):
        if hasattr(request, 'tenant'):
            return self.get_response(request)

        urlconf = None
        tenant_model = get_tenant_model()
        domain_model = get_tenant_domain_model()
        subfolder_prefix_path = f'/{get_subfolder_prefix()}/'

        if not request.path.startswith(subfolder_prefix_path):
            try:
                tenant = tenant_model.objects.get(schema_name=get_public_schema_name())
            except tenant_model.DoesNotExist as exc:
                raise self.TENANT_NOT_FOUND_EXCEPTION('Unable to find public tenant') from exc
            request.urlconf = settings.PUBLIC_SCHEMA_URLCONF
            set_urlconf(settings.PUBLIC_SCHEMA_URLCONF)
        else:
            tenant_subfolder = request.path[len(subfolder_prefix_path):].split('/')[0]
            try:
                domain = domain_model.objects.select_related('tenant').get(domain=tenant_subfolder)
            except domain_model.DoesNotExist as exc:
                raise self.TENANT_NOT_FOUND_EXCEPTION(
                    f'No tenant for subfolder "{tenant_subfolder}"'
                ) from exc
            tenant = domain.tenant
            tenant.domain_subfolder = tenant_subfolder
            urlconf = get_subfolder_urlconf(tenant)
            request.urlconf = urlconf
            set_urlconf(urlconf)

        request.tenant = tenant
        connection.tenant = tenant
        clear_url_caches()
        return self.get_response(request)
