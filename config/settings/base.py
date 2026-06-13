import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1', '.localhost']),
)

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-gph-dev-key-change-in-production')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# ---------------------------------------------------------------------------
# django-tenants: SHARED vs TENANT apps
# Public schema  → tenants, platform admin, landing page
# Tenant schemas → full ERP (patients, billing, etc.) — data isolated per hospital
# ---------------------------------------------------------------------------

SHARED_APPS = [
    'django_tenants',
    'apps.tenants',  # Hospital, Domain, PlatformUser, SubscriptionPlan
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'corsheaders',
    'rest_framework',
    'drf_spectacular',
]

TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_spectacular',
    'corsheaders',
    'auditlog',
    'django_celery_beat',
    'channels',
    'apps.core',
    'apps.users',
    'apps.patients',
    'apps.appointments',
    'apps.clinical',
    'apps.laboratory',
    'apps.pharmacy',
    'apps.billing',
    'apps.hr',
    'apps.reports',
    'apps.notifications',
    'apps.api',
]

INSTALLED_APPS = ['daphne'] + list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS and app != 'daphne'
]

# ---------------------------------------------------------------------------
# django-tenants configuration
# ---------------------------------------------------------------------------

TENANT_MODEL = 'tenants.Hospital'
TENANT_DOMAIN_MODEL = 'tenants.Domain'

# Public schema URLs (landing, registration, super admin)
PUBLIC_SCHEMA_URLCONF = 'config.urls_public'

# Tenant schema URLs (full ERP)
ROOT_URLCONF = 'config.urls_tenant'

# Path-based tenant fallback: yourdomain.com/h/gph-islamabad/
TENANT_SUBFOLDER_PREFIX = 'h/'
TENANT_USE_SUBFOLDER = env.bool('TENANT_USE_SUBFOLDER', default=True)
EXTRA_SET_TENANT_METHOD_PATH = 'apps.tenants.db.extra_set_tenant'

# Show public schema when no tenant matched (landing page)
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True

AUTH_USER_MODEL = 'users.User'  # TENANT: User model lives in each hospital schema

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Middleware — tenant resolver MUST be first
if TENANT_USE_SUBFOLDER:
    TENANT_MIDDLEWARE = 'apps.tenants.middleware.TenantSubfolderMiddleware'
else:
    TENANT_MIDDLEWARE = 'django_tenants.middleware.TenantMainMiddleware'

MIDDLEWARE = [
    TENANT_MIDDLEWARE,
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'apps.tenants.middleware.PublicSchemaSessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'apps.tenants.middleware.PublicSchemaAuthGuardMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.tenants.middleware.TenantSessionAuthMiddleware',
    'apps.tenants.middleware.TenantAccessMiddleware',
    'apps.tenants.middleware.PlanModuleMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    # Must be last — runs immediately before the view, after auth/session/auditlog
    'apps.tenants.middleware.TenantSubfolderGuardMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.tenants.context_processors.tenant_context',
                'apps.core.context_processors.hospital_context',
                'apps.core.context_processors.navigation_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# PostgreSQL required for schema-based multi-tenancy.
# Prefer DATABASE_URL (set automatically on Render when Postgres is linked).
_database_url = env('DATABASE_URL', default='')
if _database_url:
    DATABASES = {
        'default': env.db('DATABASE_URL'),
    }
    DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'
    DATABASES['default'].setdefault('CONN_MAX_AGE', env.int('DB_CONN_MAX_AGE', default=600))
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django_tenants.postgresql_backend',
            'NAME': env('DB_NAME', default='gph_erp'),
            'USER': env('DB_USER', default='gph'),
            'PASSWORD': env('DB_PASSWORD', default='gph_secret'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }

DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Redis
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Celery
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [REDIS_URL]},
    },
}

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'login': '10/minute',
        'otp': '5/minute',
    },
    'EXCEPTION_HANDLER': 'apps.api.exceptions.custom_exception_handler',
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'CARE-U API',
    'DESCRIPTION': 'Multi-tenant hospital management platform',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:8000'])
CORS_ALLOW_ALL_ORIGINS = DEBUG

# Email
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@care-u.com')

# Twilio
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = env('TWILIO_PHONE_NUMBER', default='')

# SaaS platform settings
PLATFORM_NAME = env('PLATFORM_NAME', default='CARE-U')
BASE_DOMAIN = env('BASE_DOMAIN', default='localhost')
TRIAL_DAYS = env.int('TRIAL_DAYS', default=14)

# Stripe placeholders
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')

# AWS S3 (optional)
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY', default='')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='ap-south-1')

if AWS_STORAGE_BUCKET_NAME:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_FILE_OVERWRITE = False

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = '/login/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
    },
}

AUDITLOG_INCLUDE_ALL_MODELS = False
