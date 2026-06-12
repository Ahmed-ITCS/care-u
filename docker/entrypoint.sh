#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until python -c "
import os, psycopg2
conn = psycopg2.connect(
    dbname=os.environ.get('DB_NAME','gph_erp'),
    user=os.environ.get('DB_USER','gph'),
    password=os.environ.get('DB_PASSWORD','gph_secret'),
    host=os.environ.get('DB_HOST','db'),
    port=os.environ.get('DB_PORT','5432'),
)
conn.close()
" 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL is ready."

# TENANT: Migrate public schema first, then all tenant schemas
python manage.py migrate_schemas --shared
python manage.py migrate_schemas --tenant

python manage.py setup_public_tenant 2>/dev/null || true
python manage.py seed_plans 2>/dev/null || true
python manage.py create_platform_admin 2>/dev/null || true

case "$1" in
    web)
        python manage.py collectstatic --noinput 2>/dev/null || true
        exec python manage.py runserver 0.0.0.0:8000
        ;;
    celery)
        exec celery -A config worker -l info
        ;;
    beat)
        exec celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    channels)
        exec daphne -b 0.0.0.0 -p 8001 config.asgi:application
        ;;
    *)
        exec "$@"
        ;;
esac
