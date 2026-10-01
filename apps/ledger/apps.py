from django.apps import AppConfig


class LedgerConfig(AppConfig):
    """Configuration for Ledger app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ledger"
    verbose_name = "Ledger"
    label = "ledger"