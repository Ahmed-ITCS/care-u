from django.contrib import admin
from apps.tenants.models import Hospital, Domain, PlatformUser, SubscriptionPlan, HospitalRegistration


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ('name', 'subdomain', 'schema_name', 'status', 'plan', 'paid_until', 'created_at')
    list_filter = ('status', 'plan')
    search_fields = ('name', 'subdomain', 'email')
    readonly_fields = ('schema_name', 'created_at', 'updated_at')


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')


@admin.register(PlatformUser)
class PlatformUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_active', 'last_login')
    search_fields = ('username', 'email')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'price_monthly', 'max_users', 'is_active')


@admin.register(HospitalRegistration)
class HospitalRegistrationAdmin(admin.ModelAdmin):
    list_display = ('hospital_name', 'subdomain', 'admin_email', 'is_processed', 'created_at')
    list_filter = ('is_processed',)
