import re
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone
from django_tenants.models import DomainMixin, TenantMixin


class SubscriptionPlan(models.Model):
    """SaaS subscription tiers — stored in public schema."""

    name = models.SlugField(max_length=50, unique=True, help_text='Internal slug, e.g. premium or acme-hospital')
    display_name = models.CharField(max_length=100)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_users = models.PositiveIntegerField(default=10)
    max_patients = models.PositiveIntegerField(default=1000)
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['price_monthly']

    def __str__(self):
        return self.display_name

    @property
    def modules_mode(self):
        return (self.features or {}).get('modules', 'all')

    def module_labels(self):
        from apps.tenants.limits import plan_module_summary
        return plan_module_summary(self)


class Hospital(TenantMixin):
    """
    Each hospital is a tenant with its own PostgreSQL schema.
    schema_name is auto-set from subdomain on save.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
    ]

    name = models.CharField(max_length=255)
    subdomain = models.SlugField(max_length=63, unique=True, help_text='Used for subdomain & schema')
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    logo = models.ImageField(upload_to='tenants/logos/', blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial', db_index=True)
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='hospitals'
    )
    paid_until = models.DateField(null=True, blank=True)
    trial_ends = models.DateField(null=True, blank=True)

    primary_color = models.CharField(max_length=7, default='#1E40AF')
    accent_color = models.CharField(max_length=7, default='#059669')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='PKR')
    receipt_header = models.TextField(blank=True)
    receipt_footer = models.TextField(blank=True)

    onboarding_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.schema_name:
            self.schema_name = self._sanitize_schema_name(self.subdomain)
        super().save(*args, **kwargs)

    @staticmethod
    def _sanitize_schema_name(subdomain):
        name = re.sub(r'[^a-z0-9_]', '', subdomain.lower().replace('-', '_'))
        return name[:63] or 'tenant'

    @property
    def is_active_tenant(self):
        if self.status == 'suspended':
            return False
        if self.status == 'expired':
            return False
        if self.paid_until and self.paid_until < timezone.now().date():
            return False
        if self.status == 'trial' and self.trial_ends and self.trial_ends < timezone.now().date():
            return False
        return self.status in ('trial', 'active')

    @property
    def days_until_expiry(self):
        if self.paid_until:
            return (self.paid_until - timezone.now().date()).days
        if self.trial_ends and self.status == 'trial':
            return (self.trial_ends - timezone.now().date()).days
        return None

    def setup_trial(self, days=14):
        self.status = 'trial'
        self.trial_ends = timezone.now().date() + timedelta(days=days)
        trial_plan = SubscriptionPlan.objects.filter(name='trial').first()
        if trial_plan:
            self.plan = trial_plan


class Domain(DomainMixin):
    """Maps subdomain (or custom domain) to a hospital tenant."""

    class Meta:
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'


class PlatformUser(models.Model):
    """
    Super Admin users — PUBLIC SCHEMA ONLY.
    Lightweight model (not AbstractUser) to avoid auth table conflicts with tenant User.
    """

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Platform Admin'
        verbose_name_plural = 'Platform Admins'

    def __str__(self):
        return f'Platform Admin: {self.username}'

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class HospitalRegistration(models.Model):
    """Tracks hospital sign-up requests before/after tenant creation."""

    hospital = models.OneToOneField(
        Hospital, on_delete=models.CASCADE, related_name='registration', null=True, blank=True
    )
    admin_name = models.CharField(max_length=200)
    admin_email = models.EmailField()
    admin_phone = models.CharField(max_length=20, blank=True)
    hospital_name = models.CharField(max_length=255)
    subdomain = models.SlugField(max_length=63)
    address = models.TextField(blank=True)
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.hospital_name} ({self.subdomain})'


class TenantUserIndex(models.Model):
    """
    PUBLIC SCHEMA: maps login credentials → hospital tenant.
    Enables single /login/ for all hospitals — no subdomain entry required.
    """
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='user_index')
    username = models.CharField(max_length=150, db_index=True)
    email = models.EmailField(blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tenant User Index'
        unique_together = [('hospital', 'username')]
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]

    def __str__(self):
        return f'{self.username} @ {self.hospital.subdomain}'
