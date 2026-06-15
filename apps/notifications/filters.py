import django_filters

from apps.notifications.models import Notification


class NotificationFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(field_name='title', lookup_expr='icontains', label='Search')
    is_read = django_filters.BooleanFilter(label='Read')
    notification_type = django_filters.ChoiceFilter(
        choices=Notification.TYPE_CHOICES,
        empty_label='All types',
        label='Type',
    )

    layout = {
        'primary': ['q', 'notification_type', 'is_read'],
        'groups': [],
    }

    class Meta:
        model = Notification
        fields = []
