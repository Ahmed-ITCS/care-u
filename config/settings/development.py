from .base import *  # noqa: F401,F403

DEBUG = True

try:
    import debug_toolbar
    INSTALLED_APPS += ['debug_toolbar']  # noqa: F405
    MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')  # noqa: F405
    INTERNAL_IPS = ['127.0.0.1']
except ImportError:
    pass

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
CORS_ALLOW_ALL_ORIGINS = True

# Dev fallbacks when Redis unavailable
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Allow all localhost subdomains in dev
ALLOWED_HOSTS = ['*']
