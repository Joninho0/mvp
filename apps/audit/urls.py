"""URL patterns for audit app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()
router.register(r"", viewsets.AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("", include(router.urls)),
]