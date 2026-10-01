"""Tests for REST API endpoints."""

import uuid
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import Account
from apps.transactions.models import Transaction, TransactionType


@pytest.mark.django_db
class TestAccountAPI:
    """Tests for Account API endpoints."""

    def test_list_accounts(self, authenticated_client, test_account):
        """Test listing accounts."""
        response = authenticated_client.get("/api/accounts/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_get_account_detail(self, authenticated_client, test_account):
        """Test getting account details."""
        response = authenticated_client.get(f"/api/accounts/{test_account.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["account_number"] == test_account.account_number

    def test_get_account_balance(self, authenticated_client, test_account):
        """Test getting account balance."""
        response = authenticated_client.get(f"/api/accounts/{test_account.id}/balance/")
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data["balance"]) == test_account.balance


@pytest.mark.django_db
class TestTransactionAPI:
    """Tests for Transaction API endpoints."""

    def test_create_deposit(self, authenticated_client, test_account):
        """Test creating a deposit."""
        data = {
            "account_id": str(test_account.id),
            "amount": "100.00",
            "reference": "Test deposit",
        }

        response = authenticated_client.post(
            "/api/transactions/deposit/",
            data,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data["amount"]) == Decimal("100.00")

        # Verify account balance updated
        test_account.refresh_from_db()
        assert test_account.balance == Decimal("1100.00")  # 1000 + 100

    def test_create_transfer(self, authenticated_client, test_account, test_account2):
        """Test creating a transfer."""
        data = {
            "source_account_id": str(test_account.id),
            "destination_account_number": test_account2.account_number,
            "amount": "100.00",
            "reference": "Test transfer",
        }

        response = authenticated_client.post(
            "/api/transactions/transfer/",
            data,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Decimal(response.data["amount"]) == Decimal("100.00")

        # Verify balances
        test_account.refresh_from_db()
        test_account2.refresh_from_db()

        assert test_account.balance == Decimal("900.00")  # 1000 - 100
        assert test_account2.balance == Decimal("2100.00")  # 2000 + 100

    def test_transfer_insufficient_balance(self, authenticated_client, test_account, test_account2):
        """Test transfer with insufficient balance."""
        data = {
            "source_account_id": str(test_account.id),
            "destination_account_number": test_account2.account_number,
            "amount": "999999.00",  # More than balance
            "reference": "Test transfer",
        }

        response = authenticated_client.post(
            "/api/transactions/transfer/",
            data,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_transaction_detail(self, authenticated_client, sample_transaction):
        """Test getting transaction details."""
        response = authenticated_client.get(
            f"/api/transactions/{sample_transaction.id}/"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_idempotency(self, authenticated_client, test_account):
        """Test idempotency key works."""
        idempotency_key = uuid.uuid4()

        data = {
            "account_id": str(test_account.id),
            "amount": "50.00",
            "idempotency_key": str(idempotency_key),
        }

        # First request
        response1 = authenticated_client.post(
            "/api/transactions/deposit/",
            data,
            format="json",
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Second request with same key
        response2 = authenticated_client.post(
            "/api/transactions/deposit/",
            data,
            format="json",
        )

        # Should return the same transaction
        assert response2.status_code == status.HTTP_200_OK
        assert response1.data["transaction_id"] == response2.data["transaction_id"]