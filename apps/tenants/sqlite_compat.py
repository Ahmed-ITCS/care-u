"""SQLite local-dev helpers (single-database, no PostgreSQL schemas)."""

from contextlib import contextmanager, nullcontext

from django.conf import settings


def is_sqlite_mode() -> bool:
    return getattr(settings, 'USE_SQLITE', False)


@contextmanager
def tenant_schema_context(schema_name):
    """No-op on SQLite; delegates to django-tenants on PostgreSQL."""
    if is_sqlite_mode():
        yield
        return
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        yield


def set_connection_tenant(connection, tenant):
    if is_sqlite_mode():
        connection.tenant = tenant
        if tenant is None:
            connection.schema_name = 'public'
            return
        connection.schema_name = getattr(tenant, 'schema_name', 'public')
        if not getattr(tenant, 'domain_subfolder', None) and getattr(tenant, 'subdomain', None):
            tenant.domain_subfolder = tenant.subdomain
        return
    connection.set_tenant(tenant)


def set_connection_public(connection):
    if is_sqlite_mode():
        from django_tenants.utils import get_public_schema_name, get_tenant_model

        connection.schema_name = get_public_schema_name()
        try:
            connection.tenant = get_tenant_model().objects.get(
                schema_name=get_public_schema_name()
            )
        except Exception:
            connection.tenant = None
        return
    connection.set_schema_to_public()


def run_migrations(stdout=None):
    from django.core.management import call_command

    if is_sqlite_mode():
        if stdout:
            stdout.write('Migrating SQLite database…')
        call_command('migrate', interactive=False, verbosity=1 if stdout else 0)
        return
    if stdout:
        stdout.write('Migrating public schema…')
    call_command('migrate_schemas', '--shared', interactive=False, verbosity=0)
    if stdout:
        stdout.write('Migrating tenant schemas…')
    call_command('migrate_schemas', interactive=False, verbosity=0)
