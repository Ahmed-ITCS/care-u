from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.users.models import StaffProfile, DoctorProfile, OTPVerification

User = get_user_model()


class StaffProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffProfile
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')


class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')


class UserSerializer(serializers.ModelSerializer):
    staff_profile = StaffProfileSerializer(read_only=True)
    doctor_profile = DoctorProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'phone', 'is_verified', 'is_active', 'date_joined',
            'staff_profile', 'doctor_profile',
        )
        read_only_fields = ('id', 'date_joined', 'is_verified')

    def get_full_name(self, obj):
        return obj.get_full_name()


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'phone', 'password')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'is_active')


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class OTPRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    channel = serializers.ChoiceField(choices=['email', 'sms'], default='email')


class OTPVerifySerializer(serializers.Serializer):
    username = serializers.CharField()
    code = serializers.CharField(max_length=6)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
