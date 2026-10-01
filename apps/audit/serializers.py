"""Serializers for audit app."""

from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_id",
            "action",
            "payload",
            "payload_hash",
            "previous_hash",
            "current_hash",
            "is_tampered",
            "created_at",
        ]
        read_only_fields = fields