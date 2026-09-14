"""
Vapi webhook handler for receiving call status updates.
"""
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import CallStatus
from app.services.vapi_provider import VapiProvider
from app.services.call_service import CallService

logger = get_logger("webhooks")
router = APIRouter()

vapi_provider = VapiProvider()


def verify_vapi_signature(signature: str, body: bytes) -> bool:
    """
    Verify Vapi webhook signature using HMAC-SHA256.

    Args:
        signature: X-Vapi-Signature header value (hex string)
        body: Raw request body (bytes)

    Returns:
        True if signature is valid and matches expected signature

    Reference: Vapi uses HMAC-SHA256 for webhook signatures.
    The signature header format is: hex(HMAC-SHA256(secret, body))
    """
    import hmac
    import hashlib

    # Require signature header to be present
    if not signature:
        logger.warning("Missing X-Vapi-Signature header in webhook")
        return False

    # Require secret to be configured
    if not settings.VAPI_WEBHOOK_SECRET:
        logger.error("VAPI_WEBHOOK_SECRET not configured - cannot verify webhook signature")
        return False

    try:
        # Compute expected signature using HMAC-SHA256
        expected_signature = hmac.new(
            settings.VAPI_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        # Use constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(signature, expected_signature)

        if not is_valid:
            logger.warning(
                f"Invalid webhook signature. Expected: {expected_signature[:16]}..., "
                f"Got: {signature[:16]}..."
            )

        return is_valid

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}", exc_info=True)
        return False


@router.post("/vapi")
async def vapi_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_vapi_signature: str = Header(None, alias="X-Vapi-Signature")
):
    """
    Handle Vapi webhook events.

    Vapi sends webhooks for call status updates:
    - call.started
    - call.ended
    - call.failed
    - transcript.ready

    Each webhook contains:
    - message.type: Event type
    - call: Call data including metadata with our correlation_id
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Verify signature - reject if missing or invalid
        if not verify_vapi_signature(x_vapi_signature, body):
            logger.error("Webhook signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing webhook signature"
            )

        # Parse JSON payload
        payload = await request.json()

        logger.info(f"Received Vapi webhook: {payload.get('message', {}).get('type')}")

        # Parse webhook using provider
        parsed = vapi_provider.parse_webhook_payload(payload)

        correlation_id = parsed.get("correlation_id")
        if not correlation_id:
            logger.warning("Webhook missing correlation_id - cannot process")
            return {"status": "ignored", "reason": "missing_correlation_id"}

        # Get the call by our internal ID
        call_service = CallService(db, vapi_provider)

        event_type = parsed.get("event_type", "")
        provider_call_id = parsed.get("provider_call_id")
        call_status = parsed.get("status")
        transcript = parsed.get("transcript")

        # Handle different event types
        if event_type in ["call.ended", "call.completed", "end-of-call-report"]:
            # Call completed - process results
            await call_service.process_call_completion(
                call_id=correlation_id,
                vapi_call_id=provider_call_id,
                status=call_status or "completed",
                transcript=transcript
            )

        elif event_type == "call.failed":
            # Call failed
            await call_service.process_call_completion(
                call_id=correlation_id,
                vapi_call_id=provider_call_id,
                status="failed",
                transcript=None
            )

        elif event_type in ["call.started", "status-update"]:
            # Update call status
            call = await db.get(call_service.db.bind, correlation_id)
            if call:
                if call_status == "in-progress":
                    call.status = CallStatus.ANSWERED
                    call.answered_at = datetime.utcnow()
                await db.commit()

        return {"status": "processed", "correlation_id": correlation_id}

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 401 from signature verification)
        raise
    except Exception as e:
        logger.error(f"Error processing Vapi webhook: {str(e)}", exc_info=True)
        # Return 200 to prevent Vapi from retrying on application errors
        return {"status": "error", "message": str(e)}


@router.get("/vapi/test")
async def test_webhook():
    """Test endpoint to verify webhook is reachable."""
    return {
        "status": "ok",
        "message": "Vapi webhook endpoint is active",
        "webhook_secret_configured": bool(settings.VAPI_WEBHOOK_SECRET)
    }
