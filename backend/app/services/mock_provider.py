"""
Mock voice provider for testing without making real calls.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from app.services.voice_provider import (
    VoiceProvider,
    CallContext,
    CallResult,
    CallStatusResult
)
from app.core.logging import get_logger

logger = get_logger("mock_provider")


class MockVoiceProvider(VoiceProvider):
    """
    Mock voice provider for testing.

    Simulates call behavior without making actual API calls.
    Useful for unit tests and local development.
    """

    def __init__(self):
        self.calls: Dict[str, Dict[str, Any]] = {}

    async def create_call(self, context: CallContext) -> CallResult:
        """Create a mock call."""

        mock_call_id = f"mock_{uuid.uuid4().hex[:12]}"

        self.calls[mock_call_id] = {
            "context": context.dict(),
            "status": "calling",
            "initiated_at": datetime.utcnow(),
            "ended_at": None,
            "transcript": None
        }

        logger.info(
            f"Mock call created: {mock_call_id} for {context.student_name} "
            f"(correlation_id: {context.correlation_id})"
        )

        return CallResult(
            provider_call_id=mock_call_id,
            status="calling",
            initiated_at=datetime.utcnow(),
            metadata={"mock": True}
        )

    async def get_call_status(self, provider_call_id: str) -> CallStatusResult:
        """Get mock call status."""

        call_data = self.calls.get(provider_call_id)
        if not call_data:
            raise ValueError(f"Mock call {provider_call_id} not found")

        return CallStatusResult(
            provider_call_id=provider_call_id,
            status=call_data["status"],
            duration_seconds=call_data.get("duration_seconds"),
            ended_at=call_data.get("ended_at"),
            transcript=call_data.get("transcript"),
            metadata=call_data
        )

    async def cancel_call(self, provider_call_id: str) -> bool:
        """Cancel a mock call."""

        if provider_call_id in self.calls:
            self.calls[provider_call_id]["status"] = "cancelled"
            self.calls[provider_call_id]["ended_at"] = datetime.utcnow()
            logger.info(f"Mock call cancelled: {provider_call_id}")
            return True

        return False

    def parse_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse mock webhook payload."""

        return {
            "correlation_id": payload.get("correlation_id"),
            "provider_call_id": payload.get("call_id"),
            "status": payload.get("status"),
            "event_type": payload.get("event_type"),
            "transcript": payload.get("transcript"),
            "duration": payload.get("duration"),
            "ended_at": payload.get("ended_at"),
            "metadata": payload
        }

    # Helper methods for testing

    def simulate_answer(self, provider_call_id: str, transcript: str):
        """Simulate a call being answered with a transcript."""

        if provider_call_id in self.calls:
            self.calls[provider_call_id]["status"] = "completed"
            self.calls[provider_call_id]["ended_at"] = datetime.utcnow()
            self.calls[provider_call_id]["transcript"] = transcript

            duration = (
                self.calls[provider_call_id]["ended_at"] -
                self.calls[provider_call_id]["initiated_at"]
            ).total_seconds()
            self.calls[provider_call_id]["duration_seconds"] = int(duration)

            logger.info(f"Mock call answered: {provider_call_id}")

    def simulate_no_answer(self, provider_call_id: str):
        """Simulate a call with no answer."""

        if provider_call_id in self.calls:
            self.calls[provider_call_id]["status"] = "no-answer"
            self.calls[provider_call_id]["ended_at"] = datetime.utcnow()

            logger.info(f"Mock call no answer: {provider_call_id}")

    def simulate_failed(self, provider_call_id: str, error: str):
        """Simulate a failed call."""

        if provider_call_id in self.calls:
            self.calls[provider_call_id]["status"] = "failed"
            self.calls[provider_call_id]["ended_at"] = datetime.utcnow()
            self.calls[provider_call_id]["error"] = error

            logger.info(f"Mock call failed: {provider_call_id} - {error}")
