"""
Multi-tenant SaaS app — PUBLIC SCHEMA ONLY.

Hospital (TenantMixin) and Domain models live here alongside PlatformUser
for Super Admin access. All ERP data lives in per-hospital PostgreSQL schemas.
"""
from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenants'
    verbose_name = 'Multi-Tenancy (SaaS)'

    def ready(self):
        import apps.tenants.signals  # noqa: F401
        from apps.tenants.urlresolvers_patch import patch_tenant_urlresolvers

        patch_tenant_urlresolvers()
