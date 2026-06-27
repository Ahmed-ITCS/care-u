from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.appointments.models import Appointment
from apps.appointments.services import sync_queue_on_appointment_save


@receiver(post_save, sender=Appointment)
def appointment_queue_sync(sender, instance, created, **kwargs):
    sync_queue_on_appointment_save(instance, created)
