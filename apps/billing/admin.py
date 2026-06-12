from django.contrib import admin
from .models import (
    ServiceCatalog, ServicePrice, Invoice, InvoiceItem,
    Payment, InsuranceClaim, Refund, LedgerEntry,
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'patient', 'total_amount', 'amount_paid', 'status')
    list_filter = ('status',)
    inlines = [InvoiceItemInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'method', 'status', 'created_at')


admin.site.register(ServiceCatalog)
admin.site.register(ServicePrice)
admin.site.register(InsuranceClaim)
admin.site.register(Refund)
admin.site.register(LedgerEntry)
