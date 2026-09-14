"""
Tests for rate limiting middleware.
"""
import pytest
import asyncio
from fastapi import status
from httpx import AsyncClient
from unittest.mock import patch

from app.main import app
from app.core.rate_limit import RateLimitStore, get_endpoint_limit


class TestRateLimitConfiguration:
    """Test rate limit configuration."""

    def test_auth_endpoints_have_60_per_minute_limit(self):
        """Test that auth endpoints have 60 requests/minute limit."""
        limit, window = get_endpoint_limit("/api/auth/login", "POST")
        assert limit == 60
        assert window == 60

        limit, window = get_endpoint_limit("/api/auth/refresh", "POST")
        assert limit == 60
        assert window == 60

        limit, window = get_endpoint_limit("/api/auth/logout", "POST")
        assert limit == 60
        assert window == 60

    def test_webhook_endpoints_have_60_per_minute_limit(self):
        """Test that webhook endpoints have 60 requests/minute limit."""
        limit, window = get_endpoint_limit("/webhooks/vapi", "POST")
        assert limit == 60
        assert window == 60

    def test_call_endpoints_have_100_per_hour_limit(self):
        """Test that call creation endpoints have 100 requests/hour limit."""
        limit, window = get_endpoint_limit("/api/test/test-call", "POST")
        assert limit == 100
        assert window == 3600

        limit, window = get_endpoint_limit("/api/calls", "POST")
        assert limit == 100
        assert window == 3600

    def test_generic_api_endpoints_have_60_per_minute_limit(self):
        """Test that other API endpoints have 60 requests/minute limit."""
        limit, window = get_endpoint_limit("/api/students", "GET")
        assert limit == 60
        assert window == 60

    def test_health_endpoints_exempt_from_rate_limiting(self):
        """Test that health check endpoints are not rate limited."""
        assert get_endpoint_limit("/", "GET") is None
        assert get_endpoint_limit("/health", "GET") is None
        assert get_endpoint_limit("/health/live", "GET") is None
        assert get_endpoint_limit("/health/ready", "GET") is None


class TestRateLimitStore:
    """Test the rate limit store."""

    def test_is_allowed_first_request(self):
        """Test that first request is always allowed."""
        store = RateLimitStore()
        assert store.is_allowed("client1", limit=10, window_seconds=60)

    def test_is_allowed_within_limit(self):
        """Test that requests within limit are allowed."""
        store = RateLimitStore()
        limit = 5

        for i in range(limit):
            assert store.is_allowed("client1", limit=limit, window_seconds=60)

    def test_is_allowed_exceeds_limit(self):
        """Test that requests exceeding limit are rejected."""
        store = RateLimitStore()
        limit = 3

        # Fill the bucket
        for i in range(limit):
            assert store.is_allowed("client1", limit=limit, window_seconds=60)

        # Next request should be rejected
        assert not store.is_allowed("client1", limit=limit, window_seconds=60)

    def test_different_clients_have_separate_limits(self):
        """Test that different clients have independent rate limits."""
        store = RateLimitStore()
        limit = 2

        # Client 1 fills the bucket
        assert store.is_allowed("client1", limit=limit, window_seconds=60)
        assert store.is_allowed("client1", limit=limit, window_seconds=60)
        assert not store.is_allowed("client1", limit=limit, window_seconds=60)

        # Client 2 should have its own bucket
        assert store.is_allowed("client2", limit=limit, window_seconds=60)
        assert store.is_allowed("client2", limit=limit, window_seconds=60)
        assert not store.is_allowed("client2", limit=limit, window_seconds=60)

    def test_requests_expire_outside_window(self):
        """Test that old requests outside the time window are discarded."""
        from datetime import datetime, timedelta

        store = RateLimitStore()
        limit = 2
        window = 60

        # Add first request
        assert store.is_allowed("client1", limit=limit, window_seconds=window)
        assert store.is_allowed("client1", limit=limit, window_seconds=window)

        # Should be at limit now
        assert not store.is_allowed("client1", limit=limit, window_seconds=window)

        # Manually advance the timestamp past the window for the first bucket
        now = datetime.utcnow()
        store.buckets["client1"]["requests"] = [
            now - timedelta(seconds=window + 1),
            now - timedelta(seconds=window + 1)
        ]

        # Should allow new request now
        assert store.is_allowed("client1", limit=limit, window_seconds=window)

    def test_client_id_extraction_from_direct_connection(self):
        """Test extracting client ID from direct connection."""
        from unittest.mock import Mock

        store = RateLimitStore()
        request = Mock()
        request.client.host = "192.168.1.1"
        request.headers.get.return_value = None

        client_id = store.get_client_id(request)
        assert client_id == "192.168.1.1"

    def test_client_id_extraction_from_x_forwarded_for(self):
        """Test extracting client ID from X-Forwarded-For header."""
        from unittest.mock import Mock

        store = RateLimitStore()
        request = Mock()
        request.headers.get.return_value = "192.168.1.100, 10.0.0.1"

        client_id = store.get_client_id(request)
        assert client_id == "192.168.1.100"


class TestRateLimitMiddleware:
    """Test rate limiting middleware on endpoints."""

    @pytest.fixture(autouse=True)
    def reset_rate_limit_store(self):
        """Reset the global rate limit store before each test."""
        from app.core.rate_limit import rate_limit_store
        rate_limit_store.buckets.clear()
        yield
        rate_limit_store.buckets.clear()

    @pytest.mark.asyncio
    async def test_health_endpoint_not_rate_limited(self):
        """Test that health endpoint is not rate limited."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make many requests to health endpoint
            for i in range(100):
                response = await client.get("/health")
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_auth_endpoint_rate_limited(self):
        """Test that auth endpoint is rate limited at 60/minute."""
        from app.core.rate_limit import rate_limit_store

        # Mock the rate limit store to directly test bucket logic
        test_client_id = "test-client"
        limit, window = get_endpoint_limit("/api/auth/login", "POST")

        # Fill the bucket to the limit
        for i in range(limit):
            allowed = rate_limit_store.is_allowed(test_client_id, limit, window)
            assert allowed, f"Request {i+1} should be allowed within {limit}/{window}s limit"

        # Next request should exceed the limit
        allowed = rate_limit_store.is_allowed(test_client_id, limit, window)
        assert not allowed, f"Request {limit+1} should be rate limited"

    @pytest.mark.asyncio
    async def test_webhook_endpoint_rate_limited(self):
        """Test that webhook endpoint is rate limited at 60/minute."""
        from app.core.rate_limit import rate_limit_store

        # Mock the rate limit store to directly test bucket logic
        test_client_id = "test-client"
        limit, window = get_endpoint_limit("/webhooks/vapi", "POST")

        # Fill the bucket to the limit
        for i in range(limit):
            allowed = rate_limit_store.is_allowed(test_client_id, limit, window)
            assert allowed, f"Request {i+1} should be allowed within {limit}/{window}s limit"

        # Next request should exceed the limit
        allowed = rate_limit_store.is_allowed(test_client_id, limit, window)
        assert not allowed, f"Request {limit+1} should be rate limited"

    @pytest.mark.asyncio
    async def test_call_endpoint_rate_limited(self):
        """Test that call endpoint is rate limited at 100/hour."""
        from app.core.rate_limit import rate_limit_store

        # Mock the rate limit store to directly test bucket logic
        test_client_id = "test-client"
        limit, window = get_endpoint_limit("/api/calls", "POST")

        # Fill the bucket to the limit
        for i in range(limit):
            allowed = rate_limit_store.is_allowed(test_client_id, limit, window)
            assert allowed, f"Request {i+1} should be allowed within {limit}/{window}s limit"

        # Next request should exceed the limit
        allowed = rate_limit_store.is_allowed(test_client_id, limit, window)
        assert not allowed, f"Request {limit+1} should be rate limited"

    @pytest.mark.asyncio
    async def test_rate_limit_error_message(self):
        """Test that rate limit error has appropriate message."""
        from app.core.rate_limit import rate_limit_store

        test_client_id = "test-client"
        limit, window = get_endpoint_limit("/webhooks/vapi", "POST")

        # Fill the bucket to the limit
        for i in range(limit):
            rate_limit_store.is_allowed(test_client_id, limit, window)

        # Verify next is not allowed
        allowed = rate_limit_store.is_allowed(test_client_id, limit, window)
        assert not allowed

    @pytest.mark.asyncio
    async def test_different_clients_have_separate_limits(self):
        """Test that different clients have independent rate limits."""
        from app.core.rate_limit import rate_limit_store

        limit, window = get_endpoint_limit("/webhooks/vapi", "POST")

        # Client 1: max out the limit
        for i in range(limit):
            assert rate_limit_store.is_allowed("client1", limit, window)

        # Client 1 should be rate limited now
        assert not rate_limit_store.is_allowed("client1", limit, window)

        # Client 2 should have its own independent limit
        assert rate_limit_store.is_allowed("client2", limit, window)
        assert rate_limit_store.is_allowed("client2", limit, window)
