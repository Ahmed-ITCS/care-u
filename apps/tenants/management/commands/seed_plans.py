from django.core.management.base import BaseCommand
from apps.tenants.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Seed SaaS subscription plans in public schema'

    def handle(self, *args, **options):
        plans = [
            ('trial', 'Free Trial', 0, 5, 100, {'modules': 'all', 'duration_days': 14}),
            ('basic', 'Basic', 9999, 15, 2000, {'modules': 'core'}),
            ('premium', 'Premium', 24999, 50, 10000, {'modules': 'all'}),
            ('enterprise', 'Enterprise', 49999, 999, 999999, {'modules': 'all', 'support': 'priority'}),
        ]
        for name, display, price, users, patients, features in plans:
            SubscriptionPlan.objects.update_or_create(
                name=name,
                defaults={
                    'display_name': display,
                    'price_monthly': price,
                    'max_users': users,
                    'max_patients': patients,
                    'features': features,
                },
            )
        self.stdout.write(self.style.SUCCESS('Subscription plans seeded.'))
