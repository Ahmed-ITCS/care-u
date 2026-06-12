from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.notifications.models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)[:50]
    return render(request, 'notifications/list.html', {'notifications': notifications})
