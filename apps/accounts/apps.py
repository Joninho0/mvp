from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for Accounts app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"
    label = "accounts"