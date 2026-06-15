"""Shared filter helpers and patient-related field definitions."""

import django_filters
from django.db.models import Q


def search_filter(label='Search'):
    return django_filters.CharFilter(method='filter_search', label=label)


def patient_search_method(queryset, value, prefix='patient'):
    if not value:
        return queryset
    return queryset.filter(
        Q(**{f'{prefix}__full_name__icontains': value})
        | Q(**{f'{prefix}__mr_number__icontains': value})
        | Q(**{f'{prefix}__cnic__icontains': value})
        | Q(**{f'{prefix}__phone__icontains': value})
    )


PATIENT_FIELD_FILTERS = {
    'patient_cnic': django_filters.CharFilter(
        field_name='patient__cnic', lookup_expr='icontains', label='Patient CNIC',
    ),
    'patient_mr': django_filters.CharFilter(
        field_name='patient__mr_number', lookup_expr='icontains', label='MR Number',
    ),
    'patient_phone': django_filters.CharFilter(
        field_name='patient__phone', lookup_expr='icontains', label='Patient Phone',
    ),
}
