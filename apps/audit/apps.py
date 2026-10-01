from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configuration for Audit app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit"
    label = "audit"