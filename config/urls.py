# Legacy entry point — django-tenants uses urls_public / urls_tenant directly.
from config.urls_tenant import urlpatterns  # noqa: F401
