from django.conf import settings
from django.db import connection
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.tenants.auth import (
    resolve_hospital_instance,
    sync_user_to_index,
    remove_user_from_index,
)


def _hospital_for_user_index():
    """Real Hospital row for the current tenant schema (not FakeTenant)."""
    tenant = getattr(connection, 'tenant', None)
    if not tenant:
        return None
    return resolve_hospital_instance(tenant)


@receiver(post_save, sender='tenants.Hospital')
def ensure_hospital_domain_folder(sender, instance, **kwargs):
    """Create /h/{subdomain}/ Domain record whenever a hospital is saved."""
    if instance.schema_name == 'public':
        return
    from apps.tenants.services import _ensure_tenant_domains

    _ensure_tenant_domains(instance, base_domain=getattr(settings, 'BASE_DOMAIN', 'localhost'))


@receiver(post_save, sender='users.User')
def index_tenant_user_on_save(sender, instance, **kwargs):
    hospital = _hospital_for_user_index()
    if not hospital:
        return
    sync_user_to_index(hospital, instance)


@receiver(post_delete, sender='users.User')
def index_tenant_user_on_delete(sender, instance, **kwargs):
    hospital = _hospital_for_user_index()
    if not hospital:
        return
    remove_user_from_index(hospital, instance.username)
