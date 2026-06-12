from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.models import Department
from apps.core.permissions import IsAdmin, RolePermission
from apps.core.services.dashboard import get_dashboard_kpis, get_revenue_chart_data


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.filter(is_active=True)
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['name', 'code']


class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def kpis(self, request):
        return Response(get_dashboard_kpis(request.user))

    @action(detail=False, methods=['get'])
    def revenue_chart(self, request):
        days = int(request.query_params.get('days', 30))
        return Response(get_revenue_chart_data(days))
