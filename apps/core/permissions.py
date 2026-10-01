"""Custom permissions for the bank API."""

from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Permission class for object ownership."""

    def has_object_permission(self, request, view, obj):
        """Check if user has permission to access the object."""
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only to owner
        return obj.customer == request.user


class IsAccountOwner(permissions.BasePermission):
    """Permission class for account access."""

    def has_object_permission(self, request, view, obj):
        """Check if user owns the account."""
        return obj.customer == request.user


class RateLimitPermission(permissions.BasePermission):
    """Permission class with rate limiting."""

    def has_permission(self, request, view):
        """Check if user has exceeded rate limit."""
        # Rate limiting is handled by django-ratelimit middleware
        return True


class MFAPermission(permissions.BasePermission):
    """Permission class requiring MFA."""

    def has_permission(self, request, view):
        """Check if user has MFA enabled and verified."""
        user = request.user

        if not user.is_authenticated:
            return False

        # If MFA is required for this view
        if getattr(view, "require_mfa", False):
            # Check if user has verified MFA in this session
            if not getattr(request, "mfa_verified", False):
                return False

        return True