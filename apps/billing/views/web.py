from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from apps.billing.filters import InvoiceFilter, PaymentFilter
from apps.billing.forms import InvoiceFromVisitForm, PaymentForm
from apps.billing.models import Invoice, Payment
from apps.billing.services import create_invoice_from_visit, record_payment
from apps.core.decorators import roles_required
from apps.core.list_filters import filter_list_context


@login_required
def invoice_list(request):
    queryset = Invoice.objects.select_related('patient').order_by('-created_at')
    if request.user.role == 'patient':
        queryset = queryset.filter(patient__user_account=request.user)
    ctx = filter_list_context(
        request, queryset, InvoiceFilter, limit=50, clear_url=reverse('billing:invoices'),
    )
    ctx['invoices'] = ctx.pop('items')
    return render(request, 'billing/invoices.html', ctx)


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.prefetch_related('items', 'payments'), pk=pk)
    if request.user.role == 'doctor':
        from apps.clinical.doctor_scope import doctor_can_access_patient
        if not doctor_can_access_patient(request.user, invoice.patient):
            messages.error(request, 'You do not have access to this invoice.')
            return redirect('patients:list')
    payment_form = None
    if request.user.role in ('admin', 'accountant', 'receptionist') and invoice.balance_due > 0:
        payment_form = PaymentForm(invoice=invoice)
    return render(request, 'billing/invoice_detail.html', {
        'invoice': invoice,
        'payment_form': payment_form,
    })


@login_required
@roles_required('accountant', 'receptionist', 'admin')
def invoice_create_from_visit(request):
    if request.method == 'POST':
        form = InvoiceFromVisitForm(request.POST)
        if form.is_valid():
            visit = form.cleaned_data['visit']
            invoice = create_invoice_from_visit(visit.id, request.user)
            messages.success(request, f'Invoice {invoice.invoice_number} created.')
            return redirect('billing:invoice_detail', pk=invoice.pk)
        messages.error(request, 'Please select a valid visit.')
    else:
        form = InvoiceFromVisitForm()
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'Create Invoice from Visit',
        'back_url': 'billing:invoices',
        'submit_label': 'Create Invoice',
    })


@login_required
@roles_required('accountant', 'receptionist', 'admin')
def payment_create(request, invoice_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST, invoice=invoice)
        if form.is_valid():
            record_payment(
                invoice,
                form.cleaned_data['amount'],
                form.cleaned_data['method'],
                request.user,
                form.cleaned_data.get('transaction_id', ''),
            )
            messages.success(request, 'Payment recorded.')
            return redirect('billing:invoice_detail', pk=invoice.pk)
        messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentForm(invoice=invoice)
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': f'Record Payment — {invoice.invoice_number}',
        'subtitle': f'Balance due: PKR {invoice.balance_due}',
        'back_href': reverse('billing:invoice_detail', kwargs={'pk': invoice.pk}),
        'submit_label': 'Record Payment',
    })


@login_required
def payment_list(request):
    queryset = Payment.objects.select_related('invoice', 'invoice__patient').order_by('-created_at')
    ctx = filter_list_context(
        request, queryset, PaymentFilter, limit=50, clear_url=reverse('billing:payments'),
    )
    ctx['payments'] = ctx.pop('items')
    return render(request, 'billing/payments.html', ctx)


@login_required
def my_bills(request):
    invoices = Invoice.objects.filter(patient__user_account=request.user)
    return render(request, 'billing/my_bills.html', {'invoices': invoices})
