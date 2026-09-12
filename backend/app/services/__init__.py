"""
Services package for business logic.
"""
from app.services.voice_provider import VoiceProvider, CallContext, CallResult, CallStatusResult
from app.services.vapi_provider import VapiProvider
from app.services.mock_provider import MockVoiceProvider
from app.services.extraction_provider import ExtractionProvider, ExtractionError
from app.services.openai_extractor import OpenAIExtractor
from app.services.anthropic_extractor import AnthropicExtractor
from app.services.extraction_factory import get_extraction_provider
from app.services.prompt_manager import ExtractionPromptManager, PromptVersion
from app.services.ai_service import AIService
from app.services.call_service import CallService

__all__ = [
    # Voice Calling
    "VoiceProvider",
    "CallContext",
    "CallResult",
    "CallStatusResult",
    "VapiProvider",
    "MockVoiceProvider",
    "CallService",
    # AI Extraction
    "ExtractionProvider",
    "ExtractionError",
    "OpenAIExtractor",
    "AnthropicExtractor",
    "get_extraction_provider",
    "ExtractionPromptManager",
    "PromptVersion",
    "AIService",
]
