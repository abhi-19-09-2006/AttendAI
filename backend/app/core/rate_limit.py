"""
Rate limiting middleware for protecting endpoints against abuse.

Implements token bucket rate limiting with different limits for different endpoints:
- Auth endpoints (login, refresh): 60 requests/minute
- Webhook endpoints: 60 requests/minute
- Call creation endpoints: 100 requests/hour
- Health endpoints: No rate limiting
"""
from typing import Dict, Tuple
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import get_logger

logger = get_logger("rate_limit")


class RateLimitStore:
    """In-memory rate limit store with per-client buckets."""

    def __init__(self):
        self.buckets: Dict[str, Dict] = {}

    def get_client_id(self, request: Request) -> str:
        """Extract unique client identifier from request."""
        # Try to get from X-Forwarded-For header (proxied requests)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"

    def is_allowed(self, client_id: str, limit: int, window_seconds: int) -> bool:
        """Check if request is within rate limit.

        Args:
            client_id: Unique identifier for the client
            limit: Maximum requests allowed in the time window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = datetime.utcnow()

        if client_id not in self.buckets:
            self.buckets[client_id] = {
                "requests": [],
                "last_cleanup": now,
            }

        bucket = self.buckets[client_id]

        # Clean up old requests outside the window
        cutoff = now - timedelta(seconds=window_seconds)
        bucket["requests"] = [
            ts for ts in bucket["requests"] if ts > cutoff
        ]

        # Periodic cleanup of old buckets (every 100 requests across all clients)
        total_requests = sum(len(b["requests"]) for b in self.buckets.values())
        if total_requests % 100 == 0:
            old_cutoff = now - timedelta(hours=1)
            expired_clients = [
                cid for cid, b in self.buckets.items()
                if b["last_cleanup"] < old_cutoff
            ]
            for cid in expired_clients:
                del self.buckets[cid]

        # Check if within limit
        if len(bucket["requests"]) >= limit:
            return False

        # Add current request
        bucket["requests"].append(now)
        bucket["last_cleanup"] = now
        return True


# Global rate limit store
rate_limit_store = RateLimitStore()


def get_endpoint_limit(path: str, method: str) -> Tuple[int, int] | None:
    """Get rate limit for an endpoint.

    Args:
        path: Request path
        method: HTTP method

    Returns:
        Tuple of (limit, window_seconds) or None if no limit
    """
    # Exempt health checks
    if path in ["/", "/health", "/health/live", "/health/ready"]:
        return None

    # Auth endpoints: 60 requests/minute
    if path in ["/api/auth/login", "/api/auth/refresh", "/api/auth/logout"]:
        return (60, 60)

    # Webhook endpoints: 60 requests/minute
    if path.startswith("/webhooks/"):
        return (60, 60)

    # Call creation endpoints: 100 requests/hour
    if path in [
        "/api/test/test-call",
        "/api/calls",
        "/api/calls/create",
    ]:
        return (100, 3600)

    # API endpoints: default 60 requests/minute
    if path.startswith("/api/"):
        return (60, 60)

    # No limit by default
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on endpoints."""

    async def dispatch(self, request: Request, call_next):
        """Process request and check rate limit."""
        # Check if this endpoint has a rate limit
        limit_config = get_endpoint_limit(request.url.path, request.method)

        if limit_config:
            limit, window = limit_config
            client_id = rate_limit_store.get_client_id(request)

            if not rate_limit_store.is_allowed(client_id, limit, window):
                logger.warning(
                    f"Rate limit exceeded for {client_id} on {request.method} {request.url.path}"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Too many requests."
                )

        response = await call_next(request)
        return response
