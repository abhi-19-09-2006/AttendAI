"""
Voice provider interface - abstraction for voice calling services.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class CallContext(BaseModel):
    """Context information for making a call."""
    phone_number: str
    student_name: str
    absence_date: str
    correlation_id: str  # Internal ID to correlate webhooks back to our call record


class CallResult(BaseModel):
    """Result of initiating a call."""
    provider_call_id: str
    status: str
    initiated_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class CallStatusResult(BaseModel):
    """Status of an ongoing or completed call."""
    provider_call_id: str
    status: str
    duration_seconds: Optional[int] = None
    ended_at: Optional[datetime] = None
    transcript: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VoiceProvider(ABC):
    """Abstract base class for voice calling providers."""

    @abstractmethod
    async def create_call(self, context: CallContext) -> CallResult:
        """
        Initiate a phone call.

        Args:
            context: Call context with student/absence information

        Returns:
            CallResult with provider call ID and initial status
        """
        pass

    @abstractmethod
    async def get_call_status(self, provider_call_id: str) -> CallStatusResult:
        """
        Get the current status of a call.

        Args:
            provider_call_id: Provider's call identifier

        Returns:
            Current call status and metadata
        """
        pass

    @abstractmethod
    async def cancel_call(self, provider_call_id: str) -> bool:
        """
        Cancel an ongoing call.

        Args:
            provider_call_id: Provider's call identifier

        Returns:
            True if successfully cancelled
        """
        pass

    @abstractmethod
    def parse_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse provider-specific webhook payload to standard format.

        Args:
            payload: Raw webhook payload from provider

        Returns:
            Standardized webhook data with:
                - correlation_id: Our internal call ID
                - provider_call_id: Provider's call ID
                - status: Call status
                - transcript: Call transcript (if available)
                - metadata: Additional provider-specific data
        """
        pass
