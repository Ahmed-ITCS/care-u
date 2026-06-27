from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.clinical.models import Visit
from apps.appointments.services import sync_queue_from_visit


@receiver(post_save, sender=Visit)
def visit_queue_sync(sender, instance, **kwargs):
    sync_queue_from_visit(instance)
