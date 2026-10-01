"""Serializers for transactions app."""

from decimal import Decimal

from rest_framework import serializers

from .models import IdempotencyRecord, Transaction, TransactionStatus, TransactionType


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model."""

    transaction_type_display = serializers.CharField(source="get_transaction_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_account_number = serializers.CharField(source="source_account.account_number", read_only=True, allow_null=True)
    destination_account_number = serializers.CharField(source="destination_account.account_number", read_only=True, allow_null=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_type",
            "transaction_type_display",
            "status",
            "status_display",
            "amount",
            "currency",
            "source_account",
            "source_account_number",
            "destination_account",
            "destination_account_number",
            "reference",
            "failure_reason",
            "fraud_check_result",
            "correlation_id",
            "requested_at",
            "fraud_checked_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "fraud_check_result",
            "correlation_id",
            "requested_at",
            "fraud_checked_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]


class DepositSerializer(serializers.Serializer):
    """Serializer for deposit requests."""

    account_id = serializers.UUIDField()
    amount = serializers.DecimalField(min_value=Decimal("0.01"), max_digits=18, decimal_places=2)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    idempotency_key = serializers.UUIDField(required=False)

    def validate_account_id(self, value):
        """Validate account exists and belongs to user."""
        from apps.accounts.models import Account

        try:
            account = Account.objects.get(id=value, status="ACTIVE")
            self.context["account"] = account
        except Account.DoesNotExist:
            raise serializers.ValidationError("Conta não encontrada ou inativa.")
        return value

    def validate_amount(self, value):
        """Validate amount against limits."""
        account = self.context.get("account")
        if account:
            if value > account.transaction_limit:
                raise serializers.ValidationError(
                    f"Valor excede o limite por transação de {account.transaction_limit}"
                )
        return value


class WithdrawalSerializer(serializers.Serializer):
    """Serializer for withdrawal requests."""

    account_id = serializers.UUIDField()
    amount = serializers.DecimalField(min_value=Decimal("0.01"), max_digits=18, decimal_places=2)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    idempotency_key = serializers.UUIDField(required=False)

    def validate_account_id(self, value):
        """Validate account exists and belongs to user."""
        from apps.accounts.models import Account

        try:
            account = Account.objects.get(id=value, status="ACTIVE")
            self.context["account"] = account
        except Account.DoesNotExist:
            raise serializers.ValidationError("Conta não encontrada ou inativa.")
        return value

    def validate_amount(self, value):
        """Validate amount against balance and limits."""
        account = self.context.get("account")
        if account:
            if value > account.balance:
                raise serializers.ValidationError(
                    f"Saldo insuficiente. Disponível: {account.balance}"
                )
            if value > account.transaction_limit:
                raise serializers.ValidationError(
                    f"Valor excede o limite por transação de {account.transaction_limit}"
                )
            if value > account._get_remaining_daily_limit():
                raise serializers.ValidationError(
                    f"Valor excede o limite diário disponível ({account._get_remaining_daily_limit()})"
                )
        return value


class TransferSerializer(serializers.Serializer):
    """Serializer for transfer requests."""

    source_account_id = serializers.UUIDField()
    destination_account_number = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(min_value=Decimal("0.01"), max_digits=18, decimal_places=2)
    reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    idempotency_key = serializers.UUIDField(required=False)

    def validate_source_account_id(self, value):
        """Validate source account."""
        from apps.accounts.models import Account

        try:
            account = Account.objects.get(id=value, status="ACTIVE")
            self.context["source_account"] = account
        except Account.DoesNotExist:
            raise serializers.ValidationError("Conta de origem não encontrada ou inativa.")
        return value

    def validate_destination_account_number(self, value):
        """Validate destination account."""
        from apps.accounts.models import Account

        try:
            dest_account = Account.objects.get(
                account_number=value,
                status="ACTIVE",
            )
            source_account = self.context.get("source_account")

            if source_account and dest_account.id == source_account.id:
                raise serializers.ValidationError(
                    "Não é possível transferir para a mesma conta."
                )

            self.context["destination_account"] = dest_account
        except Account.DoesNotExist:
            raise serializers.ValidationError("Conta de destino não encontrada ou inativa.")
        return value

    def validate_amount(self, value):
        """Validate amount against limits."""
        account = self.context.get("source_account")
        if account:
            if value > account.balance:
                raise serializers.ValidationError(
                    f"Saldo insuficiente. Disponível: {account.balance}"
                )
            if value > account.transaction_limit:
                raise serializers.ValidationError(
                    f"Valor excede o limite por transação de {account.transaction_limit}"
                )
            if value > account._get_remaining_daily_limit():
                raise serializers.ValidationError(
                    f"Valor excede o limite diário disponível ({account._get_remaining_daily_limit()})"
                )
        return value


class TransactionCreateResponseSerializer(serializers.Serializer):
    """Serializer for transaction creation response."""

    transaction_id = serializers.UUIDField()
    status = serializers.CharField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField()
    created_at = serializers.DateTimeField()


class ReversalSerializer(serializers.Serializer):
    """Serializer for reversal requests."""

    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
    idempotency_key = serializers.UUIDField(required=False)