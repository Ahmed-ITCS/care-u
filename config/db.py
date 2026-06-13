"""Database configuration helpers (Render / local dev)."""

from __future__ import annotations

import os

import environ


def resolve_database_url() -> str:
    """Return the first non-empty Postgres URL from known environment variables."""
    for key in (
        'DATABASE_URL',
        'INTERNAL_DATABASE_URL',
        'RENDER_DATABASE_URL',
        'POSTGRES_URL',
    ):
        value = os.environ.get(key, '').strip()
        if value:
            return value
    return ''


def is_local_database_host(host: str | None) -> bool:
    return (host or 'localhost').lower() in ('localhost', '127.0.0.1', '::1')


def configure_databases(env) -> dict:
    """
    Build DATABASES for django-tenants.

    Prefer DATABASE_URL (injected on Render when Postgres is linked).
    Fall back to DB_* variables for local development.
    """
    database_url = resolve_database_url()
    if database_url:
        config = environ.Env.db_url_config(database_url)
        config['ENGINE'] = 'django_tenants.postgresql_backend'
        config.setdefault('CONN_MAX_AGE', env.int('DB_CONN_MAX_AGE', default=600))
        return {'default': config}

    return {
        'default': {
            'ENGINE': 'django_tenants.postgresql_backend',
            'NAME': env('DB_NAME', default='gph_erp'),
            'USER': env('DB_USER', default='gph'),
            'PASSWORD': env('DB_PASSWORD', default='gph_secret'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }
