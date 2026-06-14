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
        return
    connection.set_tenant(tenant)


def set_connection_public(connection):
    if is_sqlite_mode():
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
