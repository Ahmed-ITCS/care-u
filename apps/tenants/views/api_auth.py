"""
Unified API login — POST /api/v1/auth/login/ (public schema, no tenant prefix).
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django_tenants.utils import schema_context

from apps.tenants.auth import resolve_tenant_and_authenticate
from apps.users.serializers import LoginSerializer, UserSerializer


class LoginThrottle(AnonRateThrottle):
    scope = 'login'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def unified_api_login(request):
    """
    Login with username/email + password. Returns JWT + tenant info.
    Use api_base_url for all subsequent API calls.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    result = resolve_tenant_and_authenticate(
        serializer.validated_data['username'],
        serializer.validated_data['password'],
    )
    if not result:
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    hospital, user = result
    with schema_context(hospital.schema_name):
        refresh = RefreshToken.for_user(user)
        refresh['tenant_subdomain'] = hospital.subdomain
        refresh['tenant_schema'] = hospital.schema_name
        user_data = UserSerializer(user).data

    api_base = f'/h/{hospital.subdomain}/api/v1/'
    return Response({
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'tenant': hospital.subdomain,
        'tenant_name': hospital.name,
        'api_base_url': api_base,
        'user': user_data,
    })
