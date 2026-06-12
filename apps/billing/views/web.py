from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from apps.billing.models import Invoice, Payment


@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related('patient').order_by('-created_at')[:50]
    if request.user.role == 'patient':
        invoices = invoices.filter(patient__user_account=request.user)
    return render(request, 'billing/invoices.html', {'invoices': invoices})


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.prefetch_related('items', 'payments'), pk=pk)
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})


@login_required
def payment_list(request):
    payments = Payment.objects.select_related('invoice', 'invoice__patient').order_by('-created_at')[:50]
    return render(request, 'billing/payments.html', {'payments': payments})


@login_required
def my_bills(request):
    invoices = Invoice.objects.filter(patient__user_account=request.user)
    return render(request, 'billing/my_bills.html', {'invoices': invoices})
