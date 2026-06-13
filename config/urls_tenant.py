"""Tenant schema URL configuration — full ERP for each hospital."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('', include('apps.core.urls')),
    path('users/', include('apps.users.urls')),
    path('patients/', include('apps.patients.urls')),
    path('appointments/', include('apps.appointments.urls')),
    path('clinical/', include('apps.clinical.urls')),
    path('laboratory/', include('apps.laboratory.urls')),
    path('pharmacy/', include('apps.pharmacy.urls')),
    path('billing/', include('apps.billing.urls')),
    path('hr/', include('apps.hr.urls')),
    path('reports/', include('apps.reports.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('onboarding/', include('apps.tenants.urls_onboarding')),
    path('subscription/', include('apps.tenants.urls_billing')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass

admin.site.site_header = 'CARE-U Admin'
admin.site.site_title = 'Hospital Admin'
