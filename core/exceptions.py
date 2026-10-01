"""
Custom exceptions for the bank API.

This module defines domain-specific exceptions that provide
clear error messages and consistent error responses.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Error codes for the bank API."""

    # Authentication errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    MFA_REQUIRED = "MFA_REQUIRED"
    MFA_INVALID = "MFA_INVALID"

    # Customer errors
    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"
    CUSTOMER_ALREADY_EXISTS = "CUSTOMER_ALREADY_EXISTS"
    CPF_INVALID = "CPF_INVALID"
    CPF_ALREADY_REGISTERED = "CPF_ALREADY_REGISTERED"
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
    KYC_INCOMPLETE = "KYC_INCOMPLETE"

    # Account errors
    ACCOUNT_NOT_FOUND = "ACCOUNT_NOT_FOUND"
    ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED"
    ACCOUNT_CLOSED = "ACCOUNT_CLOSED"
    ACCOUNT_LIMIT_EXCEEDED = "ACCOUNT_LIMIT_EXCEEDED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"

    # Transaction errors
    TRANSACTION_NOT_FOUND = "TRANSACTION_NOT_FOUND"
    TRANSACTION_INVALID = "TRANSACTION_INVALID"
    TRANSACTION_ALREADY_PROCESSED = "TRANSACTION_ALREADY_PROCESSED"
    TRANSACTION_PENDING = "TRANSACTION_PENDING"
    TRANSACTION_FAILED = "TRANSACTION_FAILED"
    DUPLICATE_TRANSACTION = "DUPLICATE_TRANSACTION"
    INVALID_AMOUNT = "INVALID_AMOUNT"
    AMOUNT_TOO_SMALL = "AMOUNT_TOO_SMALL"
    AMOUNT_TOO_LARGE = "AMOUNT_TOO_LARGE"

    # Idempotency errors
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    IDEMPOTENCY_KEY_MISMATCH = "IDEMPOTENCY_KEY_MISMATCH"
    IDEMPOTENCY_IN_PROGRESS = "IDEMPOTENCY_IN_PROGRESS"
    IDEMPOTENCY_EXPIRED = "IDEMPOTENCY_EXPIRED"

    # Security errors
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    FRAUD_DETECTED = "FRAUD_DETECTED"

    # System errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"


@dataclass
class ApiError:
    """Represents an API error response."""

    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "error": {
                "code": self.code.value,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result


class BankException(Exception):
    """Base exception for bank errors."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def to_api_error(self) -> ApiError:
        """Convert to API error format."""
        return ApiError(code=self.code, message=self.message, details=self.details)


class AuthenticationError(BankException):
    """Exception raised for authentication failures."""

    def __init__(
        self,
        message: str = "Invalid credentials",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code=ErrorCode.INVALID_CREDENTIALS, message=message, details=details)


class CustomerNotFoundError(BankException):
    """Exception raised when a customer is not found."""

    def __init__(self, customer_id: str) -> None:
        super().__init__(
            code=ErrorCode.CUSTOMER_NOT_FOUND,
            message=f"Customer with id '{customer_id}' not found",
            details={"customer_id": customer_id},
        )


class CustomerAlreadyExistsError(BankException):
    """Exception raised when attempting to create a customer that already exists."""

    def __init__(self, field: str, value: str) -> None:
        super().__init__(
            code=ErrorCode.CUSTOMER_ALREADY_EXISTS,
            message=f"Customer with {field} '{value}' already exists",
            details={field: value},
        )


class AccountNotFoundError(BankException):
    """Exception raised when an account is not found."""

    def __init__(self, account_id: str) -> None:
        super().__init__(
            code=ErrorCode.ACCOUNT_NOT_FOUND,
            message=f"Account with id '{account_id}' not found",
            details={"account_id": account_id},
        )


class AccountBlockedError(BankException):
    """Exception raised when an account is blocked."""

    def __init__(self, account_id: str, reason: str | None = None) -> None:
        details: dict[str, Any] = {"account_id": account_id}
        if reason:
            details["reason"] = reason
        super().__init__(
            code=ErrorCode.ACCOUNT_BLOCKED,
            message=f"Account '{account_id}' is blocked",
            details=details,
        )


class InsufficientFundsError(BankException):
    """Exception raised when there are insufficient funds for a transaction."""

    def __init__(
        self,
        account_id: str,
        available: str,
        requested: str,
    ) -> None:
        super().__init__(
            code=ErrorCode.INSUFFICIENT_FUNDS,
            message=f"Insufficient funds in account '{account_id}'",
            details={
                "account_id": account_id,
                "available": available,
                "requested": requested,
            },
        )


class InvalidTransactionError(BankException):
    """Exception raised for invalid transaction requests."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.TRANSACTION_INVALID,
            message=message,
            details=details,
        )


class DuplicateTransactionError(BankException):
    """Exception raised when a duplicate transaction is detected."""

    def __init__(self, idempotency_key: str) -> None:
        super().__init__(
            code=ErrorCode.DUPLICATE_TRANSACTION,
            message=f"Transaction with idempotency key '{idempotency_key}' already processed",
            details={"idempotency_key": idempotency_key},
        )


class FraudDetectedError(BankException):
    """Exception raised when fraud is detected."""

    def __init__(
        self,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.FRAUD_DETECTED,
            message=f"Fraud detected: {reason}",
            details=details or {"reason": reason},
        )


class RateLimitExceededError(BankException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, limit: str, window: str) -> None:
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=f"Rate limit exceeded. Limit: {limit} requests per {window}",
            details={"limit": limit, "window": window},
        )


class IdempotencyConflictError(BankException):
    """Exception raised when there's an idempotency conflict."""

    def __init__(self, existing_status: str) -> None:
        super().__init__(
            code=ErrorCode.IDEMPOTENCY_CONFLICT,
            message=f"Idempotency key is currently being processed ({existing_status})",
            details={"status": existing_status},
        )


class IdempotencyKeyMismatchError(BankException):
    """Exception raised when the request body doesn't match the recorded idempotency key."""

    def __init__(self) -> None:
        super().__init__(
            code=ErrorCode.IDEMPOTENCY_KEY_MISMATCH,
            message="Request body does not match the original request for this idempotency key",
        )


class ValidationError(BankException):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        errors: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=errors,
        )