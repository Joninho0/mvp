"""
Account models for the bank.

This module contains the Account model representing customer bank accounts.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class AccountStatus(models.TextChoices):
    """Status of an account."""

    ACTIVE = "ACTIVE", _("Active")
    BLOCKED = "BLOCKED", _("Blocked")
    CLOSED = "CLOSED", _("Closed")


class AccountType(models.TextChoices):
    """Type of bank account."""

    CHECKING = "CHECKING", _("Checking Account")
    SAVINGS = "SAVINGS", _("Savings Account")
    BUSINESS = "BUSINESS", _("Business Account")


class Account(models.Model):
    """
    Represents a bank account for a customer.

    The balance is maintained as a cache/reconciliation point.
    The actual ledger of transactions is maintained in LedgerEntry.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="accounts",
        verbose_name=_("customer"),
    )
    account_number = models.CharField(
        _("account number"),
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_("Unique account number"),
    )
    account_type = models.CharField(
        _("account type"),
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.CHECKING,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    balance = models.DecimalField(
        _("balance"),
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Current balance (cached from ledger)"),
    )
    currency = models.CharField(
        _("currency"),
        max_length=3,
        default="BRL",
        help_text=_("ISO 4217 currency code"),
    )
    version = models.PositiveIntegerField(
        _("version"),
        default=1,
        help_text=_("Optimistic locking version"),
    )
    daily_limit = models.DecimalField(
        _("daily limit"),
        max_digits=18,
        decimal_places=2,
        default=Decimal("10000.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Maximum daily transaction amount"),
    )
    daily_used = models.DecimalField(
        _("daily used"),
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Amount used today"),
    )
    daily_limit_reset_at = models.DateTimeField(
        _("daily limit reset at"),
        null=True,
        blank=True,
    )
    transaction_limit = models.DecimalField(
        _("transaction limit"),
        max_digits=18,
        decimal_places=2,
        default=Decimal("5000.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Maximum amount per transaction"),
    )
    opened_at = models.DateTimeField(
        _("opened at"),
        auto_now_add=True,
    )
    blocked_at = models.DateTimeField(
        _("blocked at"),
        null=True,
        blank=True,
    )
    blocked_reason = models.TextField(
        _("block reason"),
        null=True,
        blank=True,
    )
    closed_at = models.DateTimeField(
        _("closed at"),
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
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account_number"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["status", "currency"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(balance__gte=Decimal("0.00")),
                name="non_negative_balance",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.account_number} ({self.get_status_display()})"

    def is_active(self) -> bool:
        """Check if the account is active."""
        return self.status == AccountStatus.ACTIVE

    def is_blocked(self) -> bool:
        """Check if the account is blocked."""
        return self.status == AccountStatus.BLOCKED

    def can_debit(self, amount: Decimal) -> bool:
        """Check if the account can be debited the specified amount."""
        return (
            self.is_active()
            and self.balance >= amount
            and self._get_remaining_daily_limit() >= amount
        )

    def _get_remaining_daily_limit(self) -> Decimal:
        """Get the remaining daily limit."""
        from django.utils import timezone

        if (
            self.daily_limit_reset_at is None
            or self.daily_limit_reset_at.date() < timezone.now().date()
        ):
            return self.daily_limit
        return self.daily_limit - self.daily_used

    def reset_daily_limits(self) -> None:
        """Reset daily limits if the reset date has passed."""
        from django.utils import timezone

        now = timezone.now()
        if (
            self.daily_limit_reset_at is None
            or self.daily_limit_reset_at.date() < now.date()
        ):
            self.daily_used = Decimal("0")
            self.daily_limit_reset_at = now
            self.save(update_fields=["daily_used", "daily_limit_reset_at"])

    def update_balance(self, amount: Decimal) -> None:
        """
        Update the balance with optimistic locking.

        Args:
            amount: The amount to add (positive) or subtract (negative)

        Raises:
            ValueError: If the resulting balance would be negative
            django.db.models.deletion.MultipleObjectsReturned: If there's a concurrent update
        """
        from django.db import transaction

        new_balance = self.balance + amount
        if new_balance < Decimal("0"):
            raise ValueError("Insufficient funds")

        # Use F expression for atomic update
        from django.db.models import F

        updated = Account.objects.filter(
            id=self.id,
            version=self.version,
        ).update(
            balance=F("balance") + amount,
            version=F("version") + 1,
        )

        if updated == 0:
            raise ValueError("Concurrent update detected")

        # Refresh from database
        Account.objects.refresh_from_db(self)
        self.refresh_from_db()

    def block(self, reason: str) -> None:
        """Block the account."""
        from django.utils import timezone

        self.status = AccountStatus.BLOCKED
        self.blocked_at = timezone.now()
        self.blocked_reason = reason
        self.save(update_fields=["status", "blocked_at", "blocked_reason"])

    def unblock(self) -> None:
        """Unblock the account."""
        self.status = AccountStatus.ACTIVE
        self.blocked_at = None
        self.blocked_reason = None
        self.save(update_fields=["status", "blocked_at", "blocked_reason"])

    def close(self) -> None:
        """Close the account if balance is zero."""
        if self.balance != Decimal("0"):
            raise ValueError("Cannot close account with non-zero balance")
        from django.utils import timezone

        self.status = AccountStatus.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=["status", "closed_at"])