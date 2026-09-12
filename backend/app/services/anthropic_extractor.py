"""
Anthropic extraction provider implementation.
"""
import json
from typing import Optional
from datetime import date
from anthropic import AsyncAnthropic, APIError, RateLimitError

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.extraction import ExtractedAbsenceInfo
from app.services.extraction_provider import ExtractionProvider, ExtractionError

logger = get_logger("anthropic_extractor")


class AnthropicExtractor(ExtractionProvider):
    """Anthropic-based transcript extraction."""

    EXTRACTION_PROMPT_VERSION = "v1.0"
    MAX_RETRIES = 2

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = AsyncAnthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self.model = model or "claude-3-5-sonnet-20241022"
        self.temperature = 0.1

    async def extract_absence_info(
        self,
        transcript: str,
        student_name: str,
        absence_date: date,
        context: Optional[dict] = None
    ) -> ExtractedAbsenceInfo:
        """Extract using Anthropic Claude with JSON output."""

        prompt = self._build_prompt(transcript, student_name, absence_date, context)

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    temperature=self.temperature,
                    system=self._get_system_prompt(),
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                content = response.content[0].text

                # Parse JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                data = json.loads(content)

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
                raise ExtractionError(f"Anthropic API error: {str(e)}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                raise ExtractionError(f"Invalid JSON from Claude: {str(e)}")

            except Exception as e:
                logger.error(f"Extraction failed: {str(e)}")
                raise ExtractionError(f"Extraction failed: {str(e)}")

    def get_provider_name(self) -> str:
        return "anthropic"

    def get_model_name(self) -> str:
        return self.model

    def _get_system_prompt(self) -> str:
        return """You are an expert at extracting structured information from school attendance call transcripts.

CRITICAL RULES:
1. NEVER invent information - if not stated, mark as null/unknown
2. PRESERVE exact parent statements - do not interpret or diagnose
3. DISTINGUISH between what was said vs. what you infer
4. DO NOT diagnose medical conditions - record what parent said only
5. Mark confidence LOW if information is unclear or missing
6. Flag for follow-up if: unclear info, parent refused, callback requested, or confidence < 0.85

You must respond with ONLY a valid JSON object matching the requested schema. No other text."""

    def _build_prompt(
        self,
        transcript: str,
        student_name: str,
        absence_date: date,
        context: Optional[dict]
    ) -> str:
        return f"""Extract structured absence information from this call transcript.

Student: {student_name}
Absence Date: {absence_date.isoformat()}

Transcript:
{transcript}

Return a JSON object with this exact structure:
{{
    "reason": "Exact reason stated by parent (null if not provided, NEVER invent)",
    "category": "medical | family | personal | transportation | other | unknown",
    "duration": "Expected duration as stated (e.g., '1 day', '2-3 days', null if not mentioned)",
    "expected_return_date": "Expected return date YYYY-MM-DD (null if not stated)",
    "parent_confirmed": boolean (true ONLY if parent explicitly confirmed knowledge of absence),
    "follow_up_required": boolean (true if callback requested, refused to answer, unclear, or confidence < 0.85),
    "confidence_score": float (0.0 to 1.0, where 0.9+ is clear, 0.7-0.89 good, 0.5-0.69 partial, <0.5 very low),
    "notes": "Additional context: callbacks, refusals, concerns (null if none)",
    "parent_statement": "Direct quote from parent (null if none)",
    "call_outcome": "completed | no_answer | voicemail | busy | wrong_number"
}}

Respond with ONLY the JSON object."""
