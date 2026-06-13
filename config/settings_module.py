"""Default DJANGO_SETTINGS_MODULE for WSGI/ASGI/Celery entrypoints."""

import os


def default_settings_module() -> str:
    if os.environ.get('RENDER'):
        return 'config.settings.production'
    return 'config.settings.development'
