from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsAdmin
from apps.users.models import Role
from apps.hr.filters import AttendanceFilter, LeaveRequestFilter, PayrollRunFilter
from apps.hr.models import Attendance, LeaveRequest, PayrollRun, PayrollItem, Shift
from apps.hr.services import process_payroll, approve_leave, reject_leave


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = '__all__'


class AttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'


class LeaveRequestSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['status', 'approved_by', 'approval_notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and getattr(request.user, 'role', None) != Role.ADMIN:
            self.fields['staff'].read_only = True


class PayrollItemSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)

    class Meta:
        model = PayrollItem
        fields = '__all__'


class PayrollRunSerializer(serializers.ModelSerializer):
    items = PayrollItemSerializer(many=True, read_only=True)

    class Meta:
        model = PayrollRun
        fields = '__all__'
        read_only_fields = ['status', 'total_amount', 'processed_by', 'processed_at']


class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.filter(is_active=True)
    serializer_class = ShiftSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('staff')
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_class = AttendanceFilter


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related('staff', 'approved_by')
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = LeaveRequestFilter

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role != Role.ADMIN:
            return qs.filter(staff=self.request.user)
        return qs

    def perform_create(self, serializer):
        serializer.save(staff=self.request.user, status='pending')

    def perform_update(self, serializer):
        if self.request.user.role != Role.ADMIN:
            serializer.save(staff=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def approve(self, request, pk=None):
        leave = self.get_object()
        approve_leave(leave, request.user, request.data.get('notes', ''))
        return Response(LeaveRequestSerializer(leave, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def reject(self, request, pk=None):
        leave = self.get_object()
        reject_leave(leave, request.user, request.data.get('notes', ''))
        return Response(LeaveRequestSerializer(leave, context={'request': request}).data)


class PayrollRunViewSet(viewsets.ModelViewSet):
    queryset = PayrollRun.objects.prefetch_related('items')
    serializer_class = PayrollRunSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    filterset_class = PayrollRunFilter

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        payroll = self.get_object()
        if payroll.status != 'draft':
            return Response({'detail': 'Payroll already processed.'}, status=400)
        process_payroll(payroll, request.user)
        payroll.refresh_from_db()
        return Response(PayrollRunSerializer(payroll).data)
