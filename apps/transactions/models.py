"""
Transaction models for the bank.

This module contains the Transaction model for all financial transactions.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


class TransactionStatus(models.TextChoices):
    """Status of a transaction."""

    PENDING = "PENDING", _("Pending")
    FRAUD_CHECK = "FRAUD_CHECK", _("Fraud Check")
    PROCESSING = "PROCESSING", _("Processing")
    COMPLETED = "COMPLETED", _("Completed")
    FAILED = "FAILED", _("Failed")
    REJECTED = "REJECTED", _("Rejected")
    REVERSED = "REVERSED", _("Reversed")


class TransactionType(models.TextChoices):
    """Type of financial transaction."""

    DEPOSIT = "DEPOSIT", _("Deposit")
    WITHDRAWAL = "WITHDRAWAL", _("Withdrawal")
    TRANSFER = "TRANSFER", _("Transfer")
    REVERSAL = "REVERSAL", _("Reversal")


class Transaction(models.Model):
    """
    Represents a financial transaction.

    Transactions are the core of the banking system and include:
    - Deposits
    - Withdrawals
    - Transfers between accounts
    - Reversals of previous transactions

    All transactions use the double-entry ledger system.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_type = models.CharField(
        _("transaction type"),
        max_length=20,
        choices=TransactionType.choices,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
    )
    amount = models.DecimalField(
        _("amount"),
        max_digits=18,
        decimal_places=2,
        validators=[],
        help_text=_("Transaction amount (always positive)"),
    )
    currency = models.CharField(
        _("currency"),
        max_length=3,
        default="BRL",
        help_text=_("ISO 4217 currency code"),
    )
    idempotency_key = models.CharField(
        _("idempotency key"),
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Client-provided idempotency key"),
    )
    correlation_id = models.UUIDField(
        _("correlation ID"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("ID for tracing related transactions"),
    )
    source_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="outgoing_transactions",
        verbose_name=_("source account"),
        null=True,
        blank=True,
    )
    destination_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="incoming_transactions",
        verbose_name=_("destination account"),
        null=True,
        blank=True,
    )
    reference = models.CharField(
        _("reference"),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("Optional reference/description"),
    )
    failure_reason = models.TextField(
        _("failure reason"),
        null=True,
        blank=True,
    )
    fraud_check_result = models.JSONField(
        _("fraud check result"),
        default=dict,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        _("metadata"),
        default=dict,
        null=True,
        blank=True,
    )
    requested_at = models.DateTimeField(
        _("requested at"),
        auto_now_add=True,
    )
    fraud_checked_at = models.DateTimeField(
        _("fraud checked at"),
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        _("completed at"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("updated at"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["idempotency_key"]),
            models.Index(fields=["source_account", "status"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=Decimal("0")),
                name="positive_amount",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(
                        transaction_type=TransactionType.DEPOSIT,
                        source_account__isnull=True,
                        destination_account__isnull=False,
                    )
                    | models.Q(
                        transaction_type=TransactionType.WITHDRAWAL,
                        source_account__isnull=False,
                        destination_account__isnull=True,
                    )
                    | models.Q(
                        transaction_type=TransactionType.TRANSFER,
                        source_account__isnull=False,
                        destination_account__isnull=False,
                    )
                    | models.Q(
                        transaction_type=TransactionType.REVERSAL,
                        source_account__isnull=False,
                        destination_account__isnull=False,
                    )
                ),
                name="valid_transaction_accounts",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_type} {self.amount} {self.currency} ({self.status})"

    def can_proceed_to_fraud_check(self) -> bool:
        """Check if the transaction can proceed to fraud check."""
        return self.status == TransactionStatus.PENDING

    def can_proceed_to_processing(self) -> bool:
        """Check if the transaction can proceed to processing."""
        return self.status == TransactionStatus.FRAUD_CHECK

    def can_be_completed(self) -> bool:
        """Check if the transaction can be completed."""
        return self.status == TransactionStatus.PROCESSING

    def can_be_reversed(self) -> bool:
        """Check if the transaction can be reversed."""
        return self.status == TransactionStatus.COMPLETED

    def mark_fraud_check_passed(self, result: dict | None = None) -> None:
        """Mark the transaction as passed fraud check."""
        from django.utils import timezone

        self.status = TransactionStatus.PROCESSING
        self.fraud_checked_at = timezone.now()
        self.fraud_check_result = result or {"passed": True}
        self.save(update_fields=["status", "fraud_checked_at", "fraud_check_result"])

    def mark_fraud_check_failed(self, reason: str) -> None:
        """Mark the transaction as failed fraud check."""
        from django.utils import timezone

        self.status = TransactionStatus.REJECTED
        self.fraud_checked_at = timezone.now()
        self.fraud_check_result = {"passed": False, "reason": reason}
        self.failure_reason = reason
        self.save(update_fields=["status", "fraud_checked_at", "fraud_check_result", "failure_reason"])

    def mark_completed(self) -> None:
        """Mark the transaction as completed."""
        from django.utils import timezone

        self.status = TransactionStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def mark_failed(self, reason: str) -> None:
        """Mark the transaction as failed."""
        from django.utils import timezone

        self.status = TransactionStatus.FAILED
        self.completed_at = timezone.now()
        self.failure_reason = reason
        self.save(update_fields=["status", "completed_at", "failure_reason"])

    def mark_reversed(self) -> None:
        """Mark the transaction as reversed."""
        from django.utils import timezone

        self.status = TransactionStatus.REVERSED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def is_terminal(self) -> bool:
        """Check if the transaction is in a terminal state."""
        return self.status in (
            TransactionStatus.COMPLETED,
            TransactionStatus.FAILED,
            TransactionStatus.REJECTED,
            TransactionStatus.REVERSED,
        )

    def is_successful(self) -> bool:
        """Check if the transaction completed successfully."""
        return self.status == TransactionStatus.COMPLETED

    def is_reversible(self) -> bool:
        """Check if the transaction can be reversed."""
        return self.can_be_reversed() and self.transaction_type in (
            TransactionType.TRANSFER,
            TransactionType.DEPOSIT,
            TransactionType.WITHDRAWAL,
        )

    def get_related_entries(self):
        """Get related ledger entries."""
        from apps.ledger.models import LedgerEntry

        return LedgerEntry.objects.filter(transaction_id=self.id).order_by("created_at")

    def get_settlement_account(self) -> "accounts.Account":
        """Get the settlement/cash account for the bank."""
        from apps.accounts.models import Account

        # This would normally be looked up by account number
        # For simplicity, we create a method that should be overridden
        raise NotImplementedError("Settlement account should be configured")


class IdempotencyRecord(models.Model):
    """
    Record of processed idempotency requests.

    Stores the request hash and response to detect duplicate requests.
    """

    key = models.CharField(
        _("idempotency key"),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Client-provided idempotency key"),
    )
    request_hash = models.CharField(
        _("request hash"),
        max_length=64,
        help_text=_("Hash of the request body"),
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
        null=True,
        blank=True,
    )
    response = models.JSONField(
        _("response"),
        default=dict,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        default="IN_PROGRESS",
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
    )
    expires_at = models.DateTimeField(
        _("expires at"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Idempotency Record")
        verbose_name_plural = _("Idempotency Records")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["key"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Idempotency({self.key[:8]}...) - {self.status}"

    def is_expired(self) -> bool:
        """Check if the record has expired."""
        from django.utils import timezone

        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    def matches_request(self, request_hash: str) -> bool:
        """Check if the request hash matches."""
        return self.request_hash == request_hash