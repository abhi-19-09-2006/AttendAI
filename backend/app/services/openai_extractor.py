"""
OpenAI extraction provider implementation.
"""
import json
import asyncio
from typing import Optional
from datetime import date
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.extraction import ExtractedAbsenceInfo
from app.services.extraction_provider import ExtractionProvider, ExtractionError
from app.services.prompt_manager import ExtractionPromptManager, PromptVersion

logger = get_logger("openai_extractor")


class OpenAIExtractor(ExtractionProvider):
    """OpenAI-based transcript extraction with structured function calling."""

    DEFAULT_PROMPT_VERSION = PromptVersion.LATEST
    MAX_RETRIES = 2
    RETRY_BASE_DELAY = 1.0  # seconds

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompt_version: PromptVersion = DEFAULT_PROMPT_VERSION
    ):
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self.model = model or settings.LLM_EXTRACTION_MODEL
        self.temperature = 0.1  # Low temperature for deterministic and faithful extraction
        self.prompt_version = prompt_version
        self.prompt_manager = ExtractionPromptManager

    async def extract_absence_info(
        self,
        transcript: str,
        student_name: str,
        absence_date: date,
        context: Optional[dict] = None
    ) -> ExtractedAbsenceInfo:
        """Extract structured information using OpenAI function calling."""

        prompt = self.prompt_manager.build_extraction_prompt(
            transcript=transcript,
            student_name=student_name,
            absence_date=absence_date,
            context=context,
            version=self.prompt_version
        )
        system_prompt = self.prompt_manager.get_system_prompt(version=self.prompt_version)
        function_schema = self.prompt_manager.get_openai_function_schema(version=self.prompt_version)

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    functions=[function_schema],
                    function_call={"name": "record_absence_information"},
                    temperature=self.temperature,
                    max_tokens=800
                )

                choice = response.choices[0]
                function_call = choice.message.function_call
                if not function_call or not function_call.arguments:
                    raise ExtractionError("OpenAI did not invoke the extraction function.")

                raw_args = function_call.arguments
                data = json.loads(raw_args)

                # Validate through Pydantic schema
                validated_info = ExtractedAbsenceInfo(**data)
                return validated_info

            except RateLimitError as e:
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"OpenAI rate limit hit, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                raise ExtractionError(f"OpenAI Rate limit exceeded after retries: {str(e)}")

            except (APIError, APIConnectionError) as e:
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"OpenAI API error ({str(e)}), retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                raise ExtractionError(f"OpenAI API error: {str(e)}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode OpenAI function arguments: {str(e)}")
                raise ExtractionError(f"Invalid JSON returned by OpenAI: {str(e)}")

            except Exception as e:
                logger.error(f"OpenAI extraction unexpected error: {str(e)}")
                raise ExtractionError(f"Extraction failed: {str(e)}")

    def get_provider_name(self) -> str:
        return "openai"

    def get_model_name(self) -> str:
        return self.model
