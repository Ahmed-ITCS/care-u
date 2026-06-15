import django_filters
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.pharmacy.models import Drug, DrugCategory, PurchaseOrder, Supplier


class DrugFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_search', label='Search')
    category = django_filters.ModelChoiceFilter(
        queryset=DrugCategory.objects.all().order_by('name'),
        empty_label='All categories',
    )
    form = django_filters.CharFilter(lookup_expr='icontains', label='Form')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock', label='Low stock only')

    layout = {
        'primary': ['q', 'category', 'form'],
        'groups': [
            {'label': 'Inventory', 'fields': ['low_stock']},
        ],
    }

    class Meta:
        model = Drug
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(generic_name__icontains=value)
            | Q(brand_name__icontains=value)
            | Q(barcode__icontains=value)
            | Q(strength__icontains=value)
        )

    def filter_low_stock(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            stock=Sum('batches__quantity', filter=Q(batches__expiry_date__gt=timezone.now().date()))
        ).filter(stock__lte=F('reorder_level'))


class PurchaseOrderFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(field_name='po_number', lookup_expr='icontains', label='PO Number')
    status = django_filters.ChoiceFilter(choices=PurchaseOrder.STATUS_CHOICES, empty_label='All statuses')
    supplier = django_filters.ModelChoiceFilter(
        queryset=Supplier.objects.filter(is_active=True).order_by('name'),
        empty_label='All suppliers',
    )
    order_from = django_filters.DateFilter(field_name='order_date', lookup_expr='gte', label='From')
    order_to = django_filters.DateFilter(field_name='order_date', lookup_expr='lte', label='To')

    layout = {
        'primary': ['q', 'status', 'supplier'],
        'groups': [
            {'label': 'Order date', 'fields': ['order_from', 'order_to']},
        ],
    }

    class Meta:
        model = PurchaseOrder
        fields = []
