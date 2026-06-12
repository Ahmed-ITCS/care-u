from django.core.management.base import BaseCommand
from django.conf import settings
from apps.tenants.models import Hospital, Domain


class Command(BaseCommand):
    help = 'Create public schema tenant record (required by django-tenants)'

    def handle(self, *args, **options):
        public, created = Hospital.objects.get_or_create(
            schema_name='public',
            defaults={
                'name': settings.PLATFORM_NAME,
                'subdomain': 'public',
                'email': 'admin@gphsaas.com',
                'status': 'active',
            },
        )
        if created:
            public.auto_create_schema = False
            public.save()

        base = settings.BASE_DOMAIN
        Domain.objects.get_or_create(
            domain=base,
            defaults={'tenant': public, 'is_primary': True},
        )
        Domain.objects.get_or_create(
            domain=f'www.{base}',
            defaults={'tenant': public, 'is_primary': False},
        )

        action = 'Created' if created else 'Exists'
        self.stdout.write(self.style.SUCCESS(f'{action} public schema tenant (domain={base})'))
