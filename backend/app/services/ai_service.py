"""
AI service for extracting structured information from call transcripts.
"""
from typing import Dict, Any, Optional
import json
from datetime import date

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai_service")


class AIService:
    """Service for AI-powered information extraction."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.model = settings.LLM_EXTRACTION_MODEL
        self.temperature = settings.LLM_TEMPERATURE

        # Initialize the appropriate client
        if self.provider == "openai":
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "anthropic":
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def extract_absence_info(
        self,
        transcript: str,
        student_name: str,
        absence_date: date
    ) -> Dict[str, Any]:
        """
        Extract structured absence information from call transcript using LLM.

        Args:
            transcript: The call transcript
            student_name: Name of the student
            absence_date: Date of absence

        Returns:
            Structured absence information with confidence score
        """
        prompt = self._build_extraction_prompt(transcript, student_name, absence_date)

        try:
            if self.provider == "openai":
                extraction = await self._extract_with_openai(prompt)
            elif self.provider == "anthropic":
                extraction = await self._extract_with_anthropic(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # Add metadata
            extraction["extracted_at"] = date.today().isoformat()
            extraction["model_used"] = self.model

            logger.info(f"Extracted absence info with confidence: {extraction.get('confidence_score', 0)}")
            return extraction

        except Exception as e:
            logger.error(f"Failed to extract absence info: {str(e)}")
            # Return default structure on error
            return {
                "reason": "Error extracting information",
                "category": "unknown",
                "duration": None,
                "expected_return_date": None,
                "parent_confirmed": False,
                "follow_up_required": True,
                "confidence_score": 0.0,
                "notes": f"Extraction failed: {str(e)}"
            }

    async def _extract_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Extract using OpenAI API with function calling."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at extracting structured information from school attendance call transcripts."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            functions=[{
                "name": "record_absence_information",
                "description": "Record structured absence information from the call",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "The stated reason for absence"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["medical", "family", "personal", "other", "unknown"],
                            "description": "Category of absence"
                        },
                        "duration": {
                            "type": "string",
                            "description": "Expected duration (e.g., '1 day', '2-3 days', 'a week')"
                        },
                        "expected_return_date": {
                            "type": "string",
                            "description": "Expected return date in YYYY-MM-DD format"
                        },
                        "parent_confirmed": {
                            "type": "boolean",
                            "description": "Whether parent confirmed the absence"
                        },
                        "follow_up_required": {
                            "type": "boolean",
                            "description": "Whether follow-up action is needed"
                        },
                        "confidence_score": {
                            "type": "number",
                            "description": "Confidence in extraction (0.0 to 1.0)"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional relevant notes"
                        }
                    },
                    "required": ["reason", "category", "parent_confirmed", "follow_up_required", "confidence_score"]
                }
            }],
            function_call={"name": "record_absence_information"},
            temperature=self.temperature
        )

        # Extract function call arguments
        function_call = response.choices[0].message.function_call
        return json.loads(function_call.arguments)

    async def _extract_with_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Extract using Anthropic API with structured output."""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            temperature=self.temperature,
            system="You are an expert at extracting structured information from school attendance call transcripts. Always respond with valid JSON matching the requested schema.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Parse JSON from response
        content = response.content[0].text

        # Handle code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)

    def _build_extraction_prompt(
        self,
        transcript: str,
        student_name: str,
        absence_date: date
    ) -> str:
        """Build the extraction prompt."""

        return f"""Extract structured absence information from this school attendance call transcript.

Student: {student_name}
Absence Date: {absence_date.isoformat()}

Call Transcript:
{transcript}

Extract the following information and return as JSON:
{{
    "reason": "The stated reason for absence (what parent said)",
    "category": "medical | family | personal | other | unknown",
    "duration": "Expected duration as stated by parent (e.g., '1 day', '2-3 days', 'a week', null if unknown)",
    "expected_return_date": "Expected return date in YYYY-MM-DD format (null if unknown)",
    "parent_confirmed": boolean (true if parent confirmed the absence),
    "follow_up_required": boolean (true if callback requested, doctor's note needed, low confidence, or unclear information),
    "confidence_score": float between 0.0 and 1.0 (how confident you are in the extraction),
    "notes": "Any additional relevant information or concerns"
}}

Guidelines:
- Set confidence_score based on clarity of information (clear = 0.9-1.0, somewhat clear = 0.7-0.9, unclear = 0.5-0.7, very unclear = < 0.5)
- parent_confirmed is true only if parent explicitly confirmed they knew about/approved the absence
- follow_up_required is true if: callback requested, doctor's note mentioned, information unclear, or confidence < 0.85
- If no answer or voicemail, set confidence to 0.0 and follow_up_required to true
- For medical reasons, category is "medical"
- For family emergencies/events, category is "family"
- Use "unknown" category only when truly unclear

Return ONLY the JSON object, no additional text."""

    def calculate_confidence_score(
        self,
        reason: Optional[str],
        category: str,
        parent_confirmed: bool,
        transcript_length: int
    ) -> float:
        """
        Calculate confidence score based on extracted information quality.

        Args:
            reason: The extracted reason
            category: The category
            parent_confirmed: Whether parent confirmed
            transcript_length: Length of transcript in characters

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.5  # Base score

        # Boost for clear reason
        if reason and len(reason) > 20:
            score += 0.2

        # Boost for specific category
        if category in ["medical", "family", "personal"]:
            score += 0.15

        # Boost for parent confirmation
        if parent_confirmed:
            score += 0.15

        # Boost for substantial conversation
        if transcript_length > 200:
            score += 0.1

        # Cap at 1.0
        return min(score, 1.0)
