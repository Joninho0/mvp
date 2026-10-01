"""Celery tasks for fraud detection."""

import logging
from datetime import timedelta
from uuid import uuid4

from celery import shared_task
from django.conf import settings
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.transactions.models import Transaction, TransactionStatus

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def check_fraud(self, transaction_id: str):
    """
    Check transaction for fraud patterns.

    This is an async task that can be called after a transaction is created.
    """
    try:
        tx = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} not found")
        return {"status": "error", "message": "Transaction not found"}

    # Run fraud check
    result = FraudChecker.check_transaction(tx)

    # Update transaction status
    if result["passed"]:
        tx.mark_fraud_check_passed(result)
        logger.info(f"Fraud check passed for transaction {transaction_id}")
    else:
        tx.mark_fraud_check_failed(result.get("reason", "Fraud detected"))
        logger.warning(f"Fraud check failed for transaction {transaction_id}: {result}")

    # Trigger notification if fraud detected
    if not result["passed"]:
        from apps.notifications.tasks import send_transaction_notification

        send_transaction_notification.delay(
            str(tx.id),
            "failed",
        )

    return {
        "status": "success" if result["passed"] else "failed",
        "transaction_id": transaction_id,
        "result": result,
    }


class FraudChecker:
    """Fraud detection rules engine."""

    THRESHOLDS = {
        "high_value": 10000,  # BRL
        "daily_transactions": 10,
        "new_account_days": 7,
        "hourly_transactions": 5,
        "large_transfer_ratio": 0.9,  # 90% of balance
    }

    @classmethod
    def check_transaction(cls, transaction: Transaction) -> dict:
        """
        Run all fraud checks on a transaction.

        Returns:
            dict with 'passed' (bool) and optional 'reason' (str)
        """
        checks = [
            cls._check_high_value,
            cls._check_daily_volume,
            cls._check_new_account,
            cls._check_frequency,
            cls._check_transfer_ratio,
        ]

        for check in checks:
            result = check(transaction)
            if not result["passed"]:
                return result

        return {"passed": True}

    @classmethod
    def _check_high_value(cls, transaction: Transaction) -> dict:
        """Check if transaction amount is unusually high."""
        if transaction.amount >= Decimal(str(cls.THRESHOLDS["high_value"])):
            return {
                "passed": False,
                "reason": f"Valor alto detectado: {transaction.amount}",
                "rule": "high_value",
            }
        return {"passed": True}

    @classmethod
    def _check_daily_volume(cls, transaction: Transaction) -> dict:
        """Check if daily transaction volume is exceeded."""
        if not transaction.source_account:
            return {"passed": True}

        today = timezone.now().date()
        daily_total = Transaction.objects.filter(
            source_account=transaction.source_account,
            created_at__date=today,
            status__in=[TransactionStatus.COMPLETED, TransactionStatus.PROCESSING],
        ).exclude(id=transaction.id).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")

        if daily_total + transaction.amount >= Decimal(str(cls.THRESHOLDS["daily_transactions"])):
            return {
                "passed": False,
                "reason": "Limite diário de transações excedido",
                "rule": "daily_volume",
            }
        return {"passed": True}

    @classmethod
    def _check_new_account(cls, transaction: Transaction) -> dict:
        """Check if account is too new."""
        if not transaction.source_account:
            return {"passed": True}

        account_age = timezone.now() - transaction.source_account.opened_at
        if account_age < timedelta(days=cls.THRESHOLDS["new_account_days"]):
            return {
                "passed": False,
                "reason": "Conta nova - transferência limitada",
                "rule": "new_account",
            }
        return {"passed": True}

    @classmethod
    def _check_frequency(cls, transaction: Transaction) -> dict:
        """Check for too many transactions in short period."""
        if not transaction.source_account:
            return {"passed": True}

        hour_ago = timezone.now() - timedelta(hours=1)
        recent_count = Transaction.objects.filter(
            source_account=transaction.source_account,
            created_at__gte=hour_ago,
            status__in=[TransactionStatus.COMPLETED, TransactionStatus.PROCESSING],
        ).exclude(id=transaction.id).count()

        if recent_count >= cls.THRESHOLDS["hourly_transactions"]:
            return {
                "passed": False,
                "reason": "Muitas transações em pouco tempo",
                "rule": "frequency",
            }
        return {"passed": True}

    @classmethod
    def _check_transfer_ratio(cls, transaction: Transaction) -> dict:
        """Check if transfer exceeds balance ratio."""
        if not transaction.source_account:
            return {"passed": True}

        balance = transaction.source_account.balance
        ratio = transaction.amount / balance if balance > 0 else 1

        if ratio >= cls.THRESHOLDS["large_transfer_ratio"]:
            return {
                "passed": False,
                "reason": "Transferência muito grande em relação ao saldo",
                "rule": "transfer_ratio",
            }
        return {"passed": True}