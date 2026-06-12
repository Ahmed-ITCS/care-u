# Public schema URL configuration — landing, registration, super admin.
# NOTE: django.contrib.admin is tenant-only; public uses custom platform views.

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.tenants.views import api_auth

urlpatterns = [
    path('', include('apps.tenants.urls_public')),
    path('platform/', include(('apps.tenants.urls_platform', 'platform'), namespace='platform')),
    # Unified API login — no /h/{subdomain}/ prefix needed
    path('api/v1/auth/login/', api_auth.unified_api_login, name='unified-api-login'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
