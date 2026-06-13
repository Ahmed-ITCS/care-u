from django.contrib import admin
from apps.tenants.models import Hospital, Domain, PlatformUser, SubscriptionPlan, HospitalRegistration, StripeWebhookEvent, SubscriptionPayment


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'subdomain', 'schema_name', 'status', 'plan', 'paid_until', 'created_at')
    list_filter = ('status', 'plan')
    search_fields = ('name', 'subdomain', 'email')
    readonly_fields = ('schema_name', 'created_at', 'updated_at', 'stripe_customer_id', 'stripe_subscription_id')


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')


@admin.register(PlatformUser)
class PlatformUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'last_login')
    search_fields = ('username', 'email')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'price_monthly', 'max_users', 'max_patients', 'stripe_price_id', 'is_active')
    search_fields = ('name', 'display_name')
    readonly_fields = ('stripe_product_id', 'stripe_price_id')


@admin.register(HospitalRegistration)
class HospitalRegistrationAdmin(admin.ModelAdmin):
    list_display = ('hospital_name', 'subdomain', 'admin_email', 'is_processed', 'created_at')
    list_filter = ('is_processed',)


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'stripe_event_id', 'processed_at')
    search_fields = ('stripe_event_id', 'event_type')
    readonly_fields = ('stripe_event_id', 'event_type', 'processed_at')


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ('txn_ref', 'hospital', 'plan', 'method', 'amount', 'status', 'created_at')
    list_filter = ('method', 'status')
    search_fields = ('txn_ref', 'hospital__name', 'hospital__subdomain', 'gateway_txn_id')
    readonly_fields = ('txn_ref', 'gateway_response', 'created_at', 'completed_at')
