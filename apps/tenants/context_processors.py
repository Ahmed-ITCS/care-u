from django.conf import settings
from django.db import connection


def tenant_context(request):
    """Inject current tenant (hospital) info into all templates."""
    tenant = getattr(connection, 'tenant', None)
    is_public = not tenant or getattr(tenant, 'schema_name', 'public') == 'public'

    ctx = {
        'current_tenant': None if is_public else tenant,
        'is_public_schema': is_public,
        'platform_name': settings.PLATFORM_NAME,
        'tenant_subfolder_prefix': settings.TENANT_SUBFOLDER_PREFIX,
    }

    if not is_public and tenant:
        ctx.update({
            'hospital_name': tenant.name,
            'hospital_address': tenant.address,
            'hospital_phone': tenant.phone,
            'hospital_logo': tenant.logo,
            'hospital_primary_color': tenant.primary_color,
            'hospital_accent_color': tenant.accent_color,
            'tenant_subdomain': tenant.subdomain,
        })

    return ctx
