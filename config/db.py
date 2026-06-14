"""Database configuration helpers (SQLite local dev / PostgreSQL production)."""

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


def configure_databases(env, base_dir) -> tuple[dict, bool]:
    """
    Build DATABASES and whether SQLite single-DB mode is active.

    Default: SQLite (db.sqlite3) for simple local development.
    Set DB_ENGINE=postgres or DATABASE_URL for schema-based multi-tenancy.
    """
    engine = env('DB_ENGINE', default='sqlite').lower().strip()
    database_url = resolve_database_url()

    if engine == 'sqlite' and not database_url:
        sqlite_name = env('SQLITE_DB_NAME', default='db.sqlite3')
        return {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': base_dir / sqlite_name,
            }
        }, True

    if database_url:
        config = env.db_url_config(database_url)
        config['ENGINE'] = 'django_tenants.postgresql_backend'
        config.setdefault('CONN_MAX_AGE', env.int('DB_CONN_MAX_AGE', default=600))
        return {'default': config}, False

    return {
        'default': {
            'ENGINE': 'django_tenants.postgresql_backend',
            'NAME': env('DB_NAME', default='gph_erp'),
            'USER': env('DB_USER', default='gph'),
            'PASSWORD': env('DB_PASSWORD', default='gph_secret'),
            'HOST': env('DB_HOST', default='localhost'),
            'PORT': env('DB_PORT', default='5432'),
        }
    }, False
