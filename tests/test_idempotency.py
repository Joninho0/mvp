"""Tests for idempotency handling."""

import uuid
from decimal import Decimal

import pytest

from core.idempotency import IdempotencyRecord, generate_idempotency_key, validate_idempotency_key


class TestIdempotencyKey:
    """Tests for idempotency key utilities."""

    def test_generate_idempotency_key(self):
        """Test generating idempotency keys."""
        key1 = generate_idempotency_key()
        key2 = generate_idempotency_key()

        # Keys should be valid UUIDs
        assert validate_idempotency_key(key1) is True
        assert validate_idempotency_key(key2) is True

        # Keys should be unique
        assert key1 != key2

    def test_validate_idempotency_key(self):
        """Test validating idempotency keys."""
        assert validate_idempotency_key(str(uuid.uuid4())) is True
        assert validate_idempotency_key("invalid") is False
        assert validate_idempotency_key("") is False
        assert validate_idempotency_key(None) is False

    def test_idempotency_record_creation(self):
        """Test creating idempotency records."""
        key = str(uuid.uuid4())
        request_body = {"type": "transfer", "amount": "100.00"}

        record = IdempotencyRecord.create(
            key=key,
            request_body=request_body,
        )

        assert record.key == key
        assert record.status.value == "IN_PROGRESS"
        assert record.response is None

    def test_idempotency_record_completion(self):
        """Test marking idempotency record as completed."""
        record = IdempotencyRecord.create(
            key=str(uuid.uuid4()),
            request_body={"type": "deposit"},
        )

        response = {"transaction_id": "123", "status": "completed"}
        record.mark_completed(response)

        assert record.status.value == "COMPLETED"
        assert record.response == response

    def test_request_hash_matching(self):
        """Test that request hashes match correctly."""
        key = str(uuid.uuid4())
        request_body = {"amount": "100.00", "type": "transfer"}

        record = IdempotencyRecord.create(key=key, request_body=request_body)

        # Same request should match
        assert record.matches_request(request_body) is True

        # Different request should not match
        assert record.matches_request({"amount": "200.00"}) is False

    def test_idempotency_record_expiry(self):
        """Test idempotency record expiration."""
        from datetime import timedelta
        from django.utils import timezone

        key = str(uuid.uuid4())
        record = IdempotencyRecord.create(
            key=key,
            request_body={"type": "test"},
            expires_at=timezone.now() - timedelta(hours=1),
        )

        # Record should be expired
        assert record.is_expired() is True

        # Set to future
        record.expires_at = timezone.now() + timedelta(days=1)
        assert record.is_expired() is False