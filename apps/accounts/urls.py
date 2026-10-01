"""URL patterns for accounts app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import viewsets

router = DefaultRouter()
router.register(r"", viewsets.AccountViewSet, basename="account")

urlpatterns = [
    path("", include(router.urls)),
]