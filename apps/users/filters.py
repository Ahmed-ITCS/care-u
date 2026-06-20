import django_filters
from django.db.models import Q

from apps.core.models import Department
from apps.users.models import Role, User


STAFF_ROLES = [choice for choice in Role.choices if choice[0] != Role.PATIENT]


class StaffUserFilter(django_filters.FilterSet):
    search_placeholder = 'Name, username, email, phone...'
    q = django_filters.CharFilter(method='filter_search', label='Search')
    role = django_filters.ChoiceFilter(choices=STAFF_ROLES, empty_label='All roles')
    is_active = django_filters.BooleanFilter(label='Active only')
    cnic = django_filters.CharFilter(
        field_name='staff_profile__cnic', lookup_expr='icontains', label='CNIC',
    )
    department = django_filters.ModelChoiceFilter(
        field_name='staff_profile__department',
        queryset=Department.objects.all().order_by('name'),
        empty_label='All departments',
    )

    layout = {
        'primary': ['q', 'role', 'is_active'],
        'groups': [
            {'label': 'Profile', 'fields': ['cnic', 'department']},
        ],
    }

    class Meta:
        model = User
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(username__icontains=value)
            | Q(email__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(phone__icontains=value)
        )
