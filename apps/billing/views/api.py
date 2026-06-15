from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from apps.core.permissions import IsAccountant, RolePermission
from apps.users.models import Role
from apps.billing.filters import InvoiceFilter, PaymentFilter
from apps.billing.models import ServiceCatalog, ServicePrice, Invoice, InvoiceItem, Payment, LedgerEntry
from apps.billing.services import create_invoice_from_visit, record_payment


class ServicePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePrice
        fields = '__all__'


class ServiceCatalogSerializer(serializers.ModelSerializer):
    current_price = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCatalog
        fields = '__all__'

    def get_current_price(self, obj):
        price = obj.prices.filter(is_current=True).first()
        return float(price.price) if price else 0


class InvoiceItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceItem
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class ServiceCatalogViewSet(viewsets.ModelViewSet):
    queryset = ServiceCatalog.objects.filter(is_active=True).prefetch_related('prices')
    serializer_class = ServiceCatalogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['category']
    search_fields = ['name', 'code']


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related('patient').prefetch_related('items', 'payments')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = [Role.ADMIN, Role.ACCOUNTANT, Role.RECEPTIONIST, Role.PATIENT]
    filterset_class = InvoiceFilter
    search_fields = ['invoice_number', 'patient__full_name', 'patient__mr_number']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == Role.PATIENT:
            return qs.filter(patient__user_account=self.request.user)
        return qs

    @action(detail=False, methods=['post'])
    def from_visit(self, request):
        visit_id = request.data.get('visit_id')
        invoice = create_invoice_from_visit(visit_id, request.user)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        invoice = self.get_object()
        item = InvoiceItem.objects.create(
            invoice=invoice,
            service_id=request.data.get('service_id'),
            description=request.data['description'],
            quantity=request.data.get('quantity', 1),
            unit_price=request.data['unit_price'],
        )
        invoice.recalculate()
        return Response(InvoiceItemSerializer(item).data, status=status.HTTP_201_CREATED)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('invoice', 'invoice__patient')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsAccountant]
    filterset_class = PaymentFilter

    def perform_create(self, serializer):
        payment = record_payment(
            invoice=serializer.validated_data['invoice'],
            amount=serializer.validated_data['amount'],
            method=serializer.validated_data.get('method', 'cash'),
            user=self.request.user,
            transaction_id=serializer.validated_data.get('transaction_id', ''),
        )
        serializer.instance = payment


class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({'status': 'placeholder'})
