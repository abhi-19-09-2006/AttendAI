"""
Pydantic schemas for absence information extraction.
"""
from typing import Optional
from datetime import date
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class AbsenceCategoryEnum(str, Enum):
    """Structured absence categories."""
    MEDICAL = "medical"
    FAMILY = "family"
    PERSONAL = "personal"
    TRANSPORTATION = "transportation"
    OTHER = "other"
    UNKNOWN = "unknown"


class ExtractionConfidence(str, Enum):
    """Confidence levels for extraction."""
    HIGH = "high"  # 0.85 - 1.0
    MEDIUM = "medium"  # 0.70 - 0.84
    LOW = "low"  # 0.50 - 0.69
    VERY_LOW = "very_low"  # 0.0 - 0.49


class ExtractedAbsenceInfo(BaseModel):
    """
    Validated structured absence information extracted from transcript.

    All fields preserve what was explicitly stated by the parent.
    Unknown values are marked as None, not invented.
    """

    reason: Optional[str] = Field(
        None,
        description="Exact reason stated by parent. None if not provided. Never invented."
    )

    category: AbsenceCategoryEnum = Field(
        AbsenceCategoryEnum.UNKNOWN,
        description="Categorized absence type. Use UNKNOWN when unclear."
    )

    duration: Optional[str] = Field(
        None,
        description="Expected duration as stated (e.g., '1 day', '2-3 days', 'a week'). None if not mentioned."
    )

    expected_return_date: Optional[date] = Field(
        None,
        description="Expected return date if explicitly stated. None if unknown."
    )

    parent_confirmed: bool = Field(
        False,
        description="True only if parent explicitly confirmed they were aware of and approved the absence."
    )

    follow_up_required: bool = Field(
        False,
        description="True if callback requested, unclear information, parent refused to answer, or confidence < 0.85"
    )

    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in extraction quality (0.0 = no info, 1.0 = clear and complete)"
    )

    confidence_level: ExtractionConfidence = Field(
        ExtractionConfidence.VERY_LOW,
        description="Human-readable confidence level"
    )

    notes: Optional[str] = Field(
        None,
        description="Additional context: callback requests, refusals, concerns. What parent said, not interpretations."
    )

    parent_statement: Optional[str] = Field(
        None,
        description="Key quote from parent about the absence, if available"
    )

    call_outcome: str = Field(
        "completed",
        description="Call outcome: completed, no_answer, voicemail, busy, wrong_number"
    )

    @field_validator("confidence_level", mode="before")
    @classmethod
    def derive_confidence_level(cls, v, info):
        """Derive confidence level from score."""
        score = info.data.get("confidence_score", 0.0)

        if score >= 0.85:
            return ExtractionConfidence.HIGH
        elif score >= 0.70:
            return ExtractionConfidence.MEDIUM
        elif score >= 0.50:
            return ExtractionConfidence.LOW
        else:
            return ExtractionConfidence.VERY_LOW

    @field_validator("follow_up_required", mode="before")
    @classmethod
    def auto_flag_low_confidence(cls, v, info):
        """Automatically require follow-up for low confidence."""
        score = info.data.get("confidence_score", 0.0)

        # Always require follow-up if confidence < 0.85 or parent refused
        if score < 0.85:
            return True

        notes = info.data.get("notes", "")
        if notes and any(word in notes.lower() for word in ["refused", "declined", "won't say", "callback"]):
            return True

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Not feeling well, has a fever",
                "category": "medical",
                "duration": "2-3 days",
                "expected_return_date": "2026-09-15",
                "parent_confirmed": True,
                "follow_up_required": False,
                "confidence_score": 0.92,
                "confidence_level": "high",
                "notes": "Parent mentioned doctor's appointment tomorrow",
                "parent_statement": "He's been running a fever since last night",
                "call_outcome": "completed"
            }
        }
