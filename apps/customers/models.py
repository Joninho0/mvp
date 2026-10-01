"""
Customer models for the bank.

This module contains the Customer model with KYC (Know Your Customer) information.
"""

import uuid
from typing import Any

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CustomerStatus(models.TextChoices):
    """Status of customer verification."""

    PENDING = "PENDING", _("Pending")
    VERIFIED = "VERIFIED", _("Verified")
    REJECTED = "REJECTED", _("Rejected")
    SUSPENDED = "SUSPENDED", _("Suspended")


class UserManager(BaseUserManager):
    """Custom user manager for the User model."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str, **extra_fields: Any) -> "User":
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        """Create a regular user."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        """Create a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model for the bank.

    Uses email as the primary identifier instead of username.
    Includes KYC information for customer verification.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True)
    username = None  # Remove username field
    cpf_encrypted = models.BinaryField(
        _("CPF"),
        max_length=32,
        null=True,
        blank=True,
        help_text=_("Encrypted CPF number"),
    )
    cpf_hash = models.CharField(
        _("CPF hash"),
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Hash of CPF for lookup"),
    )
    customer_status = models.CharField(
        _("customer status"),
        max_length=20,
        choices=CustomerStatus.choices,
        default=CustomerStatus.PENDING,
    )
    kyc_verified_at = models.DateTimeField(
        _("KYC verified at"),
        null=True,
        blank=True,
    )
    kyc_rejected_reason = models.TextField(
        _("KYC rejection reason"),
        null=True,
        blank=True,
    )
    phone = models.CharField(
        _("phone number"),
        max_length=20,
        null=True,
        blank=True,
    )
    address = models.JSONField(
        _("address"),
        default=dict,
        null=True,
        blank=True,
    )
    date_of_birth = models.DateField(
        _("date of birth"),
        null=True,
        blank=True,
    )
    nationality = models.CharField(
        _("nationality"),
        max_length=100,
        default="BR",
    )
    is_mfa_enabled = models.BooleanField(
        _("MFA enabled"),
        default=False,
    )
    mfa_secret = models.CharField(
        _("MFA secret"),
        max_length=32,
        null=True,
        blank=True,
    )
    last_login_ip = models.GenericIPAddressField(
        _("last login IP"),
        null=True,
        blank=True,
    )
    failed_login_attempts = models.PositiveIntegerField(
        _("failed login attempts"),
        default=0,
    )
    locked_until = models.DateTimeField(
        _("locked until"),
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

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["cpf_hash"]),
            models.Index(fields=["customer_status"]),
        ]

    def __str__(self) -> str:
        return self.email

    def is_locked(self) -> bool:
        """Check if the user account is locked."""
        if self.locked_until is None:
            return False
        return timezone.now() < self.locked_until

    def increment_failed_login(self) -> None:
        """Increment failed login counter and lock if needed."""
        from django.conf import settings

        self.failed_login_attempts += 1
        if self.failed_login_attempts >= getattr(settings, "AXES_FAILURE_LIMIT", 5):
            self.locked_until = timezone.now() + timezone.timedelta(hours=1)
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def reset_failed_login(self) -> None:
        """Reset failed login counter."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_attempts", "locked_until"])

    def verify_kyc(self) -> None:
        """Mark customer as verified."""
        self.customer_status = CustomerStatus.VERIFIED
        self.kyc_verified_at = timezone.now()
        self.save(update_fields=["customer_status", "kyc_verified_at"])

    def reject_kyc(self, reason: str) -> None:
        """Reject KYC verification."""
        self.customer_status = CustomerStatus.REJECTED
        self.kyc_rejected_reason = reason
        self.save(update_fields=["customer_status", "kyc_rejected_reason"])

    @property
    def is_kyc_verified(self) -> bool:
        """Check if customer KYC is verified."""
        return self.customer_status == CustomerStatus.VERIFIED