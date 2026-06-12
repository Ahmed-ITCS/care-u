from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsDoctor, IsReceptionist, RolePermission
from apps.users.models import Role
from apps.appointments.models import AppointmentType, DoctorSchedule, Appointment, QueueEntry


class AppointmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentType
        fields = '__all__'


class DoctorScheduleSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = '__all__'


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)
    type_name = serializers.CharField(source='appointment_type.name', read_only=True)

    class Meta:
        model = Appointment
        fields = '__all__'


class QueueEntrySerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='appointment.patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='appointment.doctor.get_full_name', read_only=True)
    token = serializers.IntegerField(source='token_number', read_only=True)

    class Meta:
        model = QueueEntry
        fields = '__all__'


class AppointmentTypeViewSet(viewsets.ModelViewSet):
    queryset = AppointmentType.objects.filter(is_active=True)
    serializer_class = AppointmentTypeSerializer
    permission_classes = [IsAuthenticated]


class DoctorScheduleViewSet(viewsets.ModelViewSet):
    queryset = DoctorSchedule.objects.select_related('doctor')
    serializer_class = DoctorScheduleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['doctor', 'day_of_week']


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.select_related('patient', 'doctor', 'appointment_type')
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = [Role.ADMIN, Role.DOCTOR, Role.RECEPTIONIST, Role.PATIENT]
    filterset_fields = ['status', 'doctor', 'patient', 'scheduled_date', 'source']
    search_fields = ['patient__full_name', 'patient__mr_number']
    ordering_fields = ['scheduled_date', 'scheduled_time']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == Role.DOCTOR:
            return qs.filter(doctor=user)
        if user.role == Role.PATIENT:
            return qs.filter(patient__user_account=user)
        return qs

    def perform_create(self, serializer):
        appointment = serializer.save(booked_by=self.request.user)
        from apps.appointments.services import create_queue_entry
        create_queue_entry(appointment)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = 'cancelled'
        appointment.save(update_fields=['status'])
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = 'confirmed'
        appointment.save(update_fields=['status'])
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=False, methods=['get'])
    def today(self, request):
        from django.utils import timezone
        today = timezone.now().date()
        qs = self.get_queryset().filter(scheduled_date=today)
        return Response(AppointmentSerializer(qs, many=True).data)


class QueueEntryViewSet(viewsets.ModelViewSet):
    queryset = QueueEntry.objects.select_related('appointment__patient', 'appointment__doctor')
    serializer_class = QueueEntrySerializer
    permission_classes = [IsAuthenticated, IsReceptionist]
    filterset_fields = ['status']

    @action(detail=True, methods=['post'])
    def call(self, request, pk=None):
        from django.utils import timezone
        entry = self.get_object()
        entry.status = 'called'
        entry.called_at = timezone.now()
        entry.save(update_fields=['status', 'called_at'])
        return Response(QueueEntrySerializer(entry).data)

    @action(detail=False, methods=['get'])
    def waiting(self, request):
        from django.utils import timezone
        qs = self.get_queryset().filter(status='waiting', created_at__date=timezone.now().date())
        return Response(QueueEntrySerializer(qs, many=True).data)
