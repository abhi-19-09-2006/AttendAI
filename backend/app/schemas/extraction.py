"""
Pydantic schemas for absence information extraction.
"""
from typing import Optional, Any, Dict, Union
from datetime import date
from pydantic import BaseModel, Field, model_validator
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

    expected_return: Optional[str] = Field(
        None,
        description="Expected return timeframe or date string as stated by parent (e.g., 'Monday', 'tomorrow', '2026-09-15'). None if unknown."
    )

    expected_return_date: Optional[date] = Field(
        None,
        description="Expected return date if explicitly determinable (YYYY-MM-DD). None if unknown."
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

    @property
    def confidence(self) -> float:
        """Alias for confidence_score."""
        return self.confidence_score

    @model_validator(mode="before")
    @classmethod
    def populate_expected_return_and_confidence(cls, data: Any) -> Any:
        """Handle aliases and mutual populating of fields."""
        if isinstance(data, dict):
            # If 'confidence' passed instead of 'confidence_score'
            if "confidence" in data and "confidence_score" not in data:
                data["confidence_score"] = data["confidence"]

            # If expected_return_date is provided but expected_return is not, populate expected_return
            if data.get("expected_return_date") and not data.get("expected_return"):
                ret_date = data["expected_return_date"]
                data["expected_return"] = ret_date.isoformat() if hasattr(ret_date, "isoformat") else str(ret_date)
            elif data.get("expected_return") and not data.get("expected_return_date"):
                # Try to parse if it's a date string (YYYY-MM-DD)
                ret_str = str(data["expected_return"]).strip()
                if len(ret_str) == 10 and ret_str.count("-") == 2:
                    try:
                        data["expected_return_date"] = date.fromisoformat(ret_str)
                    except ValueError:
                        pass

        return data

    @model_validator(mode="after")
    def derive_confidence_and_followup(self) -> "ExtractedAbsenceInfo":
        """
        Derive derived fields after all inputs are validated.

        Runs at model level so ``confidence_score`` is always available
        (field-level ``info.data`` depends on field declaration order and is
        unreliable here). Preserves an explicit ``follow_up_required=True``
        and only forces one when confidence is low or a refusal is flagged.
        """
        score = self.confidence_score

        if score >= 0.85:
            self.confidence_level = ExtractionConfidence.HIGH
        elif score >= 0.70:
            self.confidence_level = ExtractionConfidence.MEDIUM
        elif score >= 0.50:
            self.confidence_level = ExtractionConfidence.LOW
        else:
            self.confidence_level = ExtractionConfidence.VERY_LOW

        notes = self.notes or ""
        refusal_markers = ("refused", "declined", "won't say", "private matter", "callback")
        if score < 0.85 or any(marker in notes.lower() for marker in refusal_markers):
            self.follow_up_required = True

        return self

    def to_canonical_dict(self) -> Dict[str, Any]:
        """
        Return the exact expected canonical schema format:
        {
            reason,
            category,
            duration,
            expected_return,
            parent_confirmed,
            follow_up_required,
            confidence
        }
        """
        return {
            "reason": self.reason,
            "category": self.category.value if hasattr(self.category, "value") else str(self.category),
            "duration": self.duration,
            "expected_return": self.expected_return or (self.expected_return_date.isoformat() if self.expected_return_date else None),
            "parent_confirmed": self.parent_confirmed,
            "follow_up_required": self.follow_up_required,
            "confidence": self.confidence_score
        }

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Not feeling well, has a fever",
                "category": "medical",
                "duration": "2-3 days",
                "expected_return": "2026-09-15",
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
