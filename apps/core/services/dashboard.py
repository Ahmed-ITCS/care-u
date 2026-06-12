from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.core.cache import cache


def get_dashboard_kpis(user):
    cache_key = f'dashboard_kpis_{user.id}_{user.role}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    today = timezone.now().date()
    kpis = {}

    if user.role in ('admin', 'accountant', 'receptionist'):
        from apps.patients.models import Patient
        from apps.appointments.models import Appointment
        from apps.billing.models import Invoice, Payment
        from apps.pharmacy.models import DrugBatch

        kpis['patients_today'] = Patient.objects.filter(created_at__date=today).count()
        kpis['appointments_today'] = Appointment.objects.filter(scheduled_date=today).count()
        kpis['pending_bills'] = Invoice.objects.filter(status='pending').count()
        kpis['revenue_today'] = Payment.objects.filter(
            created_at__date=today, status='completed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        kpis['low_stock_alerts'] = DrugBatch.objects.filter(
            quantity__lte=10, expiry_date__gt=today
        ).count()

    if user.role == 'doctor':
        from apps.appointments.models import Appointment
        from apps.clinical.models import Prescription

        kpis['my_appointments_today'] = Appointment.objects.filter(
            doctor=user, scheduled_date=today
        ).count()
        kpis['pending_prescriptions'] = Prescription.objects.filter(
            doctor=user, status='active'
        ).count()

    if user.role == 'receptionist':
        from apps.appointments.models import QueueEntry
        kpis['queue_count'] = QueueEntry.objects.filter(
            status='waiting', created_at__date=today
        ).count()

    if user.role == 'pharmacist':
        from apps.pharmacy.models import Dispense, DrugBatch
        kpis['pending_dispenses'] = Dispense.objects.filter(status='pending').count()
        kpis['expiring_soon'] = DrugBatch.objects.filter(
            expiry_date__lte=today + timedelta(days=30),
            expiry_date__gt=today,
        ).count()

    if user.role == 'lab_tech':
        from apps.laboratory.models import LabTestRequest
        kpis['pending_samples'] = LabTestRequest.objects.filter(status='requested').count()
        kpis['pending_results'] = LabTestRequest.objects.filter(status='in_progress').count()

    cache.set(cache_key, kpis, 300)
    return kpis


def get_revenue_chart_data(days=30):
    from apps.billing.models import Payment
    end = timezone.now().date()
    start = end - timedelta(days=days)
    data = Payment.objects.filter(
        created_at__date__gte=start,
        status='completed',
    ).values('created_at__date').annotate(total=Sum('amount')).order_by('created_at__date')
    return {
        'labels': [str(d['created_at__date']) for d in data],
        'values': [float(d['total']) for d in data],
    }


def get_appointment_status_chart():
    from apps.appointments.models import Appointment
    data = Appointment.objects.values('status').annotate(count=Count('id'))
    return {
        'labels': [d['status'] for d in data],
        'values': [d['count'] for d in data],
    }


def get_patient_demographics():
    from apps.patients.models import Patient
    data = Patient.objects.values('gender').annotate(count=Count('id'))
    return {
        'labels': [d['gender'] or 'Unknown' for d in data],
        'values': [d['count'] for d in data],
    }
