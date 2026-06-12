from django.contrib import admin
from .models import (
    DrugCategory, Drug, DrugBatch, StockMovement, Supplier,
    PurchaseOrder, PurchaseOrderItem, Dispense, DispenseItem,
)


class DrugBatchInline(admin.TabularInline):
    model = DrugBatch
    extra = 0


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ('generic_name', 'brand_name', 'strength', 'unit_price', 'is_active')
    search_fields = ('generic_name', 'brand_name', 'barcode')
    inlines = [DrugBatchInline]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'status', 'total_amount', 'order_date')


admin.site.register(DrugCategory)
admin.site.register(StockMovement)
admin.site.register(Supplier)
admin.site.register(PurchaseOrderItem)
admin.site.register(Dispense)
admin.site.register(DispenseItem)
