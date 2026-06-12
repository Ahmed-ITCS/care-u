from functools import wraps
from django.shortcuts import redirect
from apps.tenants.models import PlatformUser


def platform_admin_required(view_func):
    """Decorator for super admin views — uses session-based PlatformUser auth."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('platform_user_id')
        if not user_id:
            return redirect('platform:login')
        try:
            request.platform_user = PlatformUser.objects.get(pk=user_id, is_active=True)
        except PlatformUser.DoesNotExist:
            return redirect('platform:login')
        return view_func(request, *args, **kwargs)

    return wrapper
