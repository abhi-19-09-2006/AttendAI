"""
Factory for creating extraction providers.
"""
from typing import Optional
from app.core.config import settings
from app.services.extraction_provider import ExtractionProvider
from app.services.openai_extractor import OpenAIExtractor
from app.services.anthropic_extractor import AnthropicExtractor


def get_extraction_provider(
    provider_name: Optional[str] = None
) -> ExtractionProvider:
    """
    Get the configured extraction provider.

    Args:
        provider_name: Override provider ("openai" or "anthropic").
                      Defaults to settings.LLM_PROVIDER.

    Returns:
        ExtractionProvider instance
    """
    provider = provider_name or settings.LLM_PROVIDER

    if provider == "openai":
        return OpenAIExtractor()
    elif provider == "anthropic":
        return AnthropicExtractor()
    else:
        raise ValueError(f"Unsupported extraction provider: {provider}")
