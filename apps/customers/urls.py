"""URL patterns for customers app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views, viewsets

router = DefaultRouter()
router.register(r"", viewsets.CustomerViewSet, basename="customer")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/login/", views.login_view, name="login"),
    path("auth/register/", views.register_view, name="register"),
    path("auth/logout/", views.logout_view, name="logout"),
]