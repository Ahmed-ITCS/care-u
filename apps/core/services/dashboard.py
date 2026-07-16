from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone


# Icon path data (Heroicons outline) for the executive KPI cards.
_ICON_USERS = "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"
_ICON_QUEUE = "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
_ICON_REVENUE = "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
_ICON_PILL = "M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
_ICON_BED = "M3 12h18M3 12V7a1 1 0 011-1h6a1 1 0 011 1v5m0 0v5m0-5h3m0 0v5m0-5h3a1 1 0 011 1v4M3 12v4a1 1 0 001 1h16a1 1 0 001-1v-4"
_ICON_CALENDAR = "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
_ICON_FLASK = "M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2v-4M9 21H5a2 2 0 01-2-2v-4m0 0h18"
_ICON_ALERT = "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"


def get_executive_kpis(user):
    """Hospital-wide enterprise KPI cards shown at the top of the dashboard."""
    cache_key = f'exec_kpis_{user.id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    today = timezone.now().date()

    from apps.patients.models import Patient
    from apps.appointments.models import Appointment, QueueEntry
    from apps.billing.models import Invoice, Payment
    from apps.pharmacy.models import Dispense, DrugBatch
    from apps.clinical.models import Bed
    from apps.laboratory.models import LabTestRequest

    patients_today = Patient.objects.filter(created_at__date=today).count()
    current_queue = QueueEntry.objects.filter(status='waiting', created_at__date=today).count()
    revenue_today = Payment.objects.filter(
        created_at__date=today, status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    pharmacy_sales = Dispense.objects.filter(
        status='dispensed', created_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    occupied = Bed.objects.filter(status='occupied').count()
    total_beds = Bed.objects.count()
    bed_occupancy = round(occupied / total_beds * 100) if total_beds else 0

    appointments = Appointment.objects.filter(scheduled_date=today).count()
    pending_lab = LabTestRequest.objects.filter(
        status__in=['requested', 'collected', 'in_progress']
    ).count()

    overdue = Invoice.objects.filter(
        due_date__lt=today, status__in=['pending', 'partial']
    ).count()
    low_stock = DrugBatch.objects.filter(quantity__lte=10, expiry_date__gt=today).count()
    expiring = DrugBatch.objects.filter(
        expiry_date__lte=today + timedelta(days=30), expiry_date__gt=today
    ).count()
    urgent_lab = LabTestRequest.objects.filter(
        priority__in=['urgent', 'stat'],
        status__in=['requested', 'collected', 'in_progress'],
    ).count()
    critical_alerts = overdue + low_stock + expiring + urgent_lab

    kpis = [
        {'label': "Today's Patients", 'value': patients_today, 'format': 'number',
         'color': '#4F46E5', 'icon': _ICON_USERS, 'sub': 'New registrations today'},
        {'label': 'Current Queue', 'value': current_queue, 'format': 'number',
         'color': '#0EA5E9', 'icon': _ICON_QUEUE, 'sub': 'Patients waiting now'},
        {'label': 'Revenue Today', 'value': revenue_today, 'format': 'currency',
         'color': '#059669', 'icon': _ICON_REVENUE, 'sub': 'Collected payments'},
        {'label': 'Pharmacy Sales', 'value': pharmacy_sales, 'format': 'currency',
         'color': '#7C3AED', 'icon': _ICON_PILL, 'sub': 'Dispensed today'},
        {'label': 'Bed Occupancy', 'value': bed_occupancy, 'format': 'percent',
         'color': '#D97706', 'icon': _ICON_BED, 'sub': f'{occupied} of {total_beds} beds'},
        {'label': 'Appointments', 'value': appointments, 'format': 'number',
         'color': '#2563EB', 'icon': _ICON_CALENDAR, 'sub': 'Scheduled today'},
        {'label': 'Pending Lab Reports', 'value': pending_lab, 'format': 'number',
         'color': '#EA580C', 'icon': _ICON_FLASK, 'sub': 'Awaiting results'},
        {'label': 'Critical Alerts', 'value': critical_alerts, 'format': 'number',
         'color': '#E11D48', 'icon': _ICON_ALERT, 'sub': 'Need attention'},
    ]
    cache.set(cache_key, kpis, 300)
    return kpis


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
