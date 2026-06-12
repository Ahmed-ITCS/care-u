from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_otp_email(user_id, code, purpose='login'):
    from apps.users.models import User
    try:
        user = User.objects.get(pk=user_id)
        subject = f'CARE-U - OTP for {purpose.replace("_", " ").title()}'
        message = f'Your OTP code is: {code}\n\nThis code expires in 10 minutes.\n\nGeneral Practice Hospital'
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception as e:
        logger.error(f'Failed to send OTP email: {e}')


@shared_task
def send_otp_sms(phone, code):
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
        logger.info(f'SMS OTP (console): {phone} -> {code}')
        return
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            body=f'CARE-U OTP: {code}. Valid for 10 minutes.',
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone,
        )
    except Exception as e:
        logger.error(f'Failed to send OTP SMS: {e}')
