import django_filters

from apps.hr.models import Attendance, LeaveRequest, PayrollRun
from apps.users.models import Role, User


class AttendanceFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(label='Date')
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte', label='From')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte', label='To')
    staff = django_filters.ModelChoiceFilter(
        queryset=User.objects.exclude(role=Role.PATIENT).order_by('first_name', 'last_name'),
        empty_label='All staff',
    )
    status = django_filters.ChoiceFilter(choices=Attendance.STATUS_CHOICES, empty_label='All statuses')

    layout = {
        'primary': ['date', 'staff', 'status'],
        'groups': [
            {'label': 'Date range', 'fields': ['date_from', 'date_to']},
        ],
    }

    class Meta:
        model = Attendance
        fields = []


class LeaveRequestFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=LeaveRequest.STATUS_CHOICES, empty_label='All statuses')
    leave_type = django_filters.ChoiceFilter(choices=LeaveRequest.LEAVE_TYPES, empty_label='All types')
    staff = django_filters.ModelChoiceFilter(
        queryset=User.objects.exclude(role=Role.PATIENT).order_by('first_name', 'last_name'),
        empty_label='All staff',
    )
    from_date = django_filters.DateFilter(field_name='start_date', lookup_expr='gte', label='From')
    to_date = django_filters.DateFilter(field_name='end_date', lookup_expr='lte', label='To')

    layout = {
        'primary': ['status', 'leave_type', 'staff'],
        'groups': [
            {'label': 'Date range', 'fields': ['from_date', 'to_date']},
        ],
    }

    class Meta:
        model = LeaveRequest
        fields = []


class PayrollRunFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=PayrollRun.STATUS_CHOICES, empty_label='All statuses')
    year = django_filters.NumberFilter(label='Year')
    month = django_filters.NumberFilter(label='Month')

    layout = {
        'primary': ['status', 'year', 'month'],
        'groups': [],
    }

    class Meta:
        model = PayrollRun
        fields = []
