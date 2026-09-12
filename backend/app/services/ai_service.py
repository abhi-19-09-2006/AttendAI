"""
AI service for transcript extraction and analysis.
"""
from typing import Optional, Dict, Any
from datetime import date

from app.core.logging import get_logger
from app.schemas.extraction import ExtractedAbsenceInfo
from app.services.extraction_provider import ExtractionProvider, ExtractionError
from app.services.extraction_factory import get_extraction_provider

logger = get_logger("ai_service")


class AIService:
    """Service for AI-powered transcript extraction."""

    def __init__(self, provider: Optional[ExtractionProvider] = None):
        self.provider = provider or get_extraction_provider()
        logger.info(f"Initialized AIService with provider: {self.provider.get_provider_name()}")

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
            transcript: The call transcript
            student_name: Name of the student
            absence_date: Date of absence
            context: Additional context

        Returns:
            Validated ExtractedAbsenceInfo
        """
        try:
            result = await self.provider.extract_absence_info(
                transcript=transcript,
                student_name=student_name,
                absence_date=absence_date,
                context=context
            )

            logger.info(
                f"Extracted info for {student_name}: category={result.category}, "
                f"confidence={result.confidence_score:.2f}, follow_up={result.follow_up_required}"
            )

            return result

        except ExtractionError as e:
            logger.error(f"Extraction error: {str(e)}")
            # Return safe default for failed extraction
            return ExtractedAbsenceInfo(
                reason="Extraction failed",
                category="unknown",
                parent_confirmed=False,
                follow_up_required=True,
                confidence_score=0.0,
                notes=f"Extraction error: {str(e)}",
                call_outcome="completed"
            )
