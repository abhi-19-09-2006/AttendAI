"""
Vapi.ai API client for making AI phone calls.
"""
from typing import Optional, Dict, Any
import httpx
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("vapi")


class VapiClient:
    """Client for interacting with Vapi.ai API."""

    def __init__(self):
        self.api_key = settings.VAPI_API_KEY
        self.base_url = settings.VAPI_BASE_URL
        self.phone_number_id = settings.VAPI_PHONE_NUMBER_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_call(
        self,
        phone_number: str,
        student_name: str,
        absence_date: str,
        assistant_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initiate a phone call via Vapi.

        Args:
            phone_number: Phone number to call (E.164 format)
            student_name: Name of the absent student
            absence_date: Date of absence
            assistant_config: Optional custom assistant configuration

        Returns:
            Call response with call_id and status
        """
        # Default assistant configuration
        default_assistant = {
            "model": {
                "provider": "openai",
                "model": settings.LLM_VOICE_MODEL,
                "temperature": settings.LLM_TEMPERATURE,
                "maxTokens": settings.LLM_MAX_TOKENS
            },
            "voice": {
                "provider": "11labs",
                "voiceId": "rachel"  # Professional female voice
            },
            "firstMessage": f"Hello! This is an automated call from the school regarding {student_name}'s absence on {absence_date}. May I please speak with a parent or guardian?",
            "systemPrompt": self._get_system_prompt(student_name, absence_date),
            "endCallFunctionEnabled": True,
            "recordingEnabled": True,
            "maxDurationSeconds": settings.MAX_CALL_DURATION_SECONDS
        }

        assistant = assistant_config or default_assistant

        payload = {
            "phoneNumberId": self.phone_number_id,
            "customer": {
                "number": phone_number
            },
            "assistant": assistant
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

                logger.info(f"Vapi call initiated: {data.get('id')} to {phone_number}")
                return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Vapi API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Vapi call: {str(e)}")
            raise

    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """
        Get the status of a call.

        Args:
            call_id: Vapi call ID

        Returns:
            Call status information
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/call/{call_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Failed to get call status: {str(e)}")
            raise

    async def get_call_transcript(self, call_id: str) -> Optional[str]:
        """
        Get the transcript of a completed call.

        Args:
            call_id: Vapi call ID

        Returns:
            Call transcript or None if not available
        """
        try:
            call_data = await self.get_call_status(call_id)

            # Extract messages from the call
            messages = call_data.get("messages", [])
            if not messages:
                return None

            # Format transcript
            transcript_lines = []
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("time", "")

                transcript_lines.append(f"[{timestamp}] {role.upper()}: {content}")

            return "\n".join(transcript_lines)

        except Exception as e:
            logger.error(f"Failed to get call transcript: {str(e)}")
            return None

    def _get_system_prompt(self, student_name: str, absence_date: str) -> str:
        """
        Generate the AI assistant's system prompt.

        Args:
            student_name: Name of the absent student
            absence_date: Date of absence

        Returns:
            System prompt for the AI assistant
        """
        return f"""You are a professional school attendance officer calling about {student_name}'s absence on {absence_date}.

Your goal is to:
1. Verify you're speaking with a parent or guardian
2. Confirm the absence and ask for the reason
3. Determine the expected duration and return date
4. Be empathetic, professional, and brief

Key guidelines:
- Be warm and understanding
- Keep the call under 3 minutes
- Ask open-ended questions: "Can you tell me why {student_name} was absent?"
- If medical: ask about expected recovery time
- If family matter: express understanding, ask when they'll return
- If parent requests callback: acknowledge and note it
- End politely: "Thank you for the information. We hope {student_name} feels better soon."

Important information to collect:
- Reason for absence (medical, family, personal, other)
- Expected duration (1 day, 2-3 days, a week, unknown)
- Expected return date
- Whether parent confirmed the absence
- Any follow-up needed (doctor's note, callback requested)

Be conversational but efficient. If parent is busy, offer to call back."""

    async def cancel_call(self, call_id: str) -> bool:
        """
        Cancel an ongoing call.

        Args:
            call_id: Vapi call ID

        Returns:
            True if cancelled successfully
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{self.base_url}/call/{call_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                logger.info(f"Cancelled Vapi call: {call_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to cancel call: {str(e)}")
            return False
