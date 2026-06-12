from django.utils import timezone
from django.db.models import Count, Sum
from datetime import timedelta


def generate_daily_opd_report(date=None):
    from apps.clinical.models import Visit
    from apps.appointments.models import Appointment

    date = date or timezone.now().date()
    visits = Visit.objects.filter(visit_date__date=date, visit_type='opd')
    appointments = Appointment.objects.filter(scheduled_date=date)

    return {
        'date': str(date),
        'total_visits': visits.count(),
        'completed_visits': visits.filter(status='completed').count(),
        'total_appointments': appointments.count(),
        'no_shows': appointments.filter(status='no_show').count(),
        'visits': list(visits.values('patient__full_name', 'doctor__first_name', 'status')[:50]),
    }


def generate_revenue_report(days=30):
    from apps.billing.models import Payment, Invoice

    end = timezone.now().date()
    start = end - timedelta(days=days)
    payments = Payment.objects.filter(
        created_at__date__gte=start, status='completed'
    ).aggregate(total=Sum('amount'), count=Count('id'))

    outstanding = Invoice.objects.filter(
        status__in=['pending', 'partial']
    ).aggregate(total=Sum('total_amount'), count=Count('id'))

    return {
        'period': f'{start} to {end}',
        'total_collected': float(payments['total'] or 0),
        'payment_count': payments['count'],
        'outstanding_amount': float(outstanding['total'] or 0),
        'outstanding_count': outstanding['count'],
    }


def generate_stock_report():
    from apps.pharmacy.models import Drug, DrugBatch
    from django.utils import timezone

    today = timezone.now().date()
    low_stock = DrugBatch.objects.filter(quantity__lte=10).select_related('drug')[:20]
    expiring = DrugBatch.objects.filter(
        expiry_date__lte=today + timedelta(days=30),
        expiry_date__gt=today,
        quantity__gt=0,
    ).select_related('drug')[:20]

    return {
        'total_drugs': Drug.objects.filter(is_active=True).count(),
        'low_stock': [{'drug': b.drug.generic_name, 'batch': b.batch_number, 'qty': b.quantity} for b in low_stock],
        'expiring': [{'drug': b.drug.generic_name, 'batch': b.batch_number, 'expiry': str(b.expiry_date)} for b in expiring],
    }


def export_report_excel(data, title):
    from openpyxl import Workbook
    from django.http import HttpResponse

    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(['Report', title])
    ws.append(['Generated', str(timezone.now())])
    ws.append([])
    for key, value in data.items():
        if not isinstance(value, (list, dict)):
            ws.append([str(key), str(value)])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}.xlsx"'
    wb.save(response)
    return response


def export_report_pdf(data, title):
    from django.http import HttpResponse

    try:
        from weasyprint import HTML
        html = f'<html><body><h1>{title}</h1><p>Generated: {timezone.now()}</p><table>'
        for key, value in data.items():
            if not isinstance(value, (list, dict)):
                html += f'<tr><td>{key}</td><td>{value}</td></tr>'
        html += '</table></body></html>'
        pdf = HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}.pdf"'
        return response
    except Exception:
        return HttpResponse(f'PDF generation unavailable. Data: {data}')
