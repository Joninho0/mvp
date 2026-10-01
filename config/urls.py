"""
URL configuration for bank project.
"""

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import dashboard
from apps.core.health import HealthCheckView, LivenessCheckView, ReadinessCheckView, metrics_view

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Auth
    path("auth/", include("apps.customers.urls")),
    path("auth/", include("django.contrib.auth.urls")),

    # Dashboard
    path("", dashboard, name="dashboard"),

    # Apps
    path("accounts/", include("apps.accounts.urls")),
    path("transactions/", include("apps.transactions.urls")),
    path("api/ledger/", include("apps.ledger.urls")),
    path("api/audit/", include("apps.audit.urls")),

    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Health checks
    path("health/", HealthCheckView.as_view(), name="health"),
    path("health/ready/", ReadinessCheckView.as_view(), name="readiness"),
    path("health/live/", LivenessCheckView.as_view(), name="liveness"),
    path("metrics/", metrics_view, name="metrics"),
]