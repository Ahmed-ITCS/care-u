from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def roles_required(*roles):
    """Allow admin or any of the given roles."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user_role = getattr(request.user, 'role', None)
            if user_role == 'admin' or user_role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('core:dashboard')

        return wrapper

    return decorator


def owner_required(view_func):
    """Hospital owner only (is_superuser — created at registration)."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            messages.error(request, 'Hospital owner access required.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper
