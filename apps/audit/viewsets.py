"""Viewsets for audit app."""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for audit logs (read-only)."""

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only audit logs for the current user's actions."""
        from apps.accounts.models import Account

        # Get user account IDs
        account_ids = Account.objects.filter(
            customer=self.request.user
        ).values_list("id", flat=True)

        # Get transactions for these accounts
        from apps.transactions.models import Transaction

        transaction_ids = Transaction.objects.filter(
            source_account_id__in=account_ids
        ).values_list("id", flat=True)

        # Return audit logs for the user's transactions
        return AuditLog.objects.filter(
            actor_id=self.request.user.id
        ).order_by("-created_at")