"""
Vapi webhook handler for receiving call status updates.

Includes:
- HMAC signature verification
- Idempotency protection against duplicate webhooks
- PII redaction in logs
- Graceful error handling
"""
from typing import Dict, Any
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, status, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.models import Call
from app.models.enums import CallStatus
from app.services.vapi_provider import VapiProvider
from app.services.call_service import CallService
from app.utils.pii_redaction import redact_signature, redact_phone

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
    
    Security:
    - HMAC signature verification required
    - Idempotency protection against duplicate webhooks
    - PII redaction in logs
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Verify signature - reject if missing or invalid
        if not verify_vapi_signature(x_vapi_signature, body):
            logger.error(
                "Webhook signature verification failed",
                extra={"signature": redact_signature(x_vapi_signature)}
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing webhook signature"
            )

        # Parse JSON payload
        try:
            payload = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse webhook JSON: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )

        # Extract event type
        event_type = payload.get("message", {}).get("type", "unknown")
        logger.info("Received Vapi webhook", extra={"event_type": event_type})

        # Parse webhook using provider
        parsed = vapi_provider.parse_webhook_payload(payload)

        correlation_id = parsed.get("correlation_id")
        if not correlation_id:
            logger.warning("Webhook missing correlation_id - cannot process")
            return {"status": "ignored", "reason": "missing_correlation_id"}

        # Idempotency check: verify call exists and check current state
        result = await db.execute(
            select(Call).where(Call.id == correlation_id)
        )
        call = result.scalar_one_or_none()
        
        if not call:
            logger.warning(
                "Webhook for unknown call",
                extra={"correlation_id": correlation_id, "event_type": event_type}
            )
            return {"status": "ignored", "reason": "unknown_call"}

        # Check if call is already in terminal state (idempotency protection)
        terminal_states = [
            CallStatus.COMPLETED,
            CallStatus.FAILED,
            CallStatus.UNREACHABLE,
            CallStatus.CANCELLED
        ]
        
        if call.status in terminal_states and event_type not in ["call.started", "status-update"]:
            logger.info(
                "Webhook for already-completed call (idempotency)",
                extra={
                    "correlation_id": correlation_id,
                    "current_status": call.status.value,
                    "event_type": event_type
                }
            )
            return {
                "status": "ignored",
                "reason": "already_processed",
                "call_id": correlation_id
            }

        # Get the call service
        call_service = CallService(db, vapi_provider)

        provider_call_id = parsed.get("provider_call_id")
        call_status = parsed.get("status")
        transcript = parsed.get("transcript")

        # Handle different event types
        if event_type in ["call.ended", "call.completed", "end-of-call-report"]:
            # Call completed - process results
            logger.info(
                "Processing call completion",
                extra={
                    "correlation_id": correlation_id,
                    "status": call_status,
                    "has_transcript": transcript is not None
                }
            )
            await call_service.process_call_completion(
                call_id=correlation_id,
                vapi_call_id=provider_call_id,
                status=call_status or "completed",
                transcript=transcript
            )

        elif event_type == "call.failed":
            # Call failed
            logger.warning(
                "Processing call failure",
                extra={"correlation_id": correlation_id}
            )
            await call_service.process_call_completion(
                call_id=correlation_id,
                vapi_call_id=provider_call_id,
                status="failed",
                transcript=None
            )

        elif event_type in ["call.started", "status-update"]:
            # Update call status (not terminal, so no idempotency check needed)
            if call:
                if call_status == "in-progress":
                    call.status = CallStatus.ANSWERED
                    call.answered_at = datetime.utcnow()
                    await db.commit()
                    logger.info(
                        "Call answered",
                        extra={"correlation_id": correlation_id}
                    )

        else:
            # Unknown event type - log but don't fail
            logger.warning(
                "Unknown webhook event type",
                extra={"event_type": event_type, "correlation_id": correlation_id}
            )
            return {
                "status": "ignored",
                "reason": "unknown_event_type",
                "event_type": event_type
            }

        logger.info(
            "Webhook processed successfully",
            extra={"correlation_id": correlation_id, "event_type": event_type}
        )
        return {"status": "processed", "correlation_id": correlation_id}

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 401 from signature verification)
        raise
    except Exception as e:
        logger.error(
            f"Error processing Vapi webhook: {str(e)}",
            exc_info=True,
            extra={"error_type": type(e).__name__}
        )
        # Return 200 to prevent Vapi from retrying on application errors
        # This is important: we don't want Vapi to retry if our code has a bug
        return {"status": "error", "message": str(e)}


@router.get("/vapi/test")
async def test_webhook():
    """Test endpoint to verify webhook is reachable."""
    return {
        "status": "ok",
        "message": "Vapi webhook endpoint is active",
        "webhook_secret_configured": bool(settings.VAPI_WEBHOOK_SECRET)
    }
