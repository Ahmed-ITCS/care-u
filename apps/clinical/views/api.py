from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsClinicalStaff, IsDoctor, RolePermission
from apps.users.models import Role
from apps.clinical.filters import VisitFilter
from apps.clinical.models import (
    Visit, OPDVisit, Ward, Bed, Admission, Prescription, PrescriptionItem,
    NursingNote, LabOrder, Referral,
)


class OPDVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OPDVisit
        fields = '__all__'


class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = '__all__'


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='visit.patient.full_name', read_only=True)

    class Meta:
        model = Prescription
        fields = '__all__'


class VisitSerializer(serializers.ModelSerializer):
    opd_details = OPDVisitSerializer(read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.get_full_name', read_only=True)

    class Meta:
        model = Visit
        fields = '__all__'


class WardSerializer(serializers.ModelSerializer):
    occupied_beds = serializers.IntegerField(read_only=True)
    vacant_beds = serializers.IntegerField(read_only=True)

    class Meta:
        model = Ward
        fields = '__all__'


class BedSerializer(serializers.ModelSerializer):
    ward_name = serializers.CharField(source='ward.name', read_only=True)

    class Meta:
        model = Bed
        fields = '__all__'


class AdmissionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    bed_info = serializers.CharField(source='bed.__str__', read_only=True)

    class Meta:
        model = Admission
        fields = '__all__'


class VisitViewSet(viewsets.ModelViewSet):
    queryset = Visit.objects.select_related('patient', 'doctor').prefetch_related('prescriptions')
    serializer_class = VisitSerializer
    permission_classes = [IsAuthenticated, IsClinicalStaff]
    filterset_class = VisitFilter
    search_fields = ['patient__full_name', 'patient__mr_number']
    ordering_fields = ['visit_date']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == Role.DOCTOR:
            return qs.filter(doctor=self.request.user)
        return qs

    @action(detail=True, methods=['post'])
    def opd(self, request, pk=None):
        visit = self.get_object()
        serializer = OPDVisitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(visit=visit)
        visit.status = 'in_progress'
        visit.save(update_fields=['status'])
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def prescribe(self, request, pk=None):
        visit = self.get_object()
        items_data = request.data.pop('items', [])
        prescription = Prescription.objects.create(
            visit=visit, doctor=request.user, notes=request.data.get('notes', '')
        )
        for item in items_data:
            PrescriptionItem.objects.create(prescription=prescription, **item)
        return Response(PrescriptionSerializer(prescription).data, status=status.HTTP_201_CREATED)


class WardViewSet(viewsets.ModelViewSet):
    queryset = Ward.objects.filter(is_active=True).prefetch_related('beds')
    serializer_class = WardSerializer
    permission_classes = [IsAuthenticated, IsClinicalStaff]


class BedViewSet(viewsets.ModelViewSet):
    queryset = Bed.objects.select_related('ward')
    serializer_class = BedSerializer
    permission_classes = [IsAuthenticated, IsClinicalStaff]
    filterset_fields = ['ward', 'status']


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.select_related('visit__patient', 'doctor').prefetch_related('items')
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated, IsClinicalStaff]
    filterset_fields = ['status', 'doctor']

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == Role.DOCTOR:
            return qs.filter(doctor=self.request.user)
        return qs


class AdmissionViewSet(viewsets.ModelViewSet):
    queryset = Admission.objects.select_related('patient', 'bed', 'bed__ward')
    serializer_class = AdmissionSerializer
    permission_classes = [IsAuthenticated, IsClinicalStaff]
    filterset_fields = ['is_active', 'patient']

    @action(detail=True, methods=['post'])
    def discharge(self, request, pk=None):
        from apps.clinical.models import Discharge
        admission = self.get_object()
        discharge = Discharge.objects.create(
            admission=admission,
            discharged_by=request.user,
            summary=request.data.get('summary', ''),
            instructions=request.data.get('instructions', ''),
        )
        return Response({'detail': 'Patient discharged', 'id': discharge.id})
