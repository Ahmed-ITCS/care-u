from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from apps.core.list_filters import filter_list_context
from apps.notifications.filters import NotificationFilter
from apps.notifications.models import Notification


@login_required
def notification_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_all_read':
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            messages.success(request, 'All notifications marked as read.')
        elif action == 'mark_read':
            notif = get_object_or_404(Notification, pk=request.POST.get('notification_id'), user=request.user)
            notif.is_read = True
            notif.save(update_fields=['is_read', 'updated_at'])
        return redirect('notifications:list')

    queryset = Notification.objects.filter(user=request.user).order_by('-created_at')
    ctx = filter_list_context(
        request, queryset, NotificationFilter, limit=50, clear_url=reverse('notifications:list'),
    )
    ctx['notifications'] = ctx.pop('items')
    return render(request, 'notifications/list.html', ctx)
