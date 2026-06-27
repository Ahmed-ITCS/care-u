from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone


def _card(label, value, tone='primary', format_type='number'):
    return {
        'label': label,
        'value': value,
        'tone': tone,
        'format': format_type,
    }


def get_dashboard_stat_cards(user):
    cache_key = f'dashboard_cards_{user.id}_{user.role}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    today = timezone.now().date()
    role = user.role
    cards = []

    if role == 'admin':
        from apps.patients.models import Patient
        from apps.appointments.models import Appointment
        from apps.billing.models import Invoice, Payment

        cards = [
            _card('Patients Today', Patient.objects.filter(created_at__date=today).count()),
            _card('Appointments Today', Appointment.objects.filter(scheduled_date=today).count(), 'secondary'),
            _card('Pending Bills', Invoice.objects.filter(status__in=['pending', 'partial']).count(), 'warning'),
            _card(
                'Revenue Today',
                Payment.objects.filter(created_at__date=today, status='completed').aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0'),
                'accent',
                'currency',
            ),
        ]

    elif role == 'accountant':
        from apps.billing.models import Invoice, Payment

        cards = [
            _card('Pending Bills', Invoice.objects.filter(status__in=['pending', 'partial']).count(), 'warning'),
            _card(
                'Revenue Today',
                Payment.objects.filter(created_at__date=today, status='completed').aggregate(
                    total=Sum('amount')
                )['total'] or Decimal('0'),
                'accent',
                'currency',
            ),
            _card('Payments Today', Payment.objects.filter(created_at__date=today, status='completed').count(), 'secondary'),
            _card(
                'Overdue Invoices',
                Invoice.objects.filter(
                    due_date__lt=today,
                    status__in=['pending', 'partial'],
                ).count(),
                'primary',
            ),
        ]

    elif role == 'receptionist':
        from apps.patients.models import Patient
        from apps.appointments.models import Appointment, QueueEntry
        from apps.billing.models import Invoice

        cards = [
            _card('Queue Waiting', QueueEntry.objects.filter(status='waiting', created_at__date=today).count()),
            _card('Appointments Today', Appointment.objects.filter(scheduled_date=today).count(), 'secondary'),
            _card('Patients Today', Patient.objects.filter(created_at__date=today).count(), 'primary'),
            _card('Pending Bills', Invoice.objects.filter(status__in=['pending', 'partial']).count(), 'warning'),
        ]

    elif role == 'doctor':
        from apps.appointments.models import Appointment
        from apps.clinical.models import Prescription, Visit
        from apps.clinical.doctor_scope import doctor_outstanding_bills_queryset

        cards = [
            _card('My Appointments Today', Appointment.objects.filter(doctor=user, scheduled_date=today).count()),
            _card(
                'Open Visits',
                Visit.objects.filter(doctor=user, status__in=['open', 'in_progress']).count(),
                'secondary',
            ),
            _card('Pending Prescriptions', Prescription.objects.filter(doctor=user, status='active').count(), 'warning'),
            _card(
                'Outstanding Bill Patients',
                doctor_outstanding_bills_queryset(user).count(),
                'accent',
            ),
        ]

    elif role == 'nurse':
        from apps.clinical.models import Admission, Bed, Visit
        from apps.hr.models import StaffShiftAssignment

        cards = [
            _card('My Shifts Today', StaffShiftAssignment.objects.filter(staff=user, date=today).count()),
            _card('Active Admissions', Admission.objects.filter(is_active=True).count(), 'secondary'),
            _card('Occupied Beds', Bed.objects.filter(status='occupied').count(), 'warning'),
            _card('Open Visits', Visit.objects.filter(status__in=['open', 'in_progress']).count(), 'accent'),
        ]

    elif role == 'pharmacist':
        from apps.pharmacy.models import Dispense, DrugBatch, PurchaseOrder

        cards = [
            _card('Pending Dispenses', Dispense.objects.filter(status='pending').count()),
            _card(
                'Expiring Soon',
                DrugBatch.objects.filter(
                    expiry_date__lte=today + timedelta(days=30),
                    expiry_date__gt=today,
                ).count(),
                'warning',
            ),
            _card(
                'Low Stock Items',
                DrugBatch.objects.filter(quantity__lte=10, expiry_date__gt=today).count(),
                'secondary',
            ),
            _card('Open Purchase Orders', PurchaseOrder.objects.filter(status='ordered').count(), 'accent'),
        ]

    elif role == 'lab_tech':
        from apps.laboratory.models import LabTestRequest

        cards = [
            _card('Awaiting Collection', LabTestRequest.objects.filter(status='requested').count()),
            _card('Samples Collected', LabTestRequest.objects.filter(status='collected').count(), 'secondary'),
            _card('Results In Progress', LabTestRequest.objects.filter(status='in_progress').count(), 'warning'),
            _card('Completed Today', LabTestRequest.objects.filter(status='completed', updated_at__date=today).count(), 'accent'),
        ]

    elif role == 'patient':
        from apps.appointments.models import Appointment
        from apps.billing.models import Invoice
        from apps.laboratory.models import LabTestRequest
        from apps.notifications.models import Notification

        patient = getattr(user, 'patient_profile', None)
        if patient:
            cards = [
                _card(
                    'Upcoming Appointments',
                    Appointment.objects.filter(
                        patient=patient,
                        scheduled_date__gte=today,
                        status__in=['scheduled', 'confirmed'],
                    ).count(),
                ),
                _card(
                    'Unpaid Bills',
                    Invoice.objects.filter(patient=patient, status__in=['pending', 'partial']).count(),
                    'warning',
                ),
                _card(
                    'Pending Lab Tests',
                    LabTestRequest.objects.filter(
                        patient=patient,
                        status__in=['requested', 'collected', 'in_progress'],
                    ).count(),
                    'secondary',
                ),
                _card(
                    'Unread Notifications',
                    Notification.objects.filter(user=user, is_read=False).count(),
                    'accent',
                ),
            ]
        else:
            cards = [
                _card('Upcoming Appointments', 0),
                _card('Unpaid Bills', 0, 'warning'),
                _card('Pending Lab Tests', 0, 'secondary'),
                _card('Unread Notifications', Notification.objects.filter(user=user, is_read=False).count(), 'accent'),
            ]

    cache.set(cache_key, cards, 300)
    return cards


def get_dashboard_kpis(user):
    """Legacy dict of KPI values derived from stat cards."""
    return {card['label'].lower().replace(' ', '_'): card['value'] for card in get_dashboard_stat_cards(user)}


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
    from django.db.models import Count
    from apps.appointments.models import Appointment

    data = Appointment.objects.values('status').annotate(count=Count('id'))
    return {
        'labels': [d['status'] for d in data],
        'values': [d['count'] for d in data],
    }


def get_patient_demographics():
    from django.db.models import Count
    from apps.patients.models import Patient

    data = Patient.objects.values('gender').annotate(count=Count('id'))
    return {
        'labels': [d['gender'] or 'Unknown' for d in data],
        'values': [d['count'] for d in data],
    }
