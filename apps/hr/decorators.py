from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if getattr(request.user, 'role', None) != 'admin':
            messages.error(request, 'Admin access required.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
