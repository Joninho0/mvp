"""Celery tasks for notifications."""

import logging
from celery import shared_task
from django.conf import settings

from .backends import EmailBackend, LogBackend, Notification

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
)
def send_transaction_notification(self, transaction_id: str, notification_type: str):
    """
    Send transaction notification asynchronously.

    Args:
        transaction_id: UUID of the transaction
        notification_type: Type of notification (completed, failed, etc.)
    """
    from apps.transactions.models import Transaction

    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} not found")
        return {"status": "error", "message": "Transaction not found"}

    # Get customer email
    if transaction.source_account:
        email = transaction.source_account.customer.email
    elif transaction.destination_account:
        email = transaction.destination_account.customer.email
    else:
        logger.warning(f"Transaction {transaction_id} has no customer")
        return {"status": "error", "message": "No customer found"}

    # Build notification content
    subject_map = {
        "completed": f"Transação #{transaction_id[:8]} concluída",
        "failed": f"Transação #{transaction_id[:8]} falhou",
        "reversed": f"Transação #{transaction_id[:8]} estornada",
    }

    body_map = {
        "completed": f"""
Olá,

Sua transação foi concluída com sucesso!

Detalhes:
- Tipo: {transaction.get_transaction_type_display()}
- Valor: {transaction.amount} {transaction.currency}
- Data: {transaction.completed_at}

Obrigado por usar Bank MVP!
        """,
        "failed": f"""
Olá,

Sua transação não pôde ser procesada.

Motivo: {transaction.failure_reason}

Detalhes:
- Tipo: {transaction.get_transaction_type_display()}
- Valor: {transaction.amount} {transaction.currency}

Por favor, tente novamente ou entre em contato com o suporte.

Obrigado por usar Bank MVP!
        """,
        "reversed": f"""
Olá,

Sua transação foi estornada.

Detalhes:
- Tipo: {transaction.get_transaction_type_display()}
- Valor: {transaction.amount} {transaction.currency}

O estorno será refletido no saldo em até 24 horas.

Obrigado por usar Bank MVP!
        """,
    }

    notification = Notification(
        recipient=email,
        subject=subject_map.get(notification_type, "Notificação Bank MVP"),
        body=body_map.get(notification_type, "Mensagem do Bank MVP"),
        type="email",
        metadata={
            "transaction_id": str(transaction.id),
            "transaction_type": transaction.transaction_type,
            "notification_type": notification_type,
        },
    )

    # Send via configured backends
    for backend_class in settings.NOTIFICATION_BACKENDS:
        backend = EmailBackend()  # In production, instantiate proper backend
        try:
            success = backend.send(notification)
            if success:
                logger.info(f"Notification sent for transaction {transaction_id}")
            else:
                logger.warning(f"Failed to send notification for transaction {transaction_id}")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            raise

    return {"status": "success", "transaction_id": transaction_id, "type": notification_type}


@shared_task(bind=True)
def send_bulk_notifications(self, notifications: list[dict]):
    """Send bulk notifications."""
    from .backends import EmailBackend

    backend = EmailBackend()
    results = []

    for notif_data in notifications:
        notification = Notification(
            recipient=notif_data["recipient"],
            subject=notif_data["subject"],
            body=notif_data["body"],
            type=notif_data.get("type", "email"),
        )
        success = backend.send(notification)
        results.append({
            "recipient": notif_data["recipient"],
            "success": success,
        })

    return {"total": len(notifications), "results": results}