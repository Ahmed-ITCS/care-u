from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsPharmacist, RolePermission
from apps.users.models import Role
from apps.pharmacy.models import (
    Drug, DrugBatch, DrugCategory, Supplier, PurchaseOrder,
    PurchaseOrderItem, Dispense, DispenseItem, StockMovement,
)
from apps.pharmacy.services import dispense_prescription, receive_purchase_order


class DrugSerializer(serializers.ModelSerializer):
    total_stock = serializers.IntegerField(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Drug
        fields = '__all__'


class DrugBatchSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source='drug.generic_name', read_only=True)

    class Meta:
        model = DrugBatch
        fields = '__all__'


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = '__all__'


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = '__all__'


class DispenseItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispenseItem
        fields = '__all__'


class DispenseSerializer(serializers.ModelSerializer):
    items = DispenseItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)

    class Meta:
        model = Dispense
        fields = '__all__'


class DrugViewSet(viewsets.ModelViewSet):
    queryset = Drug.objects.filter(is_active=True).select_related('category')
    serializer_class = DrugSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category']
    search_fields = ['generic_name', 'brand_name', 'barcode']

    @action(detail=True, methods=['get'])
    def batches(self, request, pk=None):
        drug = self.get_object()
        return Response(DrugBatchSerializer(drug.batches.all(), many=True).data)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.filter(is_active=True)
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsPharmacist]
    search_fields = ['name']


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier').prefetch_related('items')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated, IsPharmacist]
    filterset_fields = ['status', 'supplier']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        po = self.get_object()
        receive_purchase_order(po, request.user)
        return Response(PurchaseOrderSerializer(po).data)


class DispenseViewSet(viewsets.ModelViewSet):
    queryset = Dispense.objects.select_related('patient', 'prescription').prefetch_related('items')
    serializer_class = DispenseSerializer
    permission_classes = [IsAuthenticated, IsPharmacist]
    filterset_fields = ['status', 'patient']

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        dispense = self.get_object()
        dispense_prescription(dispense, request.user)
        return Response(DispenseSerializer(dispense).data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        qs = self.get_queryset().filter(status='pending')
        return Response(DispenseSerializer(qs, many=True).data)
