"""
Vapi.ai voice provider implementation.
"""
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.services.voice_provider import (
    VoiceProvider,
    CallContext,
    CallResult,
    CallStatusResult
)

logger = get_logger("vapi_provider")


class VapiProvider(VoiceProvider):
    """Vapi.ai implementation of voice calling provider."""

    def __init__(self):
        self.api_key = settings.VAPI_API_KEY
        self.base_url = settings.VAPI_BASE_URL
        self.phone_number_id = settings.VAPI_PHONE_NUMBER_ID
        self.assistant_id = settings.VAPI_ASSISTANT_ID if hasattr(settings, 'VAPI_ASSISTANT_ID') else None

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_call(self, context: CallContext) -> CallResult:
        """
        Initiate a call via Vapi.

        Uses a reusable assistant configuration and passes student-specific
        data via assistant overrides and metadata for correlation.
        """

        # Build assistant configuration with dynamic student context
        assistant_config = self._build_assistant_config(context)

        payload = {
            "phoneNumberId": self.phone_number_id,
            "customer": {
                "number": context.phone_number
            },
            "assistant": assistant_config,
            # Store correlation ID in metadata for webhook identification
            "metadata": {
                "correlation_id": context.correlation_id,
                "student_name": context.student_name,
                "absence_date": context.absence_date
            }
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/call",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

                logger.info(
                    f"Vapi call initiated: {data.get('id')} for {context.student_name} "
                    f"(correlation_id: {context.correlation_id})"
                )

                return CallResult(
                    provider_call_id=data.get("id"),
                    status=data.get("status", "queued"),
                    initiated_at=datetime.utcnow(),
                    metadata=data
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"Vapi API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Vapi call: {str(e)}")
            raise

    async def get_call_status(self, provider_call_id: str) -> CallStatusResult:
        """Get call status from Vapi."""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/call/{provider_call_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                data = response.json()

                # Extract transcript if available
                transcript = self._extract_transcript(data)

                return CallStatusResult(
                    provider_call_id=provider_call_id,
                    status=data.get("status", "unknown"),
                    duration_seconds=data.get("duration"),
                    ended_at=self._parse_datetime(data.get("endedAt")),
                    transcript=transcript,
                    metadata=data
                )

        except Exception as e:
            logger.error(f"Failed to get call status: {str(e)}")
            raise

    async def cancel_call(self, provider_call_id: str) -> bool:
        """Cancel an ongoing call."""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.base_url}/call/{provider_call_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                logger.info(f"Cancelled Vapi call: {provider_call_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to cancel call: {str(e)}")
            return False

    def parse_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Vapi webhook payload to standard format.

        Based on Vapi webhook documentation, expected fields:
        - call.id: Vapi call ID
        - call.status: Call status
        - call.metadata: Our correlation data
        - message.type: Event type (status-update, transcript, etc.)
        - transcript: Full conversation transcript (if available)
        """

        call_data = payload.get("call", {})
        message = payload.get("message", {})

        # Extract correlation ID from metadata
        metadata = call_data.get("metadata", {})
        correlation_id = metadata.get("correlation_id")

        # Extract transcript
        transcript = call_data.get("transcript") or payload.get("transcript")

        # Parse messages array into formatted transcript
        if not transcript and call_data.get("messages"):
            transcript = self._format_messages(call_data.get("messages"))

        return {
            "correlation_id": correlation_id,
            "provider_call_id": call_data.get("id"),
            "status": call_data.get("status"),
            "event_type": message.get("type"),
            "transcript": transcript,
            "duration": call_data.get("duration"),
            "ended_at": call_data.get("endedAt"),
            "metadata": payload
        }

    def _build_assistant_config(self, context: CallContext) -> Dict[str, Any]:
        """
        Build assistant configuration with student-specific context.

        Uses a reusable assistant structure with dynamic first message
        and system prompt that includes student information.
        """

        # If using a pre-created assistant, reference it and override message
        if self.assistant_id:
            return {
                "assistantId": self.assistant_id,
                "assistantOverrides": {
                    "firstMessage": self._get_first_message(context),
                    "variableValues": {
                        "studentName": context.student_name,
                        "absenceDate": context.absence_date
                    }
                }
            }

        # Otherwise, create inline assistant configuration
        return {
            "model": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "maxTokens": 500
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "rachel"  # Professional female voice
            },
            "firstMessage": self._get_first_message(context),
            "systemPrompt": self._get_system_prompt(context),
            "endCallFunctionEnabled": True,
            "recordingEnabled": True,
            "maxDurationSeconds": settings.MAX_CALL_DURATION_SECONDS,
            "silenceTimeoutSeconds": 30,
            "responseDelaySeconds": 1
        }

    def _get_first_message(self, context: CallContext) -> str:
        """Generate the opening message for the call."""
        return (
            f"Hello, this is the attendance assistant calling from the college regarding "
            f"{context.student_name}'s absence on {context.absence_date}. "
            f"May I please speak with a parent or guardian?"
        )

    def _get_system_prompt(self, context: CallContext) -> str:
        """
        Generate system prompt for the AI assistant.

        This creates a safe, professional prompt for college attendance calls.
        """
        return f"""You are a professional college attendance assistant calling about {context.student_name}'s absence on {context.absence_date}.

Your role and guidelines:
1. IDENTIFY: You are calling from the college attendance office
2. VERIFY: Confirm you are speaking with a parent or guardian of {context.student_name}
3. INFORM: Explain that {context.student_name} was marked absent on {context.absence_date}
4. INQUIRE: Ask for the reason for the absence
5. CLARIFY: If medical or extended absence, ask about expected return date
6. CONFIRM: Repeat back the information to ensure accuracy
7. CLOSE: Thank them and end the call politely

Important guidelines:
- Be warm, professional, and respectful
- Keep the call brief (under 3 minutes)
- Do NOT provide medical advice or diagnose conditions
- Do NOT ask for sensitive medical details beyond general reason (e.g., "not feeling well" is sufficient)
- Do NOT request personal information beyond what's needed for attendance
- If parent is busy or upset, offer to call back at a better time
- If voicemail, leave a brief message with callback number
- If wrong number or cannot reach guardian, note it and end the call

Information to collect:
- Confirmation that parent was aware of the absence
- General reason (sick, family matter, personal, appointment, other)
- Expected duration (returning tomorrow, few days, this week, unknown)
- Whether follow-up is needed (callback requested, documentation needed)

Example conversation flow:
1. "Hello, this is the attendance assistant from the college..."
2. "Am I speaking with a parent or guardian of {context.student_name}?"
3. "We're calling because {context.student_name} was absent on {context.absence_date}. Were you aware of this absence?"
4. "Can you tell me the reason for the absence?"
5. "When do you expect {context.student_name} to return to classes?"
6. "Just to confirm, [repeat back the information]. Is that correct?"
7. "Thank you for the information. We hope {context.student_name} feels better soon. Have a good day."

End the call naturally when you have the needed information or if the parent requests it."""

    def _extract_transcript(self, call_data: Dict[str, Any]) -> Optional[str]:
        """Extract and format transcript from call data."""

        # Check for direct transcript field
        if call_data.get("transcript"):
            return call_data["transcript"]

        # Format from messages array
        messages = call_data.get("messages", [])
        if messages:
            return self._format_messages(messages)

        return None

    def _format_messages(self, messages: list) -> str:
        """Format message array into readable transcript."""

        transcript_lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("time", "")

            if content:
                if timestamp:
                    transcript_lines.append(f"[{timestamp}] {role.upper()}: {content}")
                else:
                    transcript_lines.append(f"{role.upper()}: {content}")

        return "\n".join(transcript_lines) if transcript_lines else None

    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except Exception:
            return None
