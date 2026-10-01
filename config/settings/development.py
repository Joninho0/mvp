"""Development settings for bank project."""

from .base import *

# Override base settings for development
DEBUG = True
DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: True}

# Allow all hosts in development
ALLOWED_HOSTS = ["*"]

# Database for development
DATABASES["default"].update({
    "HOST": env("DB_HOST", default="localhost"),
    "PORT": env("DB_PORT", default="5432"),
})

# Simpler password validation for development
AUTH_PASSWORD_VALIDATORS = []

# Disable security middleware for development
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_structlog.middleware.RequestMiddleware",
    "django_axes.middleware.AxesMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_ratelimit.middleware.RatelimitMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# Logging - more verbose in development
LOGGING["loggers"]["bank"]["level"] = "DEBUG"

# Disable rate limiting in development
RATELIMIT_ENABLE = False

# Fraud check disabled in development
FRAUD_CHECK_ENABLED = False

# JWT settings for development (use symmetric for simplicity)
SIMPLE_JWT.update({
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
})

# Simplified Celery configuration
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ALWAYS_EAGER = True

# Add debug toolbar to installed apps
INSTALLED_APPS += ["debug_toolbar"]

# Include debug toolbar URLs
ROOT_URLCONF = "config.urls_with_debug"