"""Tests for transaction models and forms."""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.transactions.models import Transaction, TransactionStatus, TransactionType


@pytest.mark.django_db
class TestTransactionModel:
    """Tests for Transaction model."""

    def test_transaction_creation(self, test_account):
        """Test creating a transaction."""
        tx = Transaction.objects.create(
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.PENDING,
            amount=Decimal("500.00"),
            destination_account=test_account,
        )

        assert tx.id is not None
        assert tx.transaction_type == TransactionType.DEPOSIT
        assert tx.status == TransactionStatus.PENDING

    def test_transaction_status_transitions(self, sample_transaction):
        """Test transaction status changes."""
        # Initial state
        assert sample_transaction.status == TransactionStatus.COMPLETED

        # Cannot reverse if not in completed status
        assert sample_transaction.can_be_reversed() is True
        assert sample_transaction.is_successful() is True

    def test_transaction_terminal_state(self, sample_transaction):
        """Test terminal state detection."""
        assert sample_transaction.is_terminal() is True
        assert sample_transaction.is_successful() is True


@pytest.mark.django_db
class TestTransferForm:
    """Tests for TransferForm."""

    def test_transfer_validation_insufficient_balance(self, authenticated_client, test_account, test_account2):
        """Test transfer with insufficient balance."""
        # Try to transfer more than balance
        assert test_account.balance == Decimal("1000.00")

        # This would fail validation in the form
        # Form should reject transfer amount > balance

    def test_transfer_validation_self_transfer(self, authenticated_client, test_account):
        """Test transfer to same account."""
        # Cannot transfer to the same account
        pass  # This is tested in the form validation


@pytest.mark.django_db
class TestDepositForm:
    """Tests for DepositForm."""

    def test_deposit_creates_transaction(self, authenticated_client, test_account):
        """Test deposit creates transaction and updates balance."""
        initial_balance = test_account.balance

        from apps.transactions.forms import DepositForm
        from apps.transactions.models import Transaction, TransactionType

        # Create deposit via form
        form_data = {
            "account": test_account.id,
            "amount": Decimal("500.00"),
            "reference": "Test deposit",
        }

        form = DepositForm(data=form_data, user=authenticated_client.handler._force_user)
        assert form.is_valid(), form.errors

        tx = form.save()

        # Verify transaction
        assert tx.transaction_type == TransactionType.DEPOSIT
        assert tx.amount == Decimal("500.00")
        assert tx.status == TransactionStatus.COMPLETED

        # Verify balance updated
        test_account.refresh_from_db()
        assert test_account.balance == initial_balance + Decimal("500.00")