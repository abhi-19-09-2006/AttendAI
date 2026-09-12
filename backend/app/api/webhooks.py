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
    Verify Vapi webhook signature.

    Args:
        signature: X-Vapi-Signature header value
        body: Raw request body

    Returns:
        True if signature is valid
    """
    # TODO: Implement actual signature verification using VAPI_WEBHOOK_SECRET
    # For now, just check if webhook secret is configured
    if not settings.VAPI_WEBHOOK_SECRET:
        logger.warning("VAPI_WEBHOOK_SECRET not configured - skipping signature verification")
        return True

    # In production, implement HMAC-SHA256 signature verification:
    # import hmac
    # import hashlib
    # expected = hmac.new(
    #     settings.VAPI_WEBHOOK_SECRET.encode(),
    #     body,
    #     hashlib.sha256
    # ).hexdigest()
    # return hmac.compare_digest(signature, expected)

    return True


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

        # Verify signature
        if x_vapi_signature and not verify_vapi_signature(x_vapi_signature, body):
            logger.error("Invalid webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
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

    except Exception as e:
        logger.error(f"Error processing Vapi webhook: {str(e)}", exc_info=True)
        # Return 200 to prevent Vapi from retrying
        return {"status": "error", "message": str(e)}


@router.get("/vapi/test")
async def test_webhook():
    """Test endpoint to verify webhook is reachable."""
    return {
        "status": "ok",
        "message": "Vapi webhook endpoint is active",
        "webhook_secret_configured": bool(settings.VAPI_WEBHOOK_SECRET)
    }
