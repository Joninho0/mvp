"""Pytest configuration and fixtures for bank tests."""

import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Create an API client for testing."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(
        email="test@bank.local",
        password="testpassword123",
        first_name="Test",
        last_name="User",
    )
    return user


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Create an authenticated API client."""
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def test_account(db, test_user):
    """Create a test account."""
    from apps.accounts.models import Account

    account = Account.objects.create(
        customer=test_user,
        account_number=Account.generate_account_number(),
        account_type="CHECKING",
        balance=Decimal("1000.00"),
        daily_limit=Decimal("10000.00"),
        transaction_limit=Decimal("5000.00"),
    )
    return account


@pytest.fixture
def test_account2(db, test_user):
    """Create a second test account."""
    from apps.accounts.models import Account

    account = Account.objects.create(
        customer=test_user,
        account_number=Account.generate_account_number(),
        account_type="CHECKING",
        balance=Decimal("2000.00"),
        daily_limit=Decimal("10000.00"),
        transaction_limit=Decimal("5000.00"),
    )
    return account


@pytest.fixture
def sample_transaction(db, test_account):
    """Create a sample transaction."""
    from apps.transactions.models import Transaction, TransactionStatus, TransactionType

    transaction = Transaction.objects.create(
        transaction_type=TransactionType.DEPOSIT,
        status=TransactionStatus.COMPLETED,
        amount=Decimal("500.00"),
        destination_account=test_account,
        reference="Test deposit",
    )
    return transaction


@pytest.fixture
def sample_transfer(db, test_account, test_account2):
    """Create a sample transfer transaction."""
    from apps.transactions.models import Transaction, TransactionStatus, TransactionType

    transaction = Transaction.objects.create(
        transaction_type=TransactionType.TRANSFER,
        status=TransactionStatus.COMPLETED,
        amount=Decimal("100.00"),
        source_account=test_account,
        destination_account=test_account2,
        reference="Test transfer",
    )
    return transaction