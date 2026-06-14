from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.tenants.sqlite_compat import tenant_schema_context

from apps.tenants.models import Hospital
from apps.tenants.auth import sync_user_to_index

User = get_user_model()


class Command(BaseCommand):
    help = 'Rebuild public login index from all tenant users (run after enabling unified login)'

    def handle(self, *args, **options):
        total = 0
        for hospital in Hospital.objects.exclude(schema_name='public'):
            with tenant_schema_context(hospital.schema_name):
                for user in User.objects.all():
                    sync_user_to_index(hospital, user)
                    total += 1
            self.stdout.write(f'  {hospital.subdomain}: synced')
        self.stdout.write(self.style.SUCCESS(f'Synced {total} user(s) — login at /login/ with username or email'))
