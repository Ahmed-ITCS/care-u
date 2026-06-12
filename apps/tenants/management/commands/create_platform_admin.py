from django.core.management.base import BaseCommand
from apps.tenants.models import PlatformUser


class Command(BaseCommand):
    help = 'Create platform super admin user (public schema)'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='superadmin')
        parser.add_argument('--email', default='admin@gphsaas.com')
        parser.add_argument('--password', default='superadmin123')

    def handle(self, *args, **options):
        user, created = PlatformUser.objects.get_or_create(
            username=options['username'],
            defaults={'email': options['email'], 'is_superuser': True},
        )
        user.set_password(options['password'])
        user.save()
        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} platform admin: {options["username"]} / {options["password"]}'
        ))
