"""Structured login/auth tracing — logs to stderr (visible in gunicorn/journalctl)."""
import logging

logger = logging.getLogger('careu.auth')


def client_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '?')


def session_snapshot(session) -> dict:
    return {
        'session_key': getattr(session, 'session_key', None),
        '_auth_user_id': session.get('_auth_user_id'),
        'tenant_subdomain': session.get('tenant_subdomain'),
        'tenant_schema': session.get('tenant_schema'),
    }


def log_auth(event: str, request, **extra):
    tenant = getattr(request, 'tenant', None)
    payload = {
        'event': event,
        'path': request.path,
        'method': request.method,
        'host': request.get_host(),
        'ip': client_ip(request),
        'schema': getattr(tenant, 'schema_name', None) if tenant else None,
        'user': getattr(request.user, 'username', None) if getattr(request, 'user', None) else None,
        'authenticated': getattr(getattr(request, 'user', None), 'is_authenticated', False),
        'session': session_snapshot(request.session),
    }
    payload.update(extra)
    parts = [f"{k}={v!r}" for k, v in payload.items()]
    logger.info(' | '.join(parts))
