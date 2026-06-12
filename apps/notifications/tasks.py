from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_email_notification(user_id, subject, message):
    from django.core.mail import send_mail
    from django.conf import settings
    from apps.users.models import User
    try:
        user = User.objects.get(pk=user_id)
        if user.email:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception as e:
        logger.error(f'Email notification failed: {e}')


@shared_task
def send_sms_notification(phone, message):
    from django.conf import settings
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN]):
        logger.info(f'SMS (console): {phone} -> {message}')
        return
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=settings.TWILIO_PHONE_NUMBER, to=phone)
    except Exception as e:
        logger.error(f'SMS notification failed: {e}')


@shared_task
def push_notification(user_id, title, message):
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user_id}',
            {'type': 'notification_message', 'title': title, 'message': message},
        )
