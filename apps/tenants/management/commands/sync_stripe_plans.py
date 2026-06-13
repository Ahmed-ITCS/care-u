from django.core.management.base import BaseCommand
from apps.tenants.models import SubscriptionPlan
from apps.tenants.stripe_services import StripeNotConfigured, sync_plan_to_stripe


class Command(BaseCommand):
    help = 'Sync subscription plans to Stripe Products and Prices (public schema)'

    def add_arguments(self, parser):
        parser.add_argument('--plan', type=str, help='Sync a single plan slug only')

    def handle(self, *args, **options):
        try:
            qs = SubscriptionPlan.objects.filter(is_active=True).exclude(name='trial')
            if options.get('plan'):
                qs = qs.filter(name=options['plan'])
            count = 0
            for plan in qs:
                if plan.price_monthly <= 0:
                    continue
                sync_plan_to_stripe(plan)
                count += 1
                self.stdout.write(f'  {plan.name} → {plan.stripe_price_id}')
            self.stdout.write(self.style.SUCCESS(f'Synced {count} plan(s) to Stripe.'))
        except StripeNotConfigured:
            self.stderr.write(self.style.ERROR('STRIPE_SECRET_KEY is not set.'))
