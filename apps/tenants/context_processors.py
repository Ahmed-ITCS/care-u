from django.conf import settings
from django.db import connection


def tenant_context(request):
    """Inject current tenant (hospital) info into all templates."""
    tenant = getattr(request, 'tenant', None) or getattr(connection, 'tenant', None)
    is_public = not tenant or getattr(tenant, 'schema_name', 'public') == 'public'

    ctx = {
        'current_tenant': None if is_public else tenant,
        'is_public_schema': is_public,
        'platform_name': settings.PLATFORM_NAME,
        'tenant_subfolder_prefix': settings.TENANT_SUBFOLDER_PREFIX,
        'demo_video_url': getattr(settings, 'DEMO_VIDEO_URL', ''),
    }

    if not is_public and tenant:
        prefix = settings.TENANT_SUBFOLDER_PREFIX.strip('/')
        subdomain = tenant.subdomain
        tenant_base = f'/{prefix}/{subdomain}/'
        ctx.update({
            'hospital_name': tenant.name,
            'hospital_address': tenant.address,
            'hospital_phone': tenant.phone,
            'hospital_logo': tenant.logo,
            'hospital_primary_color': tenant.primary_color,
            'hospital_accent_color': tenant.accent_color,
            'tenant_subdomain': subdomain,
            'tenant_base': tenant_base,
            'tenant_api_base': f'{tenant_base}api/v1/',
        })

    return ctx
