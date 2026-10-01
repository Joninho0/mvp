"""Notification backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Notification:
    """Notification message."""

    recipient: str
    subject: str
    body: str
    type: str = "email"
    metadata: dict | None = None


class NotificationBackend(ABC):
    """Base class for notification backends."""

    @abstractmethod
    def send(self, notification: Notification) -> bool:
        """Send a notification."""
        pass


class EmailBackend(NotificationBackend):
    """Email notification backend."""

    def send(self, notification: Notification) -> bool:
        """Send email notification."""
        # In production, this would use Django's email backend
        print(f"[EMAIL] To: {notification.recipient}")
        print(f"[EMAIL] Subject: {notification.subject}")
        print(f"[EMAIL] Body: {notification.body}")
        return True


class LogBackend(NotificationBackend):
    """Log notification backend."""

    def send(self, notification: Notification) -> bool:
        """Log notification."""
        print(f"[LOG] {notification.type.upper()}: {notification.subject}")
        return True


class SMSBackend(NotificationBackend):
    """SMS notification backend (mock)."""

    def send(self, notification: Notification) -> bool:
        """Send SMS notification (mock implementation)."""
        print(f"[SMS] To: {notification.recipient}")
        print(f"[SMS] Body: {notification.body[:160]}")
        return True


class WebhookBackend(NotificationBackend):
    """Webhook notification backend."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, notification: Notification) -> bool:
        """Send webhook notification."""
        import requests

        try:
            response = requests.post(
                self.webhook_url,
                json={
                    "subject": notification.subject,
                    "body": notification.body,
                    "metadata": notification.metadata,
                },
                timeout=10,
            )
            return response.status_code < 400
        except Exception as e:
            print(f"[WEBHOOK] Error: {e}")
            return False