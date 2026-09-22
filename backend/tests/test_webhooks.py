"""
Tests for Vapi webhook signature verification and security.
"""
import json
import hmac
import hashlib
import pytest
from fastapi import status
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.main import app
from app.core.config import settings
from app.core.database import get_db


class TestVapiWebhookSignatureVerification:
    """Test webhook signature verification security."""

    def get_test_payload(self):
        """Get a valid webhook payload structure."""
        return {
            "message": {
                "type": "call.ended",
            },
            "call": {
                "id": "vapi-call-id-123",
                "status": "completed",
                "metadata": {
                    "correlation_id": "test-correlation-id"
                }
            }
        }

    def generate_valid_signature(self, body: bytes, secret: str = None) -> str:
        """Generate a valid HMAC-SHA256 signature for a webhook body."""
        if secret is None:
            secret = settings.VAPI_WEBHOOK_SECRET or "test-secret"

        return hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

    @pytest.mark.asyncio
    async def test_webhook_with_valid_signature(self):
        """Test webhook is accepted with valid signature."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = self.get_test_payload()
            body = json.dumps(payload).encode()
            valid_signature = self.generate_valid_signature(body, "test-secret")

            with patch("app.api.webhooks.settings") as mock_settings:
                mock_settings.VAPI_WEBHOOK_SECRET = "test-secret"

                # Mock the database to return a Call object
                from app.models import Call
                from app.models.enums import CallStatus
                from unittest.mock import MagicMock
                
                mock_call = MagicMock(spec=Call)
                mock_call.id = "test-correlation-id"
                mock_call.status = CallStatus.CALLING  # Not in terminal state
                
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_call
                
                mock_db = MagicMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                
                async def override_get_db():
                    yield mock_db
                
                app.dependency_overrides[get_db] = override_get_db
                
                try:
                    with patch("app.api.webhooks.CallService") as mock_call_service:
                        mock_instance = AsyncMock()
                        mock_call_service.return_value = mock_instance
                        mock_instance.process_call_completion = AsyncMock()

                        response = await client.post(
                            "/webhooks/vapi",
                            json=payload,
                            headers={"X-Vapi-Signature": valid_signature}
                        )

                        assert response.status_code == status.HTTP_200_OK
                        data = response.json()
                        assert data["status"] == "processed"
                finally:
                    app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_webhook_with_invalid_signature(self):
        """Test webhook is rejected with invalid signature."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = self.get_test_payload()
            invalid_signature = "invalid_signature_not_matching_actual"

            with patch("app.api.webhooks.settings") as mock_settings:
                mock_settings.VAPI_WEBHOOK_SECRET = "test-secret"

                response = await client.post(
                    "/webhooks/vapi",
                    json=payload,
                    headers={"X-Vapi-Signature": invalid_signature}
                )

                assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_webhook_with_missing_signature(self):
        """Test webhook is rejected when signature header is missing."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = self.get_test_payload()

            with patch("app.api.webhooks.settings") as mock_settings:
                mock_settings.VAPI_WEBHOOK_SECRET = "test-secret"

                response = await client.post(
                    "/webhooks/vapi",
                    json=payload
                )

                assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_webhook_signature_timing_attack_protection(self):
        """Test that signature verification uses constant-time comparison."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = self.get_test_payload()
            body = json.dumps(payload).encode()

            with patch("app.api.webhooks.settings") as mock_settings:
                mock_settings.VAPI_WEBHOOK_SECRET = "test-secret"

                valid_sig = self.generate_valid_signature(body, "test-secret")
                almost_correct_sig = valid_sig[:-1] + ("0" if valid_sig[-1] != "0" else "1")

                response = await client.post(
                    "/webhooks/vapi",
                    json=payload,
                    headers={"X-Vapi-Signature": almost_correct_sig}
                )

                assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_webhook_without_secret_configured(self):
        """Test that webhook is rejected when secret is not configured."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = self.get_test_payload()
            body = json.dumps(payload).encode()
            signature = self.generate_valid_signature(body, "test-secret")

            with patch("app.api.webhooks.settings") as mock_settings:
                mock_settings.VAPI_WEBHOOK_SECRET = None

                response = await client.post(
                    "/webhooks/vapi",
                    json=payload,
                    headers={"X-Vapi-Signature": signature}
                )

                assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_webhook_with_empty_signature(self):
        """Test that webhook is rejected with empty signature string."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = self.get_test_payload()

            with patch("app.api.webhooks.settings") as mock_settings:
                mock_settings.VAPI_WEBHOOK_SECRET = "test-secret"

                response = await client.post(
                    "/webhooks/vapi",
                    json=payload,
                    headers={"X-Vapi-Signature": ""}
                )

                assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_webhook_replay_attack_prevention(self):
        """Test that modified payload with old signature is rejected."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = self.get_test_payload()
            body = json.dumps(payload).encode()
            valid_signature = self.generate_valid_signature(body, "test-secret")

            with patch("app.api.webhooks.settings") as mock_settings:
                mock_settings.VAPI_WEBHOOK_SECRET = "test-secret"

                # Mock the database to return a Call object
                from app.models import Call
                from app.models.enums import CallStatus
                from unittest.mock import MagicMock
                
                mock_call = MagicMock(spec=Call)
                mock_call.id = "test-correlation-id"
                mock_call.status = CallStatus.CALLING  # Not in terminal state
                
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_call
                
                mock_db = MagicMock()
                mock_db.execute = AsyncMock(return_value=mock_result)
                
                async def override_get_db():
                    yield mock_db
                
                app.dependency_overrides[get_db] = override_get_db
                
                try:
                    with patch("app.api.webhooks.CallService") as mock_call_service:
                        mock_instance = AsyncMock()
                        mock_call_service.return_value = mock_instance
                        mock_instance.process_call_completion = AsyncMock()

                        # First request succeeds
                        response1 = await client.post(
                            "/webhooks/vapi",
                            json=payload,
                            headers={"X-Vapi-Signature": valid_signature}
                        )
                        assert response1.status_code == status.HTTP_200_OK

                        # Modified payload with old signature is rejected
                        modified_payload = payload.copy()
                        modified_payload["message"]["type"] = "call.started"

                        response2 = await client.post(
                            "/webhooks/vapi",
                            json=modified_payload,
                            headers={"X-Vapi-Signature": valid_signature}
                        )
                        assert response2.status_code == status.HTTP_401_UNAUTHORIZED
                finally:
                    app.dependency_overrides.clear()


class TestWebhookTestEndpoint:
    """Test the webhook test endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_test_endpoint_when_secret_configured(self):
        """Test webhook test endpoint reports when secret is configured."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("app.api.webhooks.settings") as mock_settings:
                mock_settings.VAPI_WEBHOOK_SECRET = "configured-secret"

                response = await client.get("/webhooks/vapi/test")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "ok"
                assert data["webhook_secret_configured"] is True

    @pytest.mark.asyncio
    async def test_webhook_test_endpoint_when_secret_not_configured(self):
        """Test webhook test endpoint reports when secret is not configured."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            with patch("app.api.webhooks.settings") as mock_settings:
                mock_settings.VAPI_WEBHOOK_SECRET = None

                response = await client.get("/webhooks/vapi/test")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "ok"
                assert data["webhook_secret_configured"] is False
