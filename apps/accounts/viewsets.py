"""Viewsets for accounts app."""

from django.db import transaction
from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Account, AccountStatus
from .serializers import AccountBalanceSerializer, AccountCreateSerializer, AccountSerializer


class AccountViewSet(viewsets.ModelViewSet):
    """ViewSet for account operations."""

    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only the current user's accounts."""
        return Account.objects.filter(
            customer=self.request.user,
        ).order_by("-created_at")

    def get_serializer_class(self):
        """Return appropriate serializer."""
        if self.action == "create":
            return AccountCreateSerializer
        return AccountSerializer

    @action(detail=True, methods=["get"])
    def balance(self, request, pk=None):
        """Get account balance."""
        account = self.get_object()
        serializer = AccountBalanceSerializer({
            "account_id": account.id,
            "balance": account.balance,
            "currency": account.currency,
            "as_of": account.updated_at,
        })
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def statement(self, request, pk=None):
        """Get account statement."""
        from apps.ledger.models import LedgerEntry
        from apps.ledger.serializers import LedgerEntrySerializer

        account = self.get_object()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        entry_type = request.query_params.get("type")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        query = LedgerEntry.objects.filter(account=account)

        if entry_type:
            query = query.filter(entry_type=entry_type)
        if start_date:
            query = query.filter(created_at__date__gte=start_date)
        if end_date:
            query = query.filter(created_at__date__lte=end_date)

        # Get totals
        from django.db.models import Sum, Case, When, DecimalField

        totals = query.aggregate(
            total_credits=Sum(
                Case(
                    When(entry_type="CREDIT", then="amount"),
                    default=0,
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            ),
            total_debits=Sum(
                Case(
                    When(entry_type="DEBIT", then="amount"),
                    default=0,
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            ),
        )

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        entries = query.order_by("-created_at")[start:end]

        return Response({
            "account": AccountSerializer(account).data,
            "entries": LedgerEntrySerializer(entries, many=True).data,
            "total_credits": totals["total_credits"] or 0,
            "total_debits": totals["total_debits"] or 0,
            "page": page,
            "page_size": page_size,
            "total": query.count(),
        })

    @action(detail=True, methods=["post"])
    def block(self, request, pk=None):
        """Block an account."""
        account = self.get_object()
        reason = request.data.get("reason", "Bloqueado pelo usuário")

        with transaction.atomic():
            account.block(reason)
            account.refresh_from_db()

        return Response(AccountSerializer(account).data)

    @action(detail=True, methods=["post"])
    def unblock(self, request, pk=None):
        """Unblock an account."""
        account = self.get_object()

        with transaction.atomic():
            account.unblock()
            account.refresh_from_db()

        return Response(AccountSerializer(account).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Close an account."""
        account = self.get_object()

        with transaction.atomic():
            account.close()
            account.refresh_from_db()

        return Response(AccountSerializer(account).data)