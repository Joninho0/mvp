"""Custom middleware for the bank API."""

import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(MiddlewareMixin):
    """Middleware to add correlation ID to all requests."""

    def process_request(self, request):
        """Add or generate correlation ID."""
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        request.correlation_id = correlation_id

        # Add to response headers
        request.correlation_id_header = correlation_id

    def process_response(self, request, response):
        """Add correlation ID to response headers."""
        correlation_id = getattr(request, "correlation_id", None)
        if correlation_id:
            response["X-Correlation-ID"] = correlation_id
        return response


class RequestTimingMiddleware(MiddlewareMixin):
    """Middleware to log request timing."""

    def process_request(self, request):
        """Record request start time."""
        request.start_time = time.time()

    def process_response(self, request, response):
        """Log request duration."""
        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time
            logger.info(
                f"{request.method} {request.path} - {response.status_code} - {duration:.3f}s",
                extra={
                    "correlation_id": getattr(request, "correlation_id", None),
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration": duration,
                },
            )
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Middleware to add security headers."""

    def process_response(self, request, response):
        """Add security headers."""
        # Prevent clickjacking
        response["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response["X-Content-Type-Options"] = "nosniff"

        # XSS protection
        response["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (customize for your needs)
        response["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"

        return response


class SessionTimeoutMiddleware(MiddlewareMixin):
    """Middleware to enforce session timeout."""

    def process_request(self, request):
        """Check if session has expired."""
        if request.user.is_authenticated:
            last_activity = request.session.get("last_activity")
            timeout = 15 * 60  # 15 minutes in seconds

            if last_activity:
                elapsed = time.time() - last_activity
                if elapsed > timeout:
                    # Session expired - logout user
                    from django.contrib.auth import logout

                    logout(request)
                    request.session.flush()

            # Update last activity
            request.session["last_activity"] = time.time()