import django_filters

from apps.appointments.models import Appointment, AppointmentType
from apps.core.filter_utils import patient_search_method
from apps.users.models import Role, User


class AppointmentFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_patient', label='Patient')
    status = django_filters.ChoiceFilter(choices=Appointment.STATUS_CHOICES, empty_label='All statuses')
    doctor = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(role=Role.DOCTOR).order_by('first_name', 'last_name'),
        empty_label='All doctors',
        label='Doctor',
    )
    appointment_type = django_filters.ModelChoiceFilter(
        queryset=AppointmentType.objects.filter(is_active=True).order_by('name'),
        empty_label='All types',
        label='Type',
    )
    source = django_filters.ChoiceFilter(choices=Appointment.SOURCE_CHOICES, empty_label='All sources')
    date_from = django_filters.DateFilter(field_name='scheduled_date', lookup_expr='gte', label='From')
    date_to = django_filters.DateFilter(field_name='scheduled_date', lookup_expr='lte', label='To')
    patient_cnic = django_filters.CharFilter(
        field_name='patient__cnic', lookup_expr='icontains', label='CNIC',
    )

    layout = {
        'primary': ['q', 'status', 'doctor', 'date_from', 'date_to'],
        'groups': [
            {'label': 'Details', 'fields': ['appointment_type', 'source', 'patient_cnic']},
        ],
    }

    class Meta:
        model = Appointment
        fields = []

    def filter_patient(self, queryset, name, value):
        return patient_search_method(queryset, value)
