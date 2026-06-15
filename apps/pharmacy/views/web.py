from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from apps.core.decorators import roles_required
from apps.core.list_filters import filter_list_context
from apps.pharmacy.filters import DrugFilter, PurchaseOrderFilter
from apps.pharmacy.forms import DrugForm, PurchaseOrderForm
from apps.pharmacy.models import Drug, Dispense, PurchaseOrder


@login_required
def inventory_list(request):
    queryset = Drug.objects.filter(is_active=True).select_related('category').order_by('generic_name')
    ctx = filter_list_context(
        request, queryset, DrugFilter, limit=100, clear_url=reverse('pharmacy:inventory'),
    )
    ctx['drugs'] = ctx.pop('items')
    return render(request, 'pharmacy/inventory.html', ctx)


@login_required
@roles_required('pharmacist', 'admin')
def drug_create(request):
    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Drug added to inventory.')
            return redirect('pharmacy:inventory')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = DrugForm()
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'Add Drug',
        'back_url': 'pharmacy:inventory',
        'submit_label': 'Add Drug',
    })


@login_required
def dispense_list(request):
    if request.method == 'POST':
        dispense = get_object_or_404(Dispense, pk=request.POST.get('dispense_id'))
        dispense.status = 'dispensed'
        dispense.dispensed_by = request.user
        dispense.save(update_fields=['status', 'dispensed_by', 'updated_at'])
        messages.success(request, f'Dispensed for {dispense.patient.full_name}.')
        return redirect('pharmacy:dispense')

    dispenses = Dispense.objects.filter(status='pending').select_related('patient', 'prescription')
    return render(request, 'pharmacy/dispense.html', {'dispenses': dispenses})


@login_required
@roles_required('pharmacist', 'admin')
def purchase_order_create(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            po = form.save(commit=False)
            po.created_by = request.user
            po.save()
            messages.success(request, f'Purchase order {po.po_number} created.')
            return redirect('pharmacy:purchase_orders')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = PurchaseOrderForm()
    return render(request, 'includes/model_form.html', {
        'form': form,
        'title': 'New Purchase Order',
        'back_url': 'pharmacy:purchase_orders',
        'submit_label': 'Create PO',
    })


@login_required
def purchase_order_list(request):
    queryset = PurchaseOrder.objects.select_related('supplier').order_by('-created_at')
    ctx = filter_list_context(
        request, queryset, PurchaseOrderFilter, limit=50, clear_url=reverse('pharmacy:purchase_orders'),
    )
    ctx['orders'] = ctx.pop('items')
    return render(request, 'pharmacy/purchase_orders.html', ctx)
