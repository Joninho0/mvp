"""
Ledger models for the bank.

This module contains the LedgerEntry model for the double-entry ledger system.
Every financial transaction creates two entries (debit and credit) that sum to zero.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


class EntryType(models.TextChoices):
    """Type of ledger entry."""

    DEBIT = "DEBIT", _("Debit")
    CREDIT = "CREDIT", _("Credit")


class LedgerEntry(models.Model):
    """
    Represents a single entry in the double-entry ledger.

    Every transaction creates two entries with opposite signs that sum to zero.
    This ensures the accounting equation stays balanced.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.UUIDField(
        _("transaction ID"),
        db_index=True,
        help_text=_("ID of the parent transaction"),
    )
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="ledger_entries",
        verbose_name=_("account"),
    )
    entry_type = models.CharField(
        _("entry type"),
        max_length=10,
        choices=EntryType.choices,
    )
    amount = models.DecimalField(
        _("amount"),
        max_digits=18,
        decimal_places=2,
        help_text=_("Absolute amount of the entry"),
    )
    balance_before = models.DecimalField(
        _("balance before"),
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Account balance before this entry"),
    )
    balance_after = models.DecimalField(
        _("balance after"),
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Account balance after this entry"),
    )
    description = models.CharField(
        _("description"),
        max_length=255,
        null=True,
        blank=True,
    )
    correlation_id = models.UUIDField(
        _("correlation ID"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("ID for tracing related entries"),
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("Ledger Entry")
        verbose_name_plural = _("Ledger Entries")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction_id"]),
            models.Index(fields=["account", "created_at"]),
            models.Index(fields=["correlation_id"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=Decimal("0")),
                name="positive_amount",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.entry_type} {self.amount} - Account {self.account_id}"

    @classmethod
    def create_entry(
        cls,
        transaction_id: uuid.UUID,
        account: "accounts.Account",
        entry_type: str,
        amount: Decimal,
        balance_before: Decimal,
        description: str | None = None,
        correlation_id: uuid.UUID | None = None,
    ) -> "LedgerEntry":
        """
        Create a single ledger entry.

        Args:
            transaction_id: ID of the parent transaction
            account: Account to debit/credit
            entry_type: DEBIT or CREDIT
            amount: Amount of the entry
            balance_before: Account balance before this entry
            description: Optional description
            correlation_id: Optional correlation ID for tracing

        Returns:
            Created LedgerEntry
        """
        balance_after = balance_before - amount if entry_type == EntryType.DEBIT else balance_before + amount

        return cls.objects.create(
            transaction_id=transaction_id,
            account=account,
            entry_type=entry_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            description=description,
            correlation_id=correlation_id,
        )

    @classmethod
    def create_transfer_entries(
        cls,
        transaction_id: uuid.UUID,
        source_account: "accounts.Account",
        destination_account: "accounts.Account",
        amount: Decimal,
        description: str | None = None,
        correlation_id: uuid.UUID | None = None,
    ) -> tuple["LedgerEntry", "LedgerEntry"]:
        """
        Create paired debit and credit entries for a transfer.

        Args:
            transaction_id: ID of the transfer transaction
            source_account: Account to debit from
            destination_account: Account to credit to
            amount: Amount to transfer
            description: Optional description
            correlation_id: Optional correlation ID for tracing

        Returns:
            Tuple of (debit_entry, credit_entry)
        """
        with transaction.atomic():
            # Lock both accounts in a deterministic order to prevent deadlock
            accounts = [source_account, destination_account]
            accounts.sort(key=lambda a: a.id)

            # Lock in order
            for account in accounts:
                from apps.accounts.models import Account
                Account.objects.select_for_update().get(id=account.id)
                account.refresh_from_db()

            # Create debit entry for source
            debit_entry = cls.create_entry(
                transaction_id=transaction_id,
                account=source_account,
                entry_type=EntryType.DEBIT,
                amount=amount,
                balance_before=source_account.balance,
                description=description,
                correlation_id=correlation_id,
            )

            # Update source balance
            source_account.balance -= amount
            source_account.save(update_fields=["balance"])

            # Create credit entry for destination
            credit_entry = cls.create_entry(
                transaction_id=transaction_id,
                account=destination_account,
                entry_type=EntryType.CREDIT,
                amount=amount,
                balance_before=destination_account.balance,
                description=description,
                correlation_id=correlation_id,
            )

            # Update destination balance
            destination_account.balance += amount
            destination_account.save(update_fields=["balance"])

            return debit_entry, credit_entry

    @classmethod
    def get_account_balance(cls, account_id: uuid.UUID) -> Decimal:
        """
        Get the current balance from the ledger for an account.

        This can be used for reconciliation.

        Args:
            account_id: ID of the account

        Returns:
            Calculated balance from ledger entries
        """
        from django.db.models import Sum, Case, When

        result = cls.objects.filter(account_id=account_id).aggregate(
            balance=Sum(
                Case(
                    When(entry_type=EntryType.DEBIT, then=-models.F("amount")),
                    When(entry_type=EntryType.CREDIT, then=models.F("amount")),
                    default=Decimal("0"),
                )
            )
        )
        return result["balance"] or Decimal("0")