from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.pharmacy.models import Drug, Dispense, PurchaseOrder


@login_required
def inventory_list(request):
    drugs = Drug.objects.filter(is_active=True).select_related('category')[:100]
    return render(request, 'pharmacy/inventory.html', {'drugs': drugs})


@login_required
def dispense_list(request):
    dispenses = Dispense.objects.filter(status='pending').select_related('patient', 'prescription')
    return render(request, 'pharmacy/dispense.html', {'dispenses': dispenses})


@login_required
def purchase_order_list(request):
    orders = PurchaseOrder.objects.select_related('supplier').order_by('-created_at')[:50]
    return render(request, 'pharmacy/purchase_orders.html', {'orders': orders})
