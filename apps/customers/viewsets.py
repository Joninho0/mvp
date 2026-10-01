"""Viewsets for customers app."""

from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CustomerStatus
from .serializers import MFASerializer, TokenRefreshSerializer, UserRegistrationSerializer, UserSerializer

User = get_user_model()


class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for customer operations."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the current user's data."""
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Get current user profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def register(self, request):
        """Register a new customer."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=201,
        )

    @action(detail=False, methods=["post"])
    def verify_kyc(self, request):
        """Submit KYC verification."""
        from apps.customers.models import IdempotencyRecord

        # This would typically involve document upload and verification
        user = request.user
        if user.is_kyc_verified:
            return Response(
                {"detail": "KYC already verified."},
                status=400,
            )

        # Simulate KYC verification
        user.verify_kyc()

        return Response(
            {"detail": "KYC verification submitted."},
            status=200,
        )

    @action(detail=False, methods=["post"])
    def enable_mfa(self, request):
        """Enable MFA for the user."""
        from django_otp import devices
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = request.user
        device = TOTPDevice.objects.create(
            user=user,
            name="Default",
        )
        url = device.config_url

        return Response(
            {"detail": "MFA device created.", "config_url": url},
            status=200,
        )

    @action(detail=False, methods=["post"])
    def verify_mfa(self, request):
        """Verify MFA OTP."""
        serializer = MFASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from django_otp import verify

        user = request.user
        otp = serializer.validated_data["otp"]

        if verify(user, otp):
            user.is_mfa_enabled = True
            user.save()
            return Response({"detail": "MFA verified successfully."})
        else:
            return Response(
                {"detail": "Invalid OTP."},
                status=400,
            )

    @action(detail=False, methods=["post"])
    def refresh_token(self, request):
        """Refresh access token."""
        from rest_framework_simplejwt.tokens import RefreshToken

        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refresh = RefreshToken(serializer.validated_data["refresh"])
        return Response({
            "access": str(refresh.access_token),
        })