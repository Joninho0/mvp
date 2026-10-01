"""Production settings for bank project."""

import os

from .base import *

# Ensure DEBUG is False
DEBUG = False

# Security settings
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Database connection pooling
DATABASES["default"]["CONN_MAX_AGE"] = 60

# Password hashing with Argon2
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# Gunicorn workers
WSGI_APPLICATION = "config.wsgi.application"

# Logging - JSON format for production
LOGGING["formatters"]["verbose"]["()"] = "django_structlog.formatters.JSONFormatter"

# Add Sentry for error tracking
SENTRY_DSN = env("SENTRY_DSN", default=None)
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment="production",
    )

# Prometheus metrics
PROMETHEUS_EXPORT_MIGRATIONS = False

# Axes configuration - stricter in production
AXES_FAILURE_LIMIT = 3
AXES_COOLOFF_TIME = 24 * 60 * 60  # 24 hours

# Rate limiting - more restrictive in production
RATELIMIT_WINDOW = 60  # seconds