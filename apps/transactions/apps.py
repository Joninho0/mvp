from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    """Configuration for Transactions app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.transactions"
    verbose_name = "Transactions"
    label = "transactions"