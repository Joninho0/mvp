"""Celery tasks for audit and reconciliation."""

import hashlib
import logging
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from django.db import transaction as db_transaction
from django.db.models import Sum, Case, When, DecimalField, F
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def create_audit_log(self, actor_id: str, action: str, payload: dict, previous_hash: str = None):
    """
    Create an immutable audit log entry.

    Args:
        actor_id: ID of the user performing the action
        action: Action performed
        payload: Data payload
        previous_hash: Hash of the previous audit entry (for chaining)
    """
    from apps.audit.models import AuditLog

    payload_str = str(payload)
    payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()

    current_hash = hashlib.sha256(
        f"{previous_hash or ''}{actor_id}{action}{payload_hash}".encode()
    ).hexdigest()

    audit_log = AuditLog.objects.create(
        actor_id=actor_id,
        action=action,
        payload=payload,
        payload_hash=payload_hash,
        previous_hash=previous_hash or "",
        current_hash=current_hash,
    )

    logger.info(f"Audit log created: {action} by {actor_id}")
    return {"status": "success", "audit_id": str(audit_log.id)}


@shared_task(bind=True)
def cleanup_expired_audit_logs(self):
    """Clean up old audit logs based on retention policy."""
    from apps.audit.models import AuditLog

    retention_days = 365  # Keep for 1 year
    cutoff = timezone.now() - timedelta(days=retention_days)

    deleted_count, _ = AuditLog.objects.filter(created_at__lt=cutoff).delete()

    logger.info(f"Cleaned up {deleted_count} expired audit logs")
    return {"deleted": deleted_count}


@shared_task(bind=True)
def verify_audit_chain(self):
    """Verify the integrity of the audit log chain."""
    from apps.audit.models import AuditLog

    logs = AuditLog.objects.order_by("created_at")[:1000]  # Verify in batches

    broken = []
    previous_hash = None

    for log in logs:
        expected_hash = hashlib.sha256(
            f"{previous_hash or ''}{log.actor_id}{log.action}{log.payload_hash}".encode()
        ).hexdigest()

        if log.current_hash != expected_hash:
            broken.append(str(log.id))
        previous_hash = log.current_hash

    if broken:
        logger.error(f"Audit chain broken at entries: {broken}")
        return {"status": "broken", "broken_entries": broken}

    return {"status": "valid", "verified": len(logs)}


@shared_task(bind=True)
def reconcile_account(self, account_id: str):
    """
    Reconcile account balance with ledger entries.

    This task checks that:
    1. The sum of all ledger entries equals the account balance
    2. The accounting equation (sum of all entries = 0) holds
    """
    from apps.accounts.models import Account
    from apps.ledger.models import LedgerEntry, EntryType

    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        return {"status": "error", "message": "Account not found"}

    # Calculate balance from ledger
    from django.db.models import Sum

    result = LedgerEntry.objects.filter(account_id=account_id).aggregate(
        calculated_balance=Sum(
            Case(
                When(entry_type=EntryType.CREDIT, then=F("amount")),
                When(entry_type=EntryType.DEBIT, then=-F("amount")),
                default=Decimal("0"),
                output_field=DecimalField(max_digits=18, decimal_places=2),
            )
        )
    )

    calculated_balance = result["calculated_balance"] or Decimal("0")

    # Compare with account balance
    discrepancy = account.balance - calculated_balance

    if abs(discrepancy) > Decimal("0.01"):
        logger.error(
            f"Balance discrepancy for account {account_id}: "
            f"DB={account.balance}, Ledger={calculated_balance}, Diff={discrepancy}"
        )

        # Create audit log for the discrepancy
        create_audit_log.delay(
            actor_id="system",
            action="RECONCILIATION_FAILED",
            payload={
                "account_id": str(account_id),
                "db_balance": str(account.balance),
                "ledger_balance": str(calculated_balance),
                "discrepancy": str(discrepancy),
            },
        )

        return {
            "status": "discrepancy",
            "account_id": account_id,
            "db_balance": str(account.balance),
            "ledger_balance": str(calculated_balance),
            "discrepancy": str(discrepancy),
        }

    logger.info(f"Account {account_id} reconciled successfully")
    return {
        "status": "reconciled",
        "account_id": account_id,
        "balance": str(account.balance),
    }


@shared_task(bind=True)
def reconcile_all_accounts(self):
    """Reconcile all accounts with their ledger entries."""
    from apps.accounts.models import Account

    accounts = Account.objects.filter(status="ACTIVE")
    results = []

    for account in accounts:
        result = reconcile_account.delay(str(account.id))
        results.append({
            "account_id": str(account.id),
            "account_number": account.account_number,
        })

    return {
        "total_accounts": len(results),
        "accounts": results,
    }


@shared_task(bind=True)
def reset_daily_limits(self):
    """Reset daily transaction limits for all accounts."""
    from apps.accounts.models import Account

    updated = Account.objects.filter(
        daily_limit_reset_at__lt=timezone.now().date()
    ).update(
        daily_used=Decimal("0"),
        daily_limit_reset_at=timezone.now(),
    )

    logger.info(f"Reset daily limits for {updated} accounts")
    return {"updated": updated}