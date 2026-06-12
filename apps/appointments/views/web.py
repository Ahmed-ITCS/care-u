from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from apps.appointments.models import Appointment, QueueEntry


@login_required
def appointment_list(request):
    today = timezone.now().date()
    appointments = Appointment.objects.filter(scheduled_date__gte=today).select_related(
        'patient', 'doctor', 'appointment_type'
    )[:50]
    return render(request, 'appointments/list.html', {'appointments': appointments})


@login_required
def doctor_calendar(request):
    return render(request, 'appointments/calendar.html')


@login_required
def queue_board(request):
    today = timezone.now().date()
    queue = QueueEntry.objects.filter(
        created_at__date=today
    ).select_related('appointment__patient', 'appointment__doctor')
    return render(request, 'appointments/queue.html', {'queue': queue})


@login_required
def my_appointments(request):
    if request.user.role == 'patient':
        appointments = Appointment.objects.filter(patient__user_account=request.user)
    else:
        appointments = Appointment.objects.filter(doctor=request.user)
    return render(request, 'appointments/my_appointments.html', {'appointments': appointments})
