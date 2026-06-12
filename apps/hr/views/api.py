from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsAdmin, RolePermission
from apps.users.models import Role
from apps.hr.models import Attendance, LeaveRequest, PayrollRun, PayrollItem, Shift
from apps.hr.services import process_payroll


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

    class Meta:
        model = LeaveRequest
        fields = '__all__'


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


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.select_related('staff')
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['staff', 'status', 'date']


class LeaveRequestViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.select_related('staff')
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'leave_type', 'staff']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role not in (Role.ADMIN,):
            return qs.filter(staff=self.request.user)
        return qs

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def approve(self, request, pk=None):
        leave = self.get_object()
        leave.status = 'approved'
        leave.approved_by = request.user
        leave.approval_notes = request.data.get('notes', '')
        leave.save()
        return Response(LeaveRequestSerializer(leave).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def reject(self, request, pk=None):
        leave = self.get_object()
        leave.status = 'rejected'
        leave.approved_by = request.user
        leave.approval_notes = request.data.get('notes', '')
        leave.save()
        return Response(LeaveRequestSerializer(leave).data)


class PayrollRunViewSet(viewsets.ModelViewSet):
    queryset = PayrollRun.objects.prefetch_related('items')
    serializer_class = PayrollRunSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        payroll = self.get_object()
        process_payroll(payroll, request.user)
        return Response(PayrollRunSerializer(payroll).data)
