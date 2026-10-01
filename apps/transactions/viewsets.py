"""Viewsets for transactions app."""

import uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Account
from apps.ledger.models import EntryType, LedgerEntry

from .models import Transaction, TransactionStatus, TransactionType
from .serializers import (
    DepositSerializer,
    ReversalSerializer,
    TransactionCreateResponseSerializer,
    TransactionSerializer,
    TransferSerializer,
    WithdrawalSerializer,
)


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for transaction operations."""

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        """Return only transactions for the current user's accounts."""
        from apps.accounts.models import Account

        account_ids = Account.objects.filter(
            customer=self.request.user
        ).values_list("id", flat=True)

        return Transaction.objects.filter(
            id__in=Transaction.objects.filter(
                source_account_id__in=account_ids
            ).values_list("id", flat=True) | Transaction.objects.filter(
                destination_account_id__in=account_ids
            ).values_list("id", flat=True)
        ).distinct().order_by("-created_at")

    @action(detail=False, methods=["post"])
    def deposit(self, request):
        """Process a deposit."""
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        idempotency_key = serializer.validated_data.get("idempotency_key")

        # Check idempotency
        if idempotency_key:
            existing = self._check_idempotency(idempotency_key, "DEPOSIT", serializer.validated_data)
            if existing:
                return Response(existing, status=200)

        account = serializer.validated_data["account"]
        amount = serializer.validated_data["amount"]
        reference = serializer.validated_data.get("reference", "Depósito")

        with transaction.atomic():
            # Create transaction
            tx = Transaction.objects.create(
                transaction_type=TransactionType.DEPOSIT,
                status=TransactionStatus.PROCESSING,
                amount=amount,
                destination_account=account,
                reference=reference,
                idempotency_key=str(idempotency_key) if idempotency_key else None,
            )

            # Create ledger entry
            balance_before = account.balance
            entry = LedgerEntry.create_entry(
                transaction_id=tx.id,
                account=account,
                entry_type=EntryType.CREDIT,
                amount=amount,
                balance_before=balance_before,
                description=reference,
            )

            # Update balance
            account.balance += amount
            account.save(update_fields=["balance"])

            # Complete transaction
            tx.mark_completed()

            # Save idempotency record
            if idempotency_key:
                self._save_idempotency(
                    idempotency_key,
                    "DEPOSIT",
                    serializer.validated_data,
                    TransactionSerializer(tx).data,
                )

        response_data = TransactionCreateResponseSerializer({
            "transaction_id": tx.id,
            "status": tx.status,
            "amount": tx.amount,
            "currency": tx.currency,
            "created_at": tx.created_at,
        }).data

        return Response(response_data, status=201)

    @action(detail=False, methods=["post"])
    def withdraw(self, request):
        """Process a withdrawal."""
        serializer = WithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        idempotency_key = serializer.validated_data.get("idempotency_key")

        # Check idempotency
        if idempotency_key:
            existing = self._check_idempotency(idempotency_key, "WITHDRAWAL", serializer.validated_data)
            if existing:
                return Response(existing, status=200)

        account = serializer.validated_data["account"]
        amount = serializer.validated_data["amount"]
        reference = serializer.validated_data.get("reference", "Saque")

        with transaction.atomic():
            # Create transaction
            tx = Transaction.objects.create(
                transaction_type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.PROCESSING,
                amount=amount,
                source_account=account,
                reference=reference,
                idempotency_key=str(idempotency_key) if idempotency_key else None,
            )

            # Create ledger entry
            balance_before = account.balance
            entry = LedgerEntry.create_entry(
                transaction_id=tx.id,
                account=account,
                entry_type=EntryType.DEBIT,
                amount=amount,
                balance_before=balance_before,
                description=reference,
            )

            # Update balance
            account.balance -= amount
            account.save(update_fields=["balance"])

            # Update daily limit
            account.daily_used += amount
            account.save(update_fields=["daily_used"])

            # Complete transaction
            tx.mark_completed()

            # Save idempotency record
            if idempotency_key:
                self._save_idempotency(
                    idempotency_key,
                    "WITHDRAWAL",
                    serializer.validated_data,
                    TransactionSerializer(tx).data,
                )

        response_data = TransactionCreateResponseSerializer({
            "transaction_id": tx.id,
            "status": tx.status,
            "amount": tx.amount,
            "currency": tx.currency,
            "created_at": tx.created_at,
        }).data

        return Response(response_data, status=201)

    @action(detail=False, methods=["post"])
    def transfer(self, request):
        """Process a transfer between accounts."""
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        idempotency_key = serializer.validated_data.get("idempotency_key")

        # Check idempotency
        if idempotency_key:
            existing = self._check_idempotency(idempotency_key, "TRANSFER", serializer.validated_data)
            if existing:
                return Response(existing, status=200)

        source = serializer.validated_data["source_account"]
        destination = serializer.validated_data["destination_account"]
        amount = serializer.validated_data["amount"]
        reference = serializer.validated_data.get("reference", "Transferência")

        # Create correlation ID
        correlation_id = uuid.uuid4()

        with transaction.atomic():
            # Create transaction
            tx = Transaction.objects.create(
                transaction_type=TransactionType.TRANSFER,
                status=TransactionStatus.PROCESSING,
                amount=amount,
                source_account=source,
                destination_account=destination,
                reference=reference,
                correlation_id=correlation_id,
                idempotency_key=str(idempotency_key) if idempotency_key else None,
            )

            # Create ledger entries
            LedgerEntry.create_transfer_entries(
                transaction_id=tx.id,
                source_account=source,
                destination_account=destination,
                amount=amount,
                description=reference,
                correlation_id=correlation_id,
            )

            # Update daily limit for source
            source.daily_used += amount
            source.save(update_fields=["daily_used"])

            # Complete transaction
            tx.mark_completed()

            # Save idempotency record
            if idempotency_key:
                self._save_idempotency(
                    idempotency_key,
                    "TRANSFER",
                    serializer.validated_data,
                    TransactionSerializer(tx).data,
                )

        response_data = TransactionCreateResponseSerializer({
            "transaction_id": tx.id,
            "status": tx.status,
            "amount": tx.amount,
            "currency": tx.currency,
            "created_at": tx.created_at,
        }).data

        return Response(response_data, status=201)

    @action(detail=True, methods=["post"])
    def reverse(self, request, id=None):
        """Reverse a transaction."""
        tx = self.get_object()

        if not tx.is_reversible():
            return Response(
                {"detail": "Transaction cannot be reversed."},
                status=400,
            )

        reason = request.data.get("reason", "Estorno")
        idempotency_key = request.data.get("idempotency_key")

        # Check idempotency
        if idempotency_key:
            existing = self._check_idempotency(idempotency_key, "REVERSAL", {"transaction_id": str(id)})
            if existing:
                return Response(existing, status=200)

        with transaction.atomic():
            # Create reversal transaction
            reversal = Transaction.objects.create(
                transaction_type=TransactionType.REVERSAL,
                status=TransactionStatus.PROCESSING,
                amount=tx.amount,
                source_account=tx.destination_account,
                destination_account=tx.source_account,
                reference=f"Estorno: {reason}",
                correlation_id=uuid.uuid4(),
                idempotency_key=str(idempotency_key) if idempotency_key else None,
                metadata={"reversed_transaction_id": str(tx.id)},
            )

            if tx.transaction_type == TransactionType.TRANSFER:
                # Reverse the transfer
                LedgerEntry.create_transfer_entries(
                    transaction_id=reversal.id,
                    source_account=tx.destination_account,
                    destination_account=tx.source_account,
                    amount=tx.amount,
                    description=f"Estorno de transferência",
                )
            else:
                # For deposits/withdrawals, reverse the ledger entry
                account = tx.source_account or tx.destination_account
                balance_before = account.balance
                entry_type = EntryType.DEBIT if tx.transaction_type == TransactionType.DEPOSIT else EntryType.CREDIT

                LedgerEntry.create_entry(
                    transaction_id=reversal.id,
                    account=account,
                    entry_type=entry_type,
                    amount=tx.amount,
                    balance_before=balance_before,
                    description=f"Estorno: {reason}",
                )

                account.balance += tx.amount if entry_type == EntryType.CREDIT else -tx.amount
                account.save(update_fields=["balance"])

            # Mark original as reversed
            tx.mark_reversed()
            reversal.mark_completed()

        return Response(
            TransactionSerializer(reversal).data,
            status=201,
        )

    def _check_idempotency(self, key, tx_type, data):
        """Check for existing idempotency record."""
        import hashlib
        import json

        try:
            record = IdempotencyRecord.objects.get(key=str(key))
            if record.status == "COMPLETED" and record.matches_request({"type": tx_type, **data}):
                return record.response
            elif record.status == "IN_PROGRESS":
                return {"detail": "Request already in progress", "status": "IN_PROGRESS"}, status=409
        except IdempotencyRecord.DoesNotExist:
            pass
        return None

    def _save_idempotency(self, key, tx_type, data, response):
        """Save idempotency record."""
        import hashlib
        import json

        body_str = json.dumps({"type": tx_type, **data}, sort_keys=True, separators=(",", ":"))
        request_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()

        IdempotencyRecord.objects.create(
            key=str(key),
            request_hash=request_hash,
            transaction_id=response.get("id"),
            response=response,
            status="COMPLETED",
            expires_at=timezone.now() + timezone.timedelta(days=7),
        )