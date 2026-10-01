"""Serializers for accounts app."""

from rest_framework import serializers

from .models import Account, AccountStatus


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Account model."""

    account_type_display = serializers.CharField(source="get_account_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    remaining_daily_limit = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id",
            "account_number",
            "account_type",
            "account_type_display",
            "status",
            "status_display",
            "balance",
            "currency",
            "daily_limit",
            "remaining_daily_limit",
            "transaction_limit",
            "opened_at",
            "blocked_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "account_number",
            "balance",
            "opened_at",
            "blocked_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]

    def get_remaining_daily_limit(self, obj):
        """Calculate remaining daily limit."""
        return obj._get_remaining_daily_limit()


class AccountCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating accounts."""

    class Meta:
        model = Account
        fields = [
            "account_type",
            "daily_limit",
            "transaction_limit",
        ]

    def create(self, validated_data):
        """Create account with generated account number."""
        from apps.accounts.models import Account as AccountModel

        validated_data["customer"] = self.context["request"].user
        validated_data["account_number"] = AccountModel.generate_account_number()
        return super().create(validated_data)


class AccountBalanceSerializer(serializers.Serializer):
    """Serializer for balance response."""

    account_id = serializers.UUIDField()
    balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField()
    as_of = serializers.DateTimeField()