"""Serializers for ledger app."""

from rest_framework import serializers

from .models import EntryType, LedgerEntry


class LedgerEntrySerializer(serializers.ModelSerializer):
    """Serializer for LedgerEntry model."""

    entry_type_display = serializers.CharField(source="get_entry_type_display", read_only=True)
    account_number = serializers.CharField(source="account.account_number", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "transaction_id",
            "account_number",
            "entry_type",
            "entry_type_display",
            "amount",
            "balance_before",
            "balance_after",
            "description",
            "correlation_id",
            "created_at",
        ]
        read_only_fields = fields


class StatementSerializer(serializers.Serializer):
    """Serializer for statement response."""

    account_id = serializers.UUIDField()
    account_number = serializers.CharField()
    balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField()
    entries = LedgerEntrySerializer(many=True)
    total_credits = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_debits = serializers.DecimalField(max_digits=18, decimal_places=2)
    as_of = serializers.DateTimeField()