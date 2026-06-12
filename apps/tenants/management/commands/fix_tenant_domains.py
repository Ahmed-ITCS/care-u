from django.conf import settings
from django.core.management.base import BaseCommand

from apps.tenants.models import Hospital
from apps.tenants.services import _ensure_tenant_domains


class Command(BaseCommand):
    help = 'Ensure subfolder + subdomain Domain records exist for all hospitals'

    def handle(self, *args, **options):
        base_domain = settings.BASE_DOMAIN
        updated = 0
        for hospital in Hospital.objects.exclude(schema_name='public'):
            _ensure_tenant_domains(hospital, base_domain=base_domain)
            updated += 1
            self.stdout.write(f'  {hospital.subdomain} → /h/{hospital.subdomain}/')
        self.stdout.write(self.style.SUCCESS(f'Updated domains for {updated} hospital(s)'))
