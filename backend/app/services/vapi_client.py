"""
Vapi.ai API client for making phone calls.

Includes retry logic with exponential backoff for transient failures,
configurable timeouts, and PII redaction in logs.
"""
from typing import Optional, Dict, Any
import httpx
from datetime import datetime
import asyncio

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.pii_redaction import redact_phone

logger = get_logger("vapi")


class VapiAPIError(Exception):
    """Exception raised for Vapi API errors."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Vapi API error {status_code}: {message}")


class VapiClient:
    """
    Client for interacting with Vapi.ai API.
    
    Features:
    - Automatic retry with exponential backoff for transient failures
    - Configurable timeouts
    - PII redaction in logs
    - Structured error handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize Vapi client.
        
        Args:
            api_key: Vapi API key (defaults to settings.VAPI_API_KEY)
            base_url: Vapi API base URL (defaults to settings.VAPI_BASE_URL)
            phone_number_id: Phone number ID (defaults to settings.VAPI_PHONE_NUMBER_ID)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for transient failures
            retry_delay: Initial retry delay in seconds (doubles on each retry)
        """
        self.api_key = api_key or settings.VAPI_API_KEY
        self.base_url = base_url or settings.VAPI_BASE_URL
        self.phone_number_id = phone_number_id or settings.VAPI_PHONE_NUMBER_ID
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with automatic retry on transient failures.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments passed to httpx
            
        Returns:
            httpx.Response object
            
        Raises:
            VapiAPIError: For non-retryable API errors
            httpx.HTTPError: For network errors after max retries
        """
        last_exception = None
        delay = self.retry_delay
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method,
                        f"{self.base_url}{endpoint}",
                        headers=self.headers,
                        **kwargs
                    )
                    
                    # Success
                    if response.status_code < 400:
                        return response
                    
                    # Client errors (4xx) are not retryable
                    if 400 <= response.status_code < 500:
                        error_msg = response.text
                        logger.error(
                            f"Vapi API client error: {response.status_code}",
                            status_code=response.status_code,
                            error=error_msg[:200]  # Truncate long errors
                        )
                        raise VapiAPIError(response.status_code, error_msg)
                    
                    # Server errors (5xx) are retryable
                    if response.status_code >= 500:
                        logger.warning(
                            f"Vapi API server error (attempt {attempt + 1}/{self.max_retries + 1}): "
                            f"{response.status_code}",
                            status_code=response.status_code
                        )
                        last_exception = VapiAPIError(response.status_code, response.text)
                    
                except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                    # Network errors are retryable
                    logger.warning(
                        f"Vapi network error (attempt {attempt + 1}/{self.max_retries + 1}): {type(e).__name__}",
                        error_type=type(e).__name__
                    )
                    last_exception = e
                
                # Don't retry on last attempt
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                    
            except VapiAPIError as e:
                # Non-retryable API error
                raise
            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error in Vapi request: {type(e).__name__}: {str(e)}")
                last_exception = e
                break
        
        # All retries exhausted
        logger.error(f"Vapi request failed after {self.max_retries + 1} attempts")
        if last_exception:
            raise last_exception
        raise httpx.HTTPError("Request failed with no exception details")

    async def create_call(
        self,
        phone_number: str,
        student_name: str,
        absence_date: str,
        assistant_config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initiate a phone call via Vapi.

        Args:
            phone_number: Phone number to call (E.164 format)
            student_name: Name of the absent student
            absence_date: Date of absence
            assistant_config: Optional custom assistant configuration
            metadata: Optional metadata to attach to call (for webhook correlation)

        Returns:
            Call response with call_id and status
            
        Raises:
            VapiAPIError: For API errors
            httpx.HTTPError: For network errors
        """
        # Build assistant configuration
        if assistant_config is None:
            assistant_config = {
                "name": f"Attendance Call - {student_name}",
                "model": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"You are calling a parent about their child {student_name}'s "
                                f"absence on {absence_date}. Be professional, empathetic, and brief. "
                                f"Ask for the reason for absence and expected return date. "
                                f"Keep the conversation under 2 minutes."
                            )
                        }
                    ]
                },
                "voice": {
                    "provider": "11labs",
                    "voiceId": "rachel"
                },
                "firstMessage": (
                    f"Hello, this is the automated attendance system calling about "
                    f"{student_name}'s absence on {absence_date}. May I speak with a parent or guardian?"
                ),
                "endCallPhrase": "Goodbye",
                "maxDurationSeconds": 120
            }

        payload = {
            "phoneNumberId": self.phone_number_id,
            "customer": {
                "number": phone_number
            },
            "assistant": assistant_config
        }
        
        # Add metadata if provided
        if metadata:
            payload["metadata"] = metadata

        logger.info(
            "Initiating Vapi call",
            phone=redact_phone(phone_number),
            student=student_name,
            absence_date=absence_date
        )

        response = await self._request_with_retry("POST", "/call", json=payload)
        data = response.json()
        
        call_id = data.get("id")
        logger.info("Vapi call created", call_id=call_id)
        
        return data

    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """
        Get the status of a call.

        Args:
            call_id: Vapi call ID

        Returns:
            Call status information
            
        Raises:
            VapiAPIError: For API errors
            httpx.HTTPError: For network errors
        """
        logger.debug("Getting Vapi call status", call_id=call_id)
        
        response = await self._request_with_retry("GET", f"/call/{call_id}")
        data = response.json()
        
        status = data.get("status")
        logger.debug("Vapi call status retrieved", call_id=call_id, status=status)
        
        return data

    async def get_call_transcript(self, call_id: str) -> Optional[str]:
        """
        Get the transcript of a completed call.

        Args:
            call_id: Vapi call ID

        Returns:
            Call transcript or None if not available
            
        Raises:
            VapiAPIError: For API errors
            httpx.HTTPError: For network errors
        """
        logger.debug("Getting Vapi call transcript", call_id=call_id)
        
        data = await self.get_call_status(call_id)
        
        # Extract transcript from response
        transcript = data.get("transcript")
        if transcript:
            logger.info(
                "Vapi transcript retrieved",
                call_id=call_id,
                length=len(transcript)
            )
            return transcript
        
        # Try to extract from messages
        messages = data.get("messages", [])
        if messages:
            transcript = "\n".join([
                f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                for msg in messages
                if msg.get('content')
            ])
            logger.info(
                "Vapi transcript extracted from messages",
                call_id=call_id,
                message_count=len(messages),
                length=len(transcript)
            )
            return transcript
        
        logger.warning("No transcript available for Vapi call", call_id=call_id)
        return None

    async def cancel_call(self, call_id: str) -> bool:
        """
        Cancel an ongoing call.

        Args:
            call_id: Vapi call ID

        Returns:
            True if cancelled successfully, False otherwise
        """
        logger.info("Cancelling Vapi call", call_id=call_id)
        
        try:
            await self._request_with_retry("DELETE", f"/call/{call_id}")
            logger.info("Vapi call cancelled successfully", call_id=call_id)
            return True
        except Exception as e:
            logger.error(f"Failed to cancel Vapi call: {type(e).__name__}: {str(e)}", call_id=call_id)
            return False
