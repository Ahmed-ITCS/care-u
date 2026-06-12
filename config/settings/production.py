from .base import *  # noqa: F401,F403

DEBUG = False

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
