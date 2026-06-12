from django.core.management.base import BaseCommand
import json
from django.apps import apps


class Command(BaseCommand):
    help = 'Export hospital data backup (JSON)'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='backup.json')

    def handle(self, *args, **options):
        from apps.patients.models import Patient
        from apps.billing.models import Invoice

        data = {
            'patients': list(Patient.objects.values('mr_number', 'full_name', 'cnic', 'phone')),
            'invoices': list(Invoice.objects.values('invoice_number', 'total_amount', 'status')),
        }
        with open(options['output'], 'w') as f:
            json.dump(data, f, indent=2, default=str)
        self.stdout.write(self.style.SUCCESS(f'Backup saved to {options["output"]}'))
