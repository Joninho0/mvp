"""Tests for ledger models."""

from decimal import Decimal

import pytest

from apps.ledger.models import EntryType, LedgerEntry


@pytest.mark.django_db
class TestLedgerEntry:
    """Tests for LedgerEntry model."""

    def test_create_ledger_entry(self, test_account):
        """Test creating a ledger entry."""
        entry = LedgerEntry.create_entry(
            transaction_id="test-uuid",
            account=test_account,
            entry_type=EntryType.CREDIT,
            amount=Decimal("100.00"),
            balance_before=Decimal("1000.00"),
            description="Test deposit",
        )

        assert entry.id is not None
        assert entry.entry_type == EntryType.CREDIT
        assert entry.amount == Decimal("100.00")
        assert entry.balance_after == Decimal("1100.00")

    def test_transfer_entries_balance(self, test_account, test_account2):
        """Test that transfer entries sum to zero."""
        # Initial balances
        source_balance_before = test_account.balance
        dest_balance_before = test_account2.balance

        amount = Decimal("100.00")

        # Create transfer entries
        debit_entry, credit_entry = LedgerEntry.create_transfer_entries(
            transaction_id="test-uuid",
            source_account=test_account,
            destination_account=test_account2,
            amount=amount,
            description="Test transfer",
        )

        # Verify entry amounts
        assert debit_entry.entry_type == EntryType.DEBIT
        assert debit_entry.amount == amount
        assert credit_entry.entry_type == EntryType.CREDIT
        assert credit_entry.amount == amount

        # Verify balances are updated
        assert test_account.balance == source_balance_before - amount
        assert test_account2.balance == dest_balance_before + amount

    def test_get_account_balance(self, test_account, sample_transaction):
        """Test calculating balance from ledger."""
        # Create additional entries
        LedgerEntry.create_entry(
            transaction_id="test-uuid-2",
            account=test_account,
            entry_type=EntryType.DEBIT,
            amount=Decimal("200.00"),
            balance_before=Decimal("1500.00"),
            description="Test debit",
        )

        # Calculate balance from ledger
        calculated = LedgerEntry.get_account_balance(test_account.id)

        # Should match account balance
        assert calculated == test_account.balance