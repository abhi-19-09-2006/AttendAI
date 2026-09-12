"""
Anthropic extraction provider implementation.
"""
import json
import asyncio
from typing import Optional
from datetime import date
from anthropic import AsyncAnthropic, APIError, RateLimitError, APIConnectionError

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.extraction import ExtractedAbsenceInfo
from app.services.extraction_provider import ExtractionProvider, ExtractionError
from app.services.prompt_manager import ExtractionPromptManager, PromptVersion

logger = get_logger("anthropic_extractor")


class AnthropicExtractor(ExtractionProvider):
    """Anthropic Claude-based transcript extraction."""

    DEFAULT_PROMPT_VERSION = PromptVersion.LATEST
    MAX_RETRIES = 2
    RETRY_BASE_DELAY = 1.0  # seconds

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        prompt_version: PromptVersion = DEFAULT_PROMPT_VERSION
    ):
        self.client = AsyncAnthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self.model = model or "claude-3-5-sonnet-20241022"
        self.temperature = 0.1
        self.prompt_version = prompt_version
        self.prompt_manager = ExtractionPromptManager

    async def extract_absence_info(
        self,
        transcript: str,
        student_name: str,
        absence_date: date,
        context: Optional[dict] = None
    ) -> ExtractedAbsenceInfo:
        """Extract structured absence information using Anthropic Claude."""

        prompt = self.prompt_manager.build_extraction_prompt(
            transcript=transcript,
            student_name=student_name,
            absence_date=absence_date,
            context=context,
            version=self.prompt_version
        )
        # Append JSON formatting instructions
        prompt += "\n" + self.prompt_manager.get_anthropic_json_schema(version=self.prompt_version)
        system_prompt = self.prompt_manager.get_system_prompt(version=self.prompt_version)

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                content = response.content[0].text.strip()

                # Clean markdown formatting if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                data = json.loads(content)

                # Validate and return
                return ExtractedAbsenceInfo(**data)

            except RateLimitError as e:
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Anthropic rate limit hit, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                raise ExtractionError(f"Anthropic Rate limit exceeded after retries: {str(e)}")

            except (APIError, APIConnectionError) as e:
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Anthropic API error ({str(e)}), retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    continue
                raise ExtractionError(f"Anthropic API error: {str(e)}")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude: {str(e)}")
                raise ExtractionError(f"Invalid JSON returned by Claude: {str(e)}")

            except Exception as e:
                logger.error(f"Anthropic extraction unexpected failure: {str(e)}")
                raise ExtractionError(f"Extraction failed: {str(e)}")

    def get_provider_name(self) -> str:
        return "anthropic"

    def get_model_name(self) -> str:
        return self.model
