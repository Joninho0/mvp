"""
Idempotency utilities for the bank API.

This module provides idempotency key handling to ensure that
repeated requests produce the same result without side effects.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID


class IdempotencyStatus(str, Enum):
    """Status of an idempotency record."""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class IdempotencyRecord:
    """
    Record of an idempotent request.

    Attributes:
        key: The idempotency key provided by the client
        request_hash: Hash of the request body for validation
        status: Current status of the request
        response: The response that was returned (for completed requests)
        created_at: When the record was created
        expires_at: When the record should be cleaned up
    """

    key: str
    request_hash: str
    status: IdempotencyStatus = IdempotencyStatus.IN_PROGRESS
    response: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None

    @classmethod
    def create(
        cls,
        key: str,
        request_body: dict[str, Any],
        expires_at: datetime | None = None,
    ) -> "IdempotencyRecord":
        """
        Create a new idempotency record.

        Args:
            key: The idempotency key from the client
            request_body: The request body as a dictionary
            expires_at: Optional expiration datetime

        Returns:
            New IdempotencyRecord
        """
        request_hash = cls._hash_request(request_body)
        return cls(
            key=key,
            request_hash=request_hash,
            status=IdempotencyStatus.IN_PROGRESS,
            response=None,
            expires_at=expires_at,
        )

    @staticmethod
    def _hash_request(request_body: dict[str, Any]) -> str:
        """
        Create a hash of the request body for validation.

        The hash is deterministic so the same request always produces
        the same hash.
        """
        # Ensure deterministic serialization
        body_str = json.dumps(request_body, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body_str.encode("utf-8")).hexdigest()

    def mark_completed(self, response: dict[str, Any]) -> None:
        """Mark the record as completed with the response."""
        self.status = IdempotencyStatus.COMPLETED
        self.response = response

    def mark_failed(self, response: dict[str, Any]) -> None:
        """Mark the record as failed with the response."""
        self.status = IdempotencyStatus.FAILED
        self.response = response

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if the record has expired."""
        if self.expires_at is None:
            return False
        if now is None:
            now = datetime.now(timezone.utc)
        return now > self.expires_at

    def matches_request(self, request_body: dict[str, Any]) -> bool:
        """Check if the request body matches the recorded hash."""
        return self.request_hash == self._hash_request(request_body)


def generate_idempotency_key() -> str:
    """
    Generate a new idempotency key.

    Returns:
        A UUID v4 string formatted as a key
    """
    return str(uuid.uuid4())


def validate_idempotency_key(key: str) -> bool:
    """
    Validate an idempotency key format.

    Args:
        key: The key to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        uuid.UUID(key)
        return True
    except (ValueError, AttributeError):
        return False