from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model

from apps.core.permissions import IsAdmin, RolePermission
from apps.users.models import StaffProfile, DoctorProfile, OTPVerification, Role
from apps.users.serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    StaffProfileSerializer, DoctorProfileSerializer,
    LoginSerializer, OTPRequestSerializer, OTPVerifySerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer,
)
from apps.users.tasks import send_otp_email, send_otp_sms

User = get_user_model()


class LoginThrottle(AnonRateThrottle):
    scope = 'login'


class OTPThrottle(AnonRateThrottle):
    scope = 'otp'


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], throttle_classes=[LoginThrottle])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if not user:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)

    @action(detail=False, methods=['post'], throttle_classes=[OTPThrottle])
    def otp_request(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(username=serializer.validated_data['username'])
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        channel = serializer.validated_data['channel']
        otp = OTPVerification.generate(user, purpose='login', channel=channel)
        if channel == 'sms' and user.phone:
            send_otp_sms.delay(user.phone, otp.code)
        else:
            send_otp_email.delay(user.id, otp.code)
        return Response({'detail': f'OTP sent via {channel}'})

    @action(detail=False, methods=['post'], throttle_classes=[OTPThrottle])
    def otp_verify(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(username=serializer.validated_data['username'])
        except User.DoesNotExist:
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        otp = OTPVerification.objects.filter(user=user, purpose='login', is_used=False).first()
        if otp and otp.verify(serializer.validated_data['code']):
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
            })
        return Response({'detail': 'Invalid or expired OTP'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], throttle_classes=[OTPThrottle])
    def password_reset(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
            otp = OTPVerification.generate(user, purpose='password_reset')
            send_otp_email.delay(user.id, otp.code, 'password_reset')
        except User.DoesNotExist:
            pass
        return Response({'detail': 'If account exists, reset code sent'})

    @action(detail=False, methods=['post'])
    def password_reset_confirm(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
        except User.DoesNotExist:
            return Response({'detail': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)
        otp = OTPVerification.objects.filter(
            user=user, purpose='password_reset', is_used=False
        ).first()
        if otp and otp.verify(serializer.validated_data['code']):
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'detail': 'Password reset successful'})
        return Response({'detail': 'Invalid or expired code'}, status=status.HTTP_400_BAD_REQUEST)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserUpdateSerializer
        return UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related('staff_profile', 'doctor_profile')
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['date_joined', 'last_name']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserSerializer


class StaffProfileViewSet(viewsets.ModelViewSet):
    queryset = StaffProfile.objects.select_related('user', 'department')
    serializer_class = StaffProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ['department']
    search_fields = ['user__first_name', 'user__last_name', 'cnic']


class DoctorProfileViewSet(viewsets.ModelViewSet):
    queryset = DoctorProfile.objects.select_related('user')
    serializer_class = DoctorProfileSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['specialty']
    search_fields = ['user__first_name', 'user__last_name', 'specialty', 'license_number']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
