from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StaffProfile, DoctorProfile, OTPVerification


class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    can_delete = False
    extra = 0


class DoctorProfileInline(admin.StackedInline):
    model = DoctorProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('CARE-U Info', {'fields': ('role', 'phone', 'is_verified')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('CARE-U Info', {'fields': ('role', 'phone')}),
    )
    inlines = [StaffProfileInline, DoctorProfileInline]


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'channel', 'is_used', 'expires_at', 'created_at')
    list_filter = ('purpose', 'channel', 'is_used')
