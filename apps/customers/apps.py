from django.apps import AppConfig


class CustomersConfig(AppConfig):
    """Configuration for Customers app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.customers"
    verbose_name = "Customers"
    label = "customers"