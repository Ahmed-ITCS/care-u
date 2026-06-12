from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_appointment_reminders():
    from apps.appointments.models import Appointment
    from apps.notifications.services import notify_user
    from apps.notifications.tasks import send_email_notification, send_sms_notification

    now = timezone.now()

    # 24h reminders
    tomorrow = now.date() + timedelta(days=1)
    appointments_24h = Appointment.objects.filter(
        scheduled_date=tomorrow,
        status__in=['scheduled', 'confirmed'],
        reminder_sent_24h=False,
    )
    for appt in appointments_24h:
        msg = f'Reminder: Appointment with Dr.{appt.doctor.get_full_name()} on {appt.scheduled_date} at {appt.scheduled_time}'
        if appt.patient.user_account:
            notify_user(appt.patient.user_account, 'Appointment Reminder', msg, 'appointment')
        if appt.patient.email:
            send_email_notification.delay(0, 'Appointment Reminder', msg)
        if appt.patient.phone:
            send_sms_notification.delay(appt.patient.phone, msg)
        appt.reminder_sent_24h = True
        appt.save(update_fields=['reminder_sent_24h'])

    # 2h reminders
    two_hours = now + timedelta(hours=2)
    appointments_2h = Appointment.objects.filter(
        scheduled_date=now.date(),
        scheduled_time__lte=two_hours.time(),
        status__in=['scheduled', 'confirmed'],
        reminder_sent_2h=False,
    )
    for appt in appointments_2h:
        msg = f'Your appointment is in 2 hours at {appt.scheduled_time}'
        if appt.patient.user_account:
            notify_user(appt.patient.user_account, 'Appointment Soon', msg, 'appointment')
        appt.reminder_sent_2h = True
        appt.save(update_fields=['reminder_sent_2h'])


@shared_task
def check_stock_alerts():
    from django.utils import timezone
    from apps.pharmacy.models import DrugBatch, Drug
    from apps.notifications.models import Notification
    from apps.users.models import User, Role

    today = timezone.now().date()
    pharmacists = User.objects.filter(role=Role.PHARMACIST, is_active=True)

    low_stock = DrugBatch.objects.filter(quantity__lte=10, expiry_date__gt=today)
    for batch in low_stock:
        for user in pharmacists:
            Notification.objects.create(
                user=user,
                title='Low Stock Alert',
                message=f'{batch.drug.generic_name} (Batch {batch.batch_number}) has only {batch.quantity} units left.',
                notification_type='stock_alert',
            )

    expiring = DrugBatch.objects.filter(
        expiry_date__lte=today + timedelta(days=30),
        expiry_date__gt=today,
        quantity__gt=0,
    )
    for batch in expiring:
        for user in pharmacists:
            Notification.objects.create(
                user=user,
                title='Expiry Alert',
                message=f'{batch.drug.generic_name} (Batch {batch.batch_number}) expires on {batch.expiry_date}.',
                notification_type='stock_alert',
            )
