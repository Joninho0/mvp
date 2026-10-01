"""Test settings for bank project."""

from .base import *

# Override base settings for testing
DEBUG = True
TEMPLATES[0]["OPTIONS"]["loaders"] = None
TEMPLATES[0]["APP_DIRS"] = True

# Use in-memory SQLite for faster tests
DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

# Simpler password validation for testing
AUTH_PASSWORD_VALIDATORS = []

# Disable migrations for testing
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable rate limiting for tests
RATELIMIT_ENABLE = False

# Disable fraud check for tests
FRAUD_CHECK_ENABLED = False

# Disable axes for tests
AXES_ENABLED = False

# Use synchronous execution for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}

# Simpler JWT for tests
SIMPLE_JWT.update({
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "ACCESS_TOKEN_LIFETIME": "1 hour",
    "REFRESH_TOKEN_LIFETIME": "1 day",
})

# Disable Prometheus
INSTALLED_APPS = [
    app for app in INSTALLED_APPS if "prometheus" not in app
]

# Disable Celery Beatroot = ""