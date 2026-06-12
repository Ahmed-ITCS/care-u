import os

from .base import *  # noqa: F401,F403

DEBUG = False

# Render Postgres (and most managed providers) require SSL on external URLs.
_db_url = os.environ.get('DATABASE_URL', '')
if _db_url and env.bool('DB_SSLMODE_REQUIRE', default='sslmode=' not in _db_url):  # noqa: F405
    DATABASES['default'].setdefault('OPTIONS', {})  # noqa: F405
    DATABASES['default']['OPTIONS'].setdefault('sslmode', 'require')  # noqa: F405

# Fall back to DB sessions when no Redis is configured (common on first Render deploy).
_redis_url = os.environ.get('REDIS_URL', '')
if not _redis_url or _redis_url in ('redis://localhost:6379/0', 'redis://127.0.0.1:6379/0'):
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

SENTRY_DSN = env('SENTRY_DSN', default='')  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
    )

LOGGING['formatters']['json'] = {  # noqa: F405
    '()': 'django.utils.log.ServerFormatter',
    'format': '[{server_time}] {message}',
    'style': '{',
}
