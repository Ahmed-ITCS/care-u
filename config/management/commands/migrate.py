"""Use standard Django migrate on SQLite; delegate to migrate_schemas on PostgreSQL."""

from django.conf import settings
from django.core.management.commands.migrate import Command as DjangoMigrateCommand


class Command(DjangoMigrateCommand):
    def handle(self, *args, **options):
        if getattr(settings, 'USE_SQLITE', False):
            return super().handle(*args, **options)
        from django_tenants.management.commands.migrate_schemas import Command as MigrateSchemasCommand

        cmd = MigrateSchemasCommand()
        cmd.stdout = self.stdout
        cmd.stderr = self.stderr
        return cmd.handle(*args, **options)
