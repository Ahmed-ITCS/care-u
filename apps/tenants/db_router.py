"""Database routers — PostgreSQL schema tenancy vs SQLite single-file dev."""

from django.conf import settings
from django_tenants.routers import TenantSyncRouter


class SqliteTenantRouter(TenantSyncRouter):
    """On SQLite, migrate all apps into the single default database."""

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if getattr(settings, 'USE_SQLITE', False):
            return db == 'default'
        return super().allow_migrate(db, app_label, model_name=model_name, **hints)
