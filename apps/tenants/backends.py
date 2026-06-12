from apps.tenants.models import PlatformUser


class PlatformAuthBackend:
    """Authenticate PlatformUser (super admin) in public schema only."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = PlatformUser.objects.get(username=username, is_active=True)
            if user.check_password(password):
                return user
        except PlatformUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return PlatformUser.objects.get(pk=user_id, is_active=True)
        except PlatformUser.DoesNotExist:
            return None
