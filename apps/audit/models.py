"""Audit models for immutable logging."""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    """Immutable audit log entry with hash chaining."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_id = models.UUIDField(
        _("actor ID"),
        db_index=True,
        help_text=_("ID of the user or system performing the action"),
    )
    action = models.CharField(
        _("action"),
        max_length=100,
        db_index=True,
        help_text=_("Action performed"),
    )
    payload = models.JSONField(
        _("payload"),
        default=dict,
        help_text=_("Action payload"),
    )
    payload_hash = models.CharField(
        _("payload hash"),
        max_length=64,
        help_text=_("SHA-256 hash of the payload"),
    )
    previous_hash = models.CharField(
        _("previous hash"),
        max_length=64,
        default="",
        help_text=_("Hash of the previous audit entry"),
    )
    current_hash = models.CharField(
        _("current hash"),
        max_length=64,
        help_text=_("Hash of this entry (includes previous hash)"),
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name = _("Audit Log")
        verbose_name_plural = _("Audit Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor_id", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]
        get_latest_by = "created_at"

    def __str__(self) -> str:
        return f"{self.action} by {self.actor_id} at {self.created_at}"

    @property
    def is_tampered(self) -> bool:
        """Check if this entry has been tampered with."""
        import hashlib

        expected_hash = hashlib.sha256(
            f"{self.previous_hash or ''}{self.actor_id}{self.action}{self.payload_hash}".encode()
        ).hexdigest()

        return self.current_hash != expected_hash