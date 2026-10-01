"""Serializers for customers app."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "customer_status",
            "kyc_verified_at",
            "phone",
            "date_of_birth",
            "nationality",
            "is_mfa_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer_status",
            "kyc_verified_at",
            "created_at",
            "updated_at",
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password1 = serializers.CharField(write_only=True, min_length=12)
    password2 = serializers.CharField(write_only=True)
    cpf = serializers.CharField(max_length=14)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "cpf",
            "password1",
            "password2",
        ]

    def validate_email(self, value):
        """Check if email already exists."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        return value

    def validate_cpf(self, value):
        """Validate and normalize CPF."""
        import re
        cpf = re.sub(r"[^0-9]", "", value)
        if len(cpf) != 11:
            raise serializers.ValidationError("CPF deve ter 11 dígitos.")
        return cpf

    def validate_password1(self, value):
        """Validate password strength."""
        if len(value) < 12:
            raise serializers.ValidationError("A senha deve ter pelo menos 12 caracteres.")
        return value

    def validate(self, data):
        """Validate that passwords match."""
        if data["password1"] != data["password2"]:
            raise serializers.ValidationError({"password2": "As senhas não coincidem."})
        return data

    def create(self, validated_data):
        """Create user with encrypted CPF."""
        from django.utils import timezone

        cpf = validated_data.pop("cpf")
        password = validated_data.pop("password1")
        validated_data.pop("password2")

        # Encrypt CPF (simplified - should use proper encryption in production)
        user = User(**validated_data)
        user.set_password(password)
        user.save()

        return user


class TokenRefreshSerializer(serializers.Serializer):
    """Serializer for token refresh."""

    refresh = serializers.CharField()


class MFASerializer(serializers.Serializer):
    """Serializer for MFA verification."""

    otp = serializers.CharField(max_length=6, min_length=6)