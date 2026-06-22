import django_filters
from django.db.models import Q

from apps.billing.models import Invoice, Payment, ServiceCatalog


class InvoiceFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_search', label='Search')
    status = django_filters.ChoiceFilter(choices=Invoice.STATUS_CHOICES, empty_label='All statuses')
    patient_cnic = django_filters.CharFilter(
        field_name='patient__cnic', lookup_expr='icontains', label='Patient CNIC',
    )
    due_from = django_filters.DateFilter(field_name='due_date', lookup_expr='gte', label='Due from')
    due_to = django_filters.DateFilter(field_name='due_date', lookup_expr='lte', label='Due to')

    layout = {
        'primary': ['q', 'status', 'due_from', 'due_to'],
        'groups': [
            {'label': 'Patient', 'fields': ['patient_cnic']},
        ],
    }

    class Meta:
        model = Invoice
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(invoice_number__icontains=value)
            | Q(patient__full_name__icontains=value)
            | Q(patient__mr_number__icontains=value)
        )


class PaymentFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_search', label='Search')
    method = django_filters.ChoiceFilter(choices=Payment.METHOD_CHOICES, empty_label='All methods')
    status = django_filters.ChoiceFilter(choices=Payment.STATUS_CHOICES, empty_label='All statuses')
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte', label='Min amount')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte', label='Max amount')

    layout = {
        'primary': ['q', 'method', 'status'],
        'groups': [
            {'label': 'Amount', 'fields': ['amount_min', 'amount_max']},
        ],
    }

    class Meta:
        model = Payment
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(invoice__invoice_number__icontains=value)
            | Q(transaction_id__icontains=value)
            | Q(invoice__patient__full_name__icontains=value)
        )


class ServiceChargeFilter(django_filters.FilterSet):
    search_placeholder = 'Name, code, description...'
    q = django_filters.CharFilter(method='filter_search', label='Search')
    category = django_filters.ChoiceFilter(
        choices=ServiceCatalog.CATEGORY_CHOICES, empty_label='All categories',
    )
    is_active = django_filters.BooleanFilter(label='Active only')

    layout = {
        'primary': ['q', 'category', 'is_active'],
        'groups': [],
    }

    class Meta:
        model = ServiceCatalog
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(code__icontains=value)
            | Q(description__icontains=value)
        )
