import django_filters
from django.db.models import Q

from apps.laboratory.models import LabTestRequest


class LabTestRequestFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_search', label='Search')
    status = django_filters.ChoiceFilter(choices=LabTestRequest.STATUS_CHOICES, empty_label='All statuses')
    priority = django_filters.CharFilter(lookup_expr='iexact', label='Priority')
    patient_cnic = django_filters.CharFilter(
        field_name='patient__cnic', lookup_expr='icontains', label='Patient CNIC',
    )

    layout = {
        'primary': ['q', 'status', 'priority'],
        'groups': [
            {'label': 'Patient', 'fields': ['patient_cnic']},
        ],
    }

    class Meta:
        model = LabTestRequest
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(request_number__icontains=value)
            | Q(patient__full_name__icontains=value)
            | Q(patient__mr_number__icontains=value)
            | Q(patient__cnic__icontains=value)
        )
