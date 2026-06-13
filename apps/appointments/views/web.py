from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from apps.appointments.forms import AppointmentForm
from apps.appointments.models import Appointment, QueueEntry
from apps.core.decorators import roles_required


@login_required
def appointment_list(request):
    today = timezone.now().date()
    appointments = Appointment.objects.filter(scheduled_date__gte=today).select_related(
        'patient', 'doctor', 'appointment_type'
    )[:50]
    return render(request, 'appointments/list.html', {'appointments': appointments})


@login_required
@roles_required('receptionist', 'admin')
def appointment_create(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.booked_by = request.user
            appt.save()
            messages.success(request, 'Appointment booked.')
            return redirect('appointments:list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = AppointmentForm()
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'Book Appointment',
        'back_url': 'appointments:list',
        'submit_label': 'Book',
    })


@login_required
@roles_required('receptionist', 'admin', 'doctor')
def appointment_edit(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appt)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated.')
            return redirect('appointments:list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = AppointmentForm(instance=appt)
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'Edit Appointment',
        'back_url': 'appointments:list',
        'submit_label': 'Save',
    })


@login_required
def doctor_calendar(request):
    today = timezone.now().date()
    appointments = Appointment.objects.filter(
        scheduled_date__gte=today,
    ).select_related('patient', 'doctor')[:100]
    return render(request, 'appointments/calendar.html', {'appointments': appointments})


@login_required
def queue_board(request):
    today = timezone.now().date()
    if request.method == 'POST':
        entry_id = request.POST.get('entry_id')
        action = request.POST.get('action')
        entry = get_object_or_404(QueueEntry, pk=entry_id)
        if action == 'call':
            entry.status = 'called'
            entry.called_at = timezone.now()
            entry.save(update_fields=['status', 'called_at', 'updated_at'])
            messages.success(request, f'Called token #{entry.token_number}.')
        elif action == 'complete':
            entry.status = 'completed'
            entry.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Marked as completed.')
        return redirect('appointments:queue')

    queue = QueueEntry.objects.filter(
        created_at__date=today,
        status__in=['waiting', 'called', 'in_consultation'],
    ).select_related('appointment__patient', 'appointment__doctor')
    return render(request, 'appointments/queue.html', {'queue': queue})


@login_required
def my_appointments(request):
    if request.user.role == 'patient':
        appointments = Appointment.objects.filter(patient__user_account=request.user)
    else:
        appointments = Appointment.objects.filter(doctor=request.user)
    return render(request, 'appointments/my_appointments.html', {'appointments': appointments})
