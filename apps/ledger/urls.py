"""URL patterns for ledger app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()
router.register(r"", viewsets.LedgerEntryViewSet, basename="ledger-entry")

urlpatterns = [
    path("", include(router.urls)),
]