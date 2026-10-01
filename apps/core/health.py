"""Health check endpoints for monitoring."""

from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Health check endpoint for load balancers and orchestration."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Return health status."""
        return Response({
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "service": "bank-mvp",
            "version": "0.1.0",
        })


class ReadinessCheckView(APIView):
    """Readiness check for Kubernetes."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Check if the service is ready to receive traffic."""
        checks = {
            "database": self.check_database(),
            "cache": self.check_cache(),
        }

        all_healthy = all(check["status"] == "healthy" for check in checks.values())

        status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": "ready" if all_healthy else "not_ready",
                "timestamp": timezone.now().isoformat(),
                "checks": checks,
            },
            status=status_code,
        )

    def check_database(self):
        """Check database connectivity."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return {
                "status": "healthy",
                "type": "postgresql",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "type": "postgresql",
                "error": str(e),
            }

    def check_cache(self):
        """Check cache connectivity."""
        try:
            from django.core.cache import cache

            cache.get("health_check")
            return {
                "status": "healthy",
                "type": "redis",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "type": "redis",
                "error": str(e),
            }


class LivenessCheckView(APIView):
    """Liveness check for Kubernetes."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Check if the service is alive."""
        return Response({
            "status": "alive",
            "timestamp": timezone.now().isoformat(),
        })


@api_view(["GET"])
@permission_classes([AllowAny])
def metrics_view(request):
    """
    Prometheus metrics endpoint.

    Requires prometheus_client library.
    """
    try:
        from prometheus_client import Counter, Gauge, Histogram, generate_latest

        # Define custom metrics
        TRANSACTION_COUNT = Counter(
            "bank_transactions_total",
            "Total number of transactions",
            ["transaction_type", "status"],
        )
        ACCOUNT_BALANCE = Gauge(
            "bank_account_balance",
            "Current account balance",
            ["account_id", "account_type"],
        )
        TRANSACTION_DURATION = Histogram(
            "bank_transaction_duration_seconds",
            "Transaction processing duration",
            ["transaction_type"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
        )
        ACTIVE_USERS = Gauge(
            "bank_active_users",
            "Number of active users",
        )

        # Generate metrics output
        metrics_data = generate_latest()

        return Response(
            metrics_data,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )

    except ImportError:
        return Response(
            "# Prometheus client not installed",
            content_type="text/plain",
        )