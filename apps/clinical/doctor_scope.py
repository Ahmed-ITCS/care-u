"""Helpers for scoping doctor-facing data to their own patients."""

from django.db.models import Q

from apps.patients.models import Patient


def doctor_patient_queryset(doctor):
    """Patients linked to this doctor via appointments, visits, or lab orders."""
    from apps.appointments.models import Appointment
    from apps.clinical.models import Visit
    from apps.laboratory.models import LabTestRequest

    patient_ids = set(
        Appointment.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    )
    patient_ids.update(
        Visit.objects.filter(doctor=doctor).values_list('patient_id', flat=True)
    )
    patient_ids.update(
        LabTestRequest.objects.filter(requested_by=doctor).values_list('patient_id', flat=True)
    )
    patient_ids.discard(None)
    if not patient_ids:
        return Patient.objects.none()
    return Patient.objects.filter(pk__in=patient_ids).distinct()


def doctor_can_access_patient(doctor, patient) -> bool:
    return doctor_patient_queryset(doctor).filter(pk=patient.pk).exists()


def doctor_lab_request_queryset(doctor):
    from apps.laboratory.models import LabTestRequest

    my_patients = doctor_patient_queryset(doctor)
    return LabTestRequest.objects.filter(
        Q(requested_by=doctor) | Q(patient__in=my_patients)
    ).distinct()


def doctor_outstanding_bills_queryset(doctor):
    """Queryset of doctor's patients with balance_due > 0."""
    from django.db.models import Sum, F, DecimalField, Value
    from django.db.models.functions import Coalesce

    return (
        doctor_patient_queryset(doctor)
        .annotate(
            total_billed=Coalesce(
                Sum('invoices__total_amount'), Value(0), output_field=DecimalField(),
            ),
            total_paid=Coalesce(
                Sum('invoices__amount_paid'), Value(0), output_field=DecimalField(),
            ),
        )
        .annotate(balance_due=F('total_billed') - F('total_paid'))
        .filter(balance_due__gt=0)
        .order_by('-balance_due')
    )


def doctor_patients_with_outstanding_bills(doctor, limit=20):
    """Patients in this doctor's care who still owe money."""
    qs = doctor_outstanding_bills_queryset(doctor)
    if limit is not None:
        qs = qs[:limit]

    return [
        {
            'patient': patient,
            'total_billed': patient.total_billed,
            'total_paid': patient.total_paid,
            'balance_due': patient.balance_due,
        }
        for patient in qs
    ]
