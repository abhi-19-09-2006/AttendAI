"""
Transcript extraction provider interface.
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from app.schemas.extraction import ExtractedAbsenceInfo


class ExtractionProvider(ABC):
    """Abstract base class for LLM-based information extraction."""

    @abstractmethod
    async def extract_absence_info(
        self,
        transcript: str,
        student_name: str,
        absence_date: date,
        context: Optional[dict] = None
    ) -> ExtractedAbsenceInfo:
        """
        Extract structured absence information from call transcript.

        Args:
            transcript: The full call transcript
            student_name: Name of the absent student
            absence_date: Date of the absence
            context: Additional context (grade level, previous absences, etc.)

        Returns:
            Validated ExtractedAbsenceInfo with confidence scoring

        Raises:
            ExtractionError: If extraction fails after retries
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name for logging."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used."""
        pass


class ExtractionError(Exception):
    """Raised when extraction fails."""
    pass
