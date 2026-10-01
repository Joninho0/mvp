"""Tests for account models."""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Account, AccountStatus


@pytest.mark.django_db
class TestAccountModel:
    """Tests for Account model."""

    def test_account_creation(self, test_user):
        """Test creating an account."""
        account = Account.objects.create(
            customer=test_user,
            account_number=Account.generate_account_number(),
            account_type="CHECKING",
            balance=Decimal("1000.00"),
        )

        assert account.id is not None
        assert account.customer == test_user
        assert account.account_type == "CHECKING"
        assert account.status == AccountStatus.ACTIVE
        assert account.balance == Decimal("1000.00")

    def test_account_number_generation(self, test_user):
        """Test account number generation."""
        account1 = Account.objects.create(
            customer=test_user,
            account_number=Account.generate_account_number(),
            account_type="CHECKING",
        )
        account2 = Account.objects.create(
            customer=test_user,
            account_number=Account.generate_account_number(),
            account_type="CHECKING",
        )

        # Numbers should be unique and properly formatted
        assert account1.account_number != account2.account_number
        assert len(account1.account_number) == 11  # 3 digits + dash + 7 digits
        assert "-" in account1.account_number

    def test_account_status_transitions(self, test_account):
        """Test account status changes."""
        # Block account
        test_account.block("Suspected fraud")
        assert test_account.status == AccountStatus.BLOCKED
        assert test_account.blocked_at is not None

        # Unblock account
        test_account.unblock()
        assert test_account.status == AccountStatus.ACTIVE
        assert test_account.blocked_at is None

    def test_daily_limit_reset(self, test_account):
        """Test daily limit reset."""
        initial_limit = test_account.daily_limit

        # Use some limit
        test_account.daily_used = Decimal("500.00")
        test_account.save()

        # Reset
        test_account.reset_daily_limits()

        # Limit should be reset
        assert test_account.daily_used == Decimal("0")
        assert test_account.daily_limit == initial_limit

    def test_can_debit(self, test_account):
        """Test debit permission."""
        # Can debit when balance is sufficient
        assert test_account.can_debit(Decimal("500.00")) is True

        # Cannot debit more than balance
        assert test_account.can_debit(Decimal("2000.00")) is False

    def test_account_string_representation(self, test_account):
        """Test string representation."""
        expected = f"{test_account.account_number} ({test_account.get_status_display()})"
        assert str(test_account) == expected