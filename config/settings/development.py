from .base import *  # noqa: F401,F403
import os

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

# Sessions must be shared across gunicorn workers. LocMemCache + cache sessions
# only lives in one worker process — login on worker A fails on worker B.
_redis_url = os.environ.get('REDIS_URL', '')  # noqa: F405
if _redis_url and _redis_url not in ('redis://localhost:6379/0', 'redis://127.0.0.1:6379/0'):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': _redis_url,
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Allow all localhost subdomains in dev
ALLOWED_HOSTS = ['*']
