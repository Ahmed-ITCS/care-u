from rest_framework import serializers, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsAdmin, IsClinicalStaff, IsReceptionist, RolePermission
from apps.tenants.limits import check_patient_limit
from apps.users.models import Role
from apps.patients.filters import PatientFilter
from apps.patients.models import (
    Patient, InsuranceProvider, PatientInsurance, EmergencyContact,
    Allergy, ChronicCondition, MedicalHistory, FamilyHistory,
    VitalSign, PatientDocument,
)


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = '__all__'
        read_only_fields = ('patient', 'created_at', 'updated_at')


class PatientInsuranceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)

    class Meta:
        model = PatientInsurance
        fields = '__all__'


class AllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergy
        fields = '__all__'


class ChronicConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChronicCondition
        fields = '__all__'


class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = '__all__'


class FamilyHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyHistory
        fields = '__all__'


class VitalSignSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSign
        fields = '__all__'


class PatientDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDocument
        fields = '__all__'


class PatientListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = (
            'id', 'mr_number', 'cnic', 'first_name', 'last_name', 'full_name',
            'phone', 'email', 'gender', 'date_of_birth', 'created_at',
        )


class PatientDetailSerializer(serializers.ModelSerializer):
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    insurance_policies = PatientInsuranceSerializer(many=True, read_only=True)
    allergies = AllergySerializer(many=True, read_only=True)
    chronic_conditions = ChronicConditionSerializer(many=True, read_only=True)
    medical_history = MedicalHistorySerializer(many=True, read_only=True)
    family_history = FamilyHistorySerializer(many=True, read_only=True)
    vitals = VitalSignSerializer(many=True, read_only=True)
    documents = PatientDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ('mr_number', 'full_name', 'created_at', 'updated_at')


class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    permission_classes = [IsAuthenticated, RolePermission]
    required_roles = [Role.ADMIN, Role.DOCTOR, Role.NURSE, Role.RECEPTIONIST]
    filterset_class = PatientFilter
    search_fields = ['mr_number', 'cnic', 'full_name', 'phone', 'email']
    ordering_fields = ['created_at', 'full_name', 'mr_number']

    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        return PatientDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == Role.PATIENT:
            return qs.filter(user_account=user)
        if user.role == Role.DOCTOR:
            from apps.clinical.models import Visit
            patient_ids = Visit.objects.filter(doctor=user).values_list('patient_id', flat=True)
            return qs.filter(id__in=patient_ids)
        return qs

    def perform_create(self, serializer):
        check_patient_limit()
        serializer.save(registered_by=self.request.user)

    @action(detail=True, methods=['get', 'post'])
    def allergies(self, request, pk=None):
        patient = self.get_object()
        if request.method == 'GET':
            return Response(AllergySerializer(patient.allergies.all(), many=True).data)
        serializer = AllergySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient, noted_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'])
    def vitals(self, request, pk=None):
        patient = self.get_object()
        if request.method == 'GET':
            return Response(VitalSignSerializer(patient.vitals.all()[:20], many=True).data)
        serializer = VitalSignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient, recorded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'])
    def documents(self, request, pk=None):
        patient = self.get_object()
        if request.method == 'GET':
            return Response(PatientDocumentSerializer(patient.documents.all(), many=True).data)
        serializer = PatientDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient, uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InsuranceProviderViewSet(viewsets.ModelViewSet):
    queryset = InsuranceProvider.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.ModelSerializer

    class Meta:
        model = InsuranceProvider
        fields = '__all__'

    def get_serializer_class(self):
        class ProviderSerializer(serializers.ModelSerializer):
            class Meta:
                model = InsuranceProvider
                fields = '__all__'
        return ProviderSerializer


class AllergyViewSet(viewsets.ModelViewSet):
    queryset = Allergy.objects.select_related('patient')
    serializer_class = AllergySerializer
    permission_classes = [IsAuthenticated, IsClinicalStaff]
    filterset_fields = ['severity', 'patient']
    search_fields = ['allergen']


class VitalSignViewSet(viewsets.ModelViewSet):
    queryset = VitalSign.objects.select_related('patient')
    serializer_class = VitalSignSerializer
    permission_classes = [IsAuthenticated, IsClinicalStaff]
    filterset_fields = ['patient']


class PatientDocumentViewSet(viewsets.ModelViewSet):
    queryset = PatientDocument.objects.select_related('patient')
    serializer_class = PatientDocumentSerializer
    permission_classes = [IsAuthenticated, IsClinicalStaff]
    filterset_fields = ['document_type', 'patient']
