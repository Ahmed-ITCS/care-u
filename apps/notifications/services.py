from apps.notifications.models import Notification, NotificationPreference


def notify_user(user, title, message, notification_type='general', link=''):
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )
    prefs = getattr(user, 'notification_prefs', None)
    if prefs and prefs.push_enabled:
        from apps.notifications.tasks import push_notification
        push_notification.delay(user.id, title, message)


def get_or_create_prefs(user):
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    return prefs
