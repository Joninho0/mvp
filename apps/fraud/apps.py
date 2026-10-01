from django.apps import AppConfig


class FraudConfig(AppConfig):
    """Configuration for Fraud detection app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.fraud"
    verbose_name = "Fraud Detection"
    label = "fraud"