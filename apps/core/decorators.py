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
