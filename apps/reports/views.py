from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse

from apps.reports.services import (
    generate_daily_opd_report,
    generate_revenue_report,
    generate_stock_report,
    export_report_excel,
    export_report_pdf,
)


@login_required
def reports_index(request):
    return render(request, 'reports/index.html')


@login_required
def daily_opd_report(request):
    data = generate_daily_opd_report()
    format_type = request.GET.get('format')
    if format_type == 'excel':
        return export_report_excel(data, 'Daily OPD Report')
    if format_type == 'pdf':
        return export_report_pdf(data, 'Daily OPD Report')
    return render(request, 'reports/daily_opd.html', {'data': data})


@login_required
def revenue_report(request):
    data = generate_revenue_report()
    format_type = request.GET.get('format')
    if format_type == 'excel':
        return export_report_excel(data, 'Revenue Report')
    if format_type == 'pdf':
        return export_report_pdf(data, 'Revenue Report')
    return render(request, 'reports/revenue.html', {'data': data})


@login_required
def stock_report(request):
    data = generate_stock_report()
    return render(request, 'reports/stock.html', {'data': data})
