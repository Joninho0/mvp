"""Viewsets for ledger app."""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import LedgerEntry
from .serializers import LedgerEntrySerializer


class LedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ledger entries (read-only)."""

    serializer_class = LedgerEntrySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["entry_type", "account", "transaction_id"]

    def get_queryset(self):
        """Return only entries for the current user's accounts."""
        from apps.accounts.models import Account

        account_ids = Account.objects.filter(
            customer=self.request.user
        ).values_list("id", flat=True)

        return LedgerEntry.objects.filter(
            account_id__in=account_ids
        ).order_by("-created_at")

    @action(detail=False, methods=["get"])
    def reconcile(self, request):
        """Reconcile account balances with ledger entries."""
        from apps.accounts.models import Account
        from django.db.models import Sum, Case, When, DecimalField

        results = []

        account_ids = Account.objects.filter(
            customer=request.user
        ).values_list("id", flat=True)

        for account_id in account_ids:
            # Get current balance
            account = Account.objects.get(id=account_id)

            # Calculate balance from ledger
            calculated_balance = LedgerEntry.objects.filter(
                account_id=account_id
            ).aggregate(
                balance=Sum(
                    Case(
                        When(entry_type="DEBIT", then=-models.F("amount")),
                        When(entry_type="CREDIT", then=models.F("amount")),
                        default=Decimal("0"),
                        output_field=DecimalField(max_digits=18, decimal_places=2),
                    )
                )
            )["balance"] or Decimal("0")

            is_reconciled = account.balance == calculated_balance

            results.append({
                "account_id": str(account_id),
                "account_number": account.account_number,
                "db_balance": str(account.balance),
                "ledger_balance": str(calculated_balance),
                "is_reconciled": is_reconciled,
                "difference": str(account.balance - calculated_balance),
            })

        return Response({
            "results": results,
            "all_reconciled": all(r["is_reconciled"] for r in results),
        })