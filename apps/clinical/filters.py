import django_filters

from apps.clinical.models import Visit
from apps.core.filter_utils import patient_search_method
from apps.users.models import Role, User


class VisitFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_patient', label='Patient')
    visit_type = django_filters.ChoiceFilter(choices=Visit.VISIT_TYPES, empty_label='All types')
    status = django_filters.ChoiceFilter(choices=Visit.STATUS_CHOICES, empty_label='All statuses')
    doctor = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(role=Role.DOCTOR).order_by('first_name', 'last_name'),
        empty_label='All doctors',
        label='Doctor',
    )
    date_from = django_filters.DateFilter(field_name='visit_date', lookup_expr='date__gte', label='From')
    date_to = django_filters.DateFilter(field_name='visit_date', lookup_expr='date__lte', label='To')
    patient_cnic = django_filters.CharFilter(
        field_name='patient__cnic', lookup_expr='icontains', label='CNIC',
    )

    layout = {
        'primary': ['q', 'visit_type', 'status', 'doctor'],
        'groups': [
            {'label': 'Date range', 'fields': ['date_from', 'date_to']},
            {'label': 'Patient', 'fields': ['patient_cnic']},
        ],
    }

    class Meta:
        model = Visit
        fields = []

    def filter_patient(self, queryset, name, value):
        return patient_search_method(queryset, value)
