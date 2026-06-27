from django.core.management.base import BaseCommand
from apps.tenants.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Seed SaaS subscription plans in public schema'

    def handle(self, *args, **options):
        plans = [
            ('trial', 'Free Trial', 0, 5, 100, {'modules': 'all'}, 0, True, 14, 'standard'),
            ('basic', 'Basic', 9999, 15, 2000, {'modules': 'core'}, 1, False, None, 'standard'),
            ('premium', 'Premium', 24999, 50, 10000, {'modules': 'all'}, 2, True, None, 'priority'),
            ('enterprise', 'Enterprise', 49999, 0, 0, {'modules': 'all'}, 3, False, None, 'dedicated'),
        ]
        for name, display, price, users, patients, features, sort_order, featured, trial_days, support in plans:
            SubscriptionPlan.objects.update_or_create(
                name=name,
                defaults={
                    'display_name': display,
                    'price_monthly': price,
                    'max_users': users,
                    'max_patients': patients,
                    'features': features,
                    'sort_order': sort_order,
                    'is_featured': featured,
                    'trial_days': trial_days,
                    'support_level': support,
                    'description': display + ' plan for hospitals.',
                },
            )
        self.stdout.write(self.style.SUCCESS('Subscription plans seeded.'))
