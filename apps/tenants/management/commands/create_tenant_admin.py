"""
Create a hospital admin user inside a tenant schema.
Use this instead of `createsuperuser` — that command only works in single-tenant Django.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from apps.tenants.sqlite_compat import tenant_schema_context

from apps.tenants.models import Hospital
from apps.users.models import Role, StaffProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Create hospital admin in a tenant schema (replaces createsuperuser for hospitals)'

    def add_arguments(self, parser):
        parser.add_argument('--subdomain', required=True, help='Hospital subdomain, e.g. gph-islamabad')
        parser.add_argument('--username', required=True)
        parser.add_argument('--email', required=True)
        parser.add_argument('--password', required=True)
        parser.add_argument('--name', default='', help='Full name')

    def handle(self, *args, **options):
        subdomain = options['subdomain'].lower().strip()
        try:
            hospital = Hospital.objects.get(subdomain=subdomain)
        except Hospital.DoesNotExist:
            raise CommandError(
                f'No hospital with subdomain "{subdomain}". '
                f'Use create_hospital to register a new tenant first.'
            )

        parts = options['name'].split() if options['name'] else []
        first_name = parts[0] if parts else ''
        last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        with tenant_schema_context(hospital.schema_name):
            if User.objects.filter(username=options['username']).exists():
                raise CommandError(f'User "{options["username"]}" already exists in this hospital.')

            user = User.objects.create_user(
                username=options['username'],
                email=options['email'],
                password=options['password'],
                first_name=first_name,
                last_name=last_name,
                role=Role.ADMIN,
                is_staff=True,
                is_superuser=True,
                is_verified=True,
            )
            StaffProfile.objects.get_or_create(user=user, defaults={'cnic': ''})

        from apps.tenants.auth import sync_user_to_index
        sync_user_to_index(hospital, user)

        self.stdout.write(self.style.SUCCESS(
            f'Hospital admin created for {hospital.name}\n'
            f'  Sign in at: /login/\n'
            f'  Username: {options["username"]}\n'
            f'  Password: {options["password"]}'
        ))
