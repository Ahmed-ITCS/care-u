from django.utils import timezone
from apps.appointments.models import QueueEntry


def create_queue_entry(appointment):
    today = timezone.now().date()
    last_token = QueueEntry.objects.filter(
        created_at__date=today
    ).order_by('-token_number').first()
    token = (last_token.token_number + 1) if last_token else 1
    return QueueEntry.objects.create(
        appointment=appointment,
        token_number=token,
        priority=1 if appointment.appointment_type.code == 'EMRG' else 0,
    )
