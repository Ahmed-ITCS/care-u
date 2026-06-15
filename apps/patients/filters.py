from django import forms
from django.db.models import Q

import django_filters

from apps.patients.models import Patient


class PatientFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(method='filter_search', label='Search')
    cnic = django_filters.CharFilter(lookup_expr='icontains', label='CNIC')
    mr_number = django_filters.CharFilter(lookup_expr='icontains', label='MR Number')
    phone = django_filters.CharFilter(lookup_expr='icontains', label='Phone')
    gender = django_filters.ChoiceFilter(choices=Patient.GENDER_CHOICES, empty_label='All genders')
    city = django_filters.CharFilter(lookup_expr='icontains', label='City')
    blood_group = django_filters.ChoiceFilter(
        choices=Patient.BLOOD_GROUP_CHOICES, empty_label='All blood groups',
    )
    dob_from = django_filters.DateFilter(field_name='date_of_birth', lookup_expr='gte', label='DOB from')
    dob_to = django_filters.DateFilter(field_name='date_of_birth', lookup_expr='lte', label='DOB to')

    layout = {
        'primary': ['q', 'cnic', 'gender', 'city'],
        'groups': [
            {
                'label': 'Registration',
                'fields': ['mr_number', 'phone', 'blood_group'],
            },
            {
                'label': 'Date of birth',
                'fields': ['dob_from', 'dob_to'],
            },
        ],
    }

    class Meta:
        model = Patient
        fields = []

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(mr_number__icontains=value)
            | Q(cnic__icontains=value)
            | Q(full_name__icontains=value)
            | Q(phone__icontains=value)
            | Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
        )
