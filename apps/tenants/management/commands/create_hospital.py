from django.core.management.base import BaseCommand
from apps.tenants.services import create_hospital_tenant


class Command(BaseCommand):
    help = 'Create a new hospital tenant with schema, domain, and admin user'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Hospital name')
        parser.add_argument('--subdomain', required=True, help='Subdomain / schema name')
        parser.add_argument('--email', required=True, help='Admin email')
        parser.add_argument('--admin-name', default='Hospital Admin')
        parser.add_argument('--password', default='admin123')

    def handle(self, *args, **options):
        data = {
            'hospital_name': options['name'],
            'subdomain': options['subdomain'],
            'admin_email': options['email'],
            'admin_name': options['admin_name'],
            'admin_password': options['password'],
            'base_domain': 'localhost',
        }
        hospital, reg = create_hospital_tenant(data, approve=True)
        self.stdout.write(self.style.SUCCESS(
            f'Tenant created: {hospital.name}\n'
            f'  Schema: {hospital.schema_name}\n'
            f'  URL: /h/{hospital.subdomain}/\n'
            f'  Admin: {options["email"]} / {options["password"]}'
        ))
