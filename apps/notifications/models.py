from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    TYPE_CHOICES = [
        ('appointment', 'Appointment'), ('lab_result', 'Lab Result'),
        ('bill', 'Bill'), ('stock_alert', 'Stock Alert'), ('system', 'System'), ('general', 'General'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username}: {self.title}'


class NotificationPreference(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_prefs')
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    appointment_reminders = models.BooleanField(default=True)
    lab_results = models.BooleanField(default=True)
    billing_alerts = models.BooleanField(default=True)

    def __str__(self):
        return f'Notification prefs: {self.user.username}'
