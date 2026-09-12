"""
Prompt and version management for AI transcript extraction.
"""
from typing import Dict, Any, Optional
from datetime import date
from enum import Enum


class PromptVersion(str, Enum):
    """Available prompt versions for transcript extraction."""
    V1_0 = "v1.0"
    V1_1 = "v1.1"
    LATEST = "v1.1"


class ExtractionPromptManager:
    """
    Centralized manager for LLM prompts, schemas, and versioning.

    Ensures consistent extraction behavior, strict anti-hallucination rules,
    medical non-diagnosis guardrails, and deterministic confidence scoring across providers.
    """

    DEFAULT_VERSION = PromptVersion.V1_1

    SYSTEM_RULES = """You are an expert, highly objective administrative extraction assistant for a college attendance office.
Your task is to extract structured absence information from a completed phone call transcript between an automated attendance assistant and a student's parent/guardian.

CRITICAL INSTRUCTIONS & GUARDRAILS:
1. NEVER INVENT INFORMATION: If an attribute was not explicitly stated during the call, output null (None). Do not extrapolate or guess.
2. DISTINGUISH UNKNOWN VALUES: If the parent could not or would not answer, or the call reached voicemail, set category to "unknown" and reason to null.
3. PRESERVE VERBATIM STATEMENTS: Record the exact words spoken by the parent under "parent_statement" and "reason". Do not paraphrase or sanitize.
4. DO NOT DIAGNOSE MEDICAL CONDITIONS: Never extrapolate medical symptoms into diagnostic labels. E.g., if parent said "he has a fever and headache", record reason as "fever and headache", NOT "viral influenza".
5. CONFIDENCE SCORING:
   - 0.90 - 1.00: High confidence. Clear parent confirmation, explicit reason, known timeframe.
   - 0.70 - 0.89: Medium confidence. Parent confirmed, general reason given, but minor details missing.
   - 0.50 - 0.69: Low confidence. Unclear/vague parent answers, conflicting details, or hesitations.
   - 0.00 - 0.49: Very low confidence. Parent refused to give reason, wrong number, or reached voicemail.
6. AUTOMATIC FACULTY FOLLOW-UP TRIAGE:
   - follow_up_required must be true if:
     * confidence_score < 0.85
     * parent refused to provide a reason or stated it is a private matter
     * parent requested a callback from faculty or administration
     * call ended prematurely or reached voicemail
     * parent did NOT confirm knowledge of absence
7. CATEGORIES:
   - "medical": Illness, doctor appointment, hospital, injury (no diagnosis)
   - "family": Wedding, funeral, family emergency, family travel
   - "personal": Personal matter, mental health day, rest
   - "transportation": Vehicle breakdown, transit delay, severe commute weather
   - "other": Explicit reason that does not fit above
   - "unknown": No reason provided, vague response, or unreachable
"""

    @classmethod
    def get_system_prompt(cls, version: PromptVersion = DEFAULT_VERSION) -> str:
        """Get the system prompt for a specific version."""
        return cls.SYSTEM_RULES

    @classmethod
    def build_extraction_prompt(
        cls,
        transcript: str,
        student_name: str,
        absence_date: date,
        context: Optional[Dict[str, Any]] = None,
        version: PromptVersion = DEFAULT_VERSION
    ) -> str:
        """
        Construct user prompt with dynamic student data and call transcript.
        """
        date_str = absence_date.isoformat() if isinstance(absence_date, date) else str(absence_date)

        prompt = f"""Extract structured absence information for student: {student_name}
Absence Date: {date_str}
"""
        if context:
            if "student_id" in context:
                prompt += f"Student ID: {context['student_id']}\n"
            if "grade_level" in context:
                prompt += f"Grade/Year: {context['grade_level']}\n"
            if "notes" in context:
                prompt += f"Prior Context: {context['notes']}\n"

        prompt += f"""
Transcript:
---
{transcript.strip()}
---

Extract the structured absence information strictly adhering to the schema and instructions.
"""
        return prompt

    @classmethod
    def get_openai_function_schema(cls, version: PromptVersion = DEFAULT_VERSION) -> Dict[str, Any]:
        """OpenAI Function / Tool Definition schema."""
        return {
            "name": "record_absence_information",
            "description": "Record structured absence details extracted from attendance transcript",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": ["string", "null"],
                        "description": "Exact reason stated by parent. null if not stated. NEVER fabricate."
                    },
                    "category": {
                        "type": "string",
                        "enum": ["medical", "family", "personal", "transportation", "other", "unknown"],
                        "description": "High-level category of absence. Use 'unknown' if unclear or omitted."
                    },
                    "duration": {
                        "type": ["string", "null"],
                        "description": "Duration of absence as stated by parent (e.g., '1 day', '2-3 days'). null if unknown."
                    },
                    "expected_return": {
                        "type": ["string", "null"],
                        "description": "Expected return timeframe or date as stated by parent (e.g., 'Monday', 'tomorrow', '2026-09-15'). null if unknown."
                    },
                    "expected_return_date": {
                        "type": ["string", "null"],
                        "description": "Expected return date in YYYY-MM-DD format if explicitly determinable. null if unknown."
                    },
                    "parent_confirmed": {
                        "type": "boolean",
                        "description": "true ONLY if parent/guardian explicitly confirmed awareness and approval of the absence."
                    },
                    "follow_up_required": {
                        "type": "boolean",
                        "description": "true if parent refused, callback requested, vague answers, or confidence < 0.85."
                    },
                    "confidence_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Granular confidence score from 0.0 to 1.0 based on clarity and completeness."
                    },
                    "notes": {
                        "type": ["string", "null"],
                        "description": "Objective notes capturing context, refusals, callback requests, or specific parent remarks."
                    },
                    "parent_statement": {
                        "type": ["string", "null"],
                        "description": "Verbatim key quote from parent regarding the absence reason."
                    },
                    "call_outcome": {
                        "type": "string",
                        "enum": ["completed", "no_answer", "voicemail", "busy", "wrong_number"],
                        "description": "Final outcome of call connection."
                    }
                },
                "required": [
                    "category",
                    "parent_confirmed",
                    "follow_up_required",
                    "confidence_score",
                    "call_outcome"
                ]
            }
        }

    @classmethod
    def get_anthropic_json_schema(cls, version: PromptVersion = DEFAULT_VERSION) -> str:
        """JSON output instruction for Anthropic Claude models."""
        return """You must respond with ONLY a valid JSON object matching this exact schema:
{
    "reason": string or null (exact reason stated by parent, null if unknown, NEVER fabricate),
    "category": "medical" | "family" | "personal" | "transportation" | "other" | "unknown",
    "duration": string or null (e.g., "1 day", "2-3 days", null if unknown),
    "expected_return": string or null (e.g., "Monday", "tomorrow", "2026-09-15", null if unknown),
    "expected_return_date": "YYYY-MM-DD" or null,
    "parent_confirmed": boolean (true ONLY if parent confirmed awareness of absence),
    "follow_up_required": boolean (true if callback requested, refused reason, vague, or confidence < 0.85),
    "confidence_score": float (0.0 to 1.0),
    "notes": string or null,
    "parent_statement": string or null (verbatim quote from parent),
    "call_outcome": "completed" | "no_answer" | "voicemail" | "busy" | "wrong_number"
}
Output nothing else before or after the JSON object."""
