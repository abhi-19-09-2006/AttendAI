"""
OpenAI extraction provider implementation.
"""
import json
from typing import Optional
from datetime import date
from openai import AsyncOpenAI, APIError, RateLimitError

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.extraction import ExtractedAbsenceInfo, AbsenceCategoryEnum
from app.services.extraction_provider import ExtractionProvider, ExtractionError

logger = get_logger("openai_extractor")


class OpenAIExtractor(ExtractionProvider):
    """OpenAI-based transcript extraction."""

    EXTRACTION_PROMPT_VERSION = "v1.0"
    MAX_RETRIES = 2

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.model = model or settings.LLM_EXTRACTION_MODEL
        self.temperature = 0.1  # Low temperature for consistent extraction

    async def extract_absence_info(
        self,
        transcript: str,
        student_name: str,
        absence_date: date,
        context: Optional[dict] = None
    ) -> ExtractedAbsenceInfo:
        """Extract using OpenAI with function calling for structured output."""

        prompt = self._build_prompt(transcript, student_name, absence_date, context)

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": self._get_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    functions=[self._get_function_schema()],
                    function_call={"name": "record_absence_information"},
                    temperature=self.temperature,
                    max_tokens=800
                )

                # Extract function call
                function_call = response.choices[0].message.function_call
                if not function_call:
                    raise ExtractionError("No function call in response")

                data = json.loads(function_call.arguments)

                # Validate and return
                return ExtractedAbsenceInfo(**data)

            except RateLimitError as e:
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"Rate limit hit, retrying (attempt {attempt + 1})")
                    continue
                raise ExtractionError(f"Rate limit exceeded: {str(e)}")

            except APIError as e:
                if attempt < self.MAX_RETRIES:
                    logger.warning(f"API error, retrying (attempt {attempt + 1}): {str(e)}")
                    continue
                raise ExtractionError(f"OpenAI API error: {str(e)}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse function call arguments: {str(e)}")
                raise ExtractionError(f"Invalid JSON response: {str(e)}")

            except Exception as e:
                logger.error(f"Extraction failed: {str(e)}")
                raise ExtractionError(f"Extraction failed: {str(e)}")

    def get_provider_name(self) -> str:
        return "openai"

    def get_model_name(self) -> str:
        return self.model

    def _get_system_prompt(self) -> str:
        """System prompt defining extraction rules."""
        return """You are an expert at extracting structured information from school attendance call transcripts.

CRITICAL RULES:
1. NEVER invent information - if not stated, mark as null/unknown
2. PRESERVE exact parent statements - do not interpret or diagnose
3. DISTINGUISH between what was said vs. what you infer
4. DO NOT diagnose medical conditions - record what parent said only
5. Mark confidence LOW if information is unclear or missing
6. Flag for follow-up if: unclear info, parent refused, callback requested, or confidence < 0.85

Confidence scoring:
- 0.9-1.0: Clear, complete information with parent confirmation
- 0.7-0.89: Good information but some details missing
- 0.5-0.69: Partial information or somewhat unclear
- 0.0-0.49: Very limited info, no answer, or parent refused

Categories:
- medical: Illness, injury, medical appointment (but DO NOT diagnose)
- family: Family event, emergency, obligation
- personal: Personal matter, mental health day
- transportation: Travel issues, car problems, weather
- other: Stated reason that doesn't fit above
- unknown: No reason given or unclear

Extract ONLY what was explicitly stated."""

    def _build_prompt(
        self,
        transcript: str,
        student_name: str,
        absence_date: date,
        context: Optional[dict]
    ) -> str:
        """Build extraction prompt with transcript."""

        prompt = f"""Extract absence information from this call transcript.

Student: {student_name}
Absence Date: {absence_date.isoformat()}
"""

        if context:
            if context.get("grade_level"):
                prompt += f"Grade Level: {context['grade_level']}\n"

        prompt += f"""
Call Transcript:
{transcript}

EXTRACT ONLY WHAT WAS EXPLICITLY STATED. Examples:

✓ GOOD:
- reason: "Not feeling well" (parent said this)
- reason: "Doctor's appointment" (parent said this)
- reason: null (parent didn't provide reason)

✗ BAD:
- reason: "Has the flu" (unless parent said "flu" specifically)
- reason: "Sick" (if parent said "not feeling well" - use their words)
- reason: "Personal reasons" (if parent didn't say anything - use null)

If parent reached voicemail or didn't answer: set call_outcome accordingly, confidence to 0.0

If parent refused to provide reason: set reason to null, notes to "Parent declined to provide reason", follow_up_required to true

If parent gave vague answer: record exactly what they said, set confidence appropriately (0.5-0.7)
"""

        return prompt

    def _get_function_schema(self) -> dict:
        """OpenAI function schema for structured output."""
        return {
            "name": "record_absence_information",
            "description": "Record structured absence information from the call",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": ["string", "null"],
                        "description": "Exact reason stated by parent. null if not provided. NEVER invent."
                    },
                    "category": {
                        "type": "string",
                        "enum": ["medical", "family", "personal", "transportation", "other", "unknown"],
                        "description": "Category of absence. Use 'unknown' when unclear."
                    },
                    "duration": {
                        "type": ["string", "null"],
                        "description": "Expected duration as stated by parent (e.g., '1 day', '2-3 days'). null if not mentioned."
                    },
                    "expected_return_date": {
                        "type": ["string", "null"],
                        "description": "Expected return date in YYYY-MM-DD format. null if not stated."
                    },
                    "parent_confirmed": {
                        "type": "boolean",
                        "description": "true ONLY if parent explicitly confirmed they knew about the absence"
                    },
                    "follow_up_required": {
                        "type": "boolean",
                        "description": "true if callback requested, refused to answer, unclear info, or confidence < 0.85"
                    },
                    "confidence_score": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Confidence: 0.9+ clear, 0.7-0.89 good, 0.5-0.69 partial, <0.5 very limited"
                    },
                    "notes": {
                        "type": ["string", "null"],
                        "description": "Additional context: callbacks, refusals, concerns. What parent said, not your interpretation."
                    },
                    "parent_statement": {
                        "type": ["string", "null"],
                        "description": "Direct quote from parent about absence, if available"
                    },
                    "call_outcome": {
                        "type": "string",
                        "enum": ["completed", "no_answer", "voicemail", "busy", "wrong_number"],
                        "description": "Outcome of the call attempt"
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
