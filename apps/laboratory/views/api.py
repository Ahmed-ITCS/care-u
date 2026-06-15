from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsLabTech, IsClinicalStaff, RolePermission
from apps.users.models import Role
from apps.laboratory.filters import LabTestRequestFilter
from apps.laboratory.models import (
    TestCategory, TestCatalog, LabTestRequest, LabTestRequestItem,
    SampleCollection, TestResult, LabReport,
)


class TestCatalogSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = TestCatalog
        fields = '__all__'


class LabTestRequestItemSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source='test.name', read_only=True)

    class Meta:
        model = LabTestRequestItem
        fields = '__all__'


class TestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestResult
        fields = '__all__'


class LabTestRequestSerializer(serializers.ModelSerializer):
    items = LabTestRequestItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)

    class Meta:
        model = LabTestRequest
        fields = '__all__'


class TestCatalogViewSet(viewsets.ModelViewSet):
    queryset = TestCatalog.objects.filter(is_active=True).select_related('category')
    serializer_class = TestCatalogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category']
    search_fields = ['name', 'code']


class LabTestRequestViewSet(viewsets.ModelViewSet):
    queryset = LabTestRequest.objects.select_related('patient').prefetch_related('items__test')
    serializer_class = LabTestRequestSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = [Role.ADMIN, Role.DOCTOR, Role.LAB_TECH, Role.NURSE]
    filterset_class = LabTestRequestFilter
    search_fields = ['request_number', 'patient__full_name', 'patient__mr_number']

    def perform_create(self, serializer):
        tests = self.request.data.get('tests', [])
        lab_request = serializer.save(requested_by=self.request.user)
        for test_id in tests:
            LabTestRequestItem.objects.create(request=lab_request, test_id=test_id)

    @action(detail=True, methods=['post'])
    def collect_sample(self, request, pk=None):
        lab_request = self.get_object()
        item_id = request.data.get('item_id')
        item = lab_request.items.get(pk=item_id)
        SampleCollection.objects.create(
            request_item=item,
            collected_by=request.user,
            sample_id=request.data.get('sample_id', ''),
        )
        item.status = 'collected'
        item.save(update_fields=['status'])
        lab_request.status = 'collected'
        lab_request.save(update_fields=['status'])
        return Response({'detail': 'Sample collected'})

    @action(detail=True, methods=['post'])
    def enter_result(self, request, pk=None):
        lab_request = self.get_object()
        item_id = request.data.get('item_id')
        item = lab_request.items.get(pk=item_id)
        TestResult.objects.update_or_create(
            request_item=item,
            defaults={
                'result_value': request.data['result_value'],
                'unit': request.data.get('unit', ''),
                'reference_range': request.data.get('reference_range', ''),
                'is_abnormal': request.data.get('is_abnormal', False),
                'entered_by': request.user,
                'notes': request.data.get('notes', ''),
            },
        )
        item.status = 'completed'
        item.save(update_fields=['status'])
        if not lab_request.items.exclude(status='completed').exists():
            lab_request.status = 'completed'
            lab_request.save(update_fields=['status'])
            from apps.laboratory.services import generate_lab_report
            generate_lab_report(lab_request, request.user)
        return Response({'detail': 'Result entered'})
