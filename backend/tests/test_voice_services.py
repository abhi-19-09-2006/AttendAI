"""
Unit tests for voice calling services.
"""
import pytest
from datetime import datetime
from app.services.mock_provider import MockVoiceProvider
from app.services.voice_provider import CallContext


@pytest.mark.asyncio
async def test_mock_provider_create_call():
    """Test creating a call with mock provider."""
    provider = MockVoiceProvider()

    context = CallContext(
        phone_number="+1234567890",
        student_name="John Smith",
        absence_date="2026-09-12",
        correlation_id="test-call-123"
    )

    result = await provider.create_call(context)

    assert result.provider_call_id.startswith("mock_")
    assert result.status == "calling"
    assert result.initiated_at is not None
    assert result.metadata["mock"] is True


@pytest.mark.asyncio
async def test_mock_provider_simulate_answer():
    """Test simulating answered call."""
    provider = MockVoiceProvider()

    context = CallContext(
        phone_number="+1234567890",
        student_name="Jane Doe",
        absence_date="2026-09-12",
        correlation_id="test-call-456"
    )

    result = await provider.create_call(context)
    call_id = result.provider_call_id

    # Simulate call being answered
    transcript = "ASSISTANT: Hello, this is the attendance assistant...\nUSER: Hi, this is Jane's mom..."
    provider.simulate_answer(call_id, transcript)

    # Check status
    status = await provider.get_call_status(call_id)
    assert status.status == "completed"
    assert status.transcript == transcript
    assert status.ended_at is not None
    assert status.duration_seconds > 0


@pytest.mark.asyncio
async def test_mock_provider_simulate_no_answer():
    """Test simulating no answer."""
    provider = MockVoiceProvider()

    context = CallContext(
        phone_number="+1234567890",
        student_name="Bob Johnson",
        absence_date="2026-09-12",
        correlation_id="test-call-789"
    )

    result = await provider.create_call(context)
    call_id = result.provider_call_id

    # Simulate no answer
    provider.simulate_no_answer(call_id)

    # Check status
    status = await provider.get_call_status(call_id)
    assert status.status == "no-answer"
    assert status.transcript is None


@pytest.mark.asyncio
async def test_mock_provider_cancel_call():
    """Test cancelling a call."""
    provider = MockVoiceProvider()

    context = CallContext(
        phone_number="+1234567890",
        student_name="Alice Brown",
        absence_date="2026-09-12",
        correlation_id="test-call-999"
    )

    result = await provider.create_call(context)
    call_id = result.provider_call_id

    # Cancel call
    cancelled = await provider.cancel_call(call_id)
    assert cancelled is True

    # Check status
    status = await provider.get_call_status(call_id)
    assert status.status == "cancelled"


@pytest.mark.asyncio
async def test_mock_provider_parse_webhook():
    """Test parsing webhook payload."""
    provider = MockVoiceProvider()

    payload = {
        "correlation_id": "test-call-123",
        "call_id": "mock_abc123",
        "status": "completed",
        "event_type": "call.ended",
        "transcript": "Test transcript",
        "duration": 120
    }

    parsed = provider.parse_webhook_payload(payload)

    assert parsed["correlation_id"] == "test-call-123"
    assert parsed["provider_call_id"] == "mock_abc123"
    assert parsed["status"] == "completed"
    assert parsed["event_type"] == "call.ended"
    assert parsed["transcript"] == "Test transcript"


# ============================================================================
# Vapi Provider Regression Tests
# ============================================================================


def test_phone_normalization_indian_10_digit():
    """Test Indian 10-digit number becomes E.164 with +91."""
    from app.services.vapi_provider import normalize_phone_to_e164
    
    # 10-digit Indian number
    result = normalize_phone_to_e164("9876543210")
    assert result == "+919876543210"
    
    # With leading 0
    result = normalize_phone_to_e164("09876543210")
    assert result == "+919876543210"


def test_phone_normalization_already_e164():
    """Test already-E.164 numbers are preserved."""
    from app.services.vapi_provider import normalize_phone_to_e164
    
    # Already E.164 Indian
    result = normalize_phone_to_e164("+919876543210")
    assert result == "+919876543210"
    
    # Already E.164 US
    result = normalize_phone_to_e164("+14155552671")
    assert result == "+14155552671"


def test_phone_normalization_invalid():
    """Test invalid phone numbers raise ValueError."""
    from app.services.vapi_provider import normalize_phone_to_e164
    
    # Too short
    with pytest.raises(ValueError):
        normalize_phone_to_e164("123")
    
    # Empty
    with pytest.raises(ValueError):
        normalize_phone_to_e164("")


@pytest.mark.asyncio
async def test_vapi_payload_no_top_level_system_prompt():
    """Verify Vapi payload does NOT contain assistant.systemPrompt (Vapi 400 error)."""
    from unittest.mock import AsyncMock, patch
    from app.services.vapi_provider import VapiProvider
    from app.services.voice_provider import CallContext
    
    provider = VapiProvider()
    
    context = CallContext(
        phone_number="+919876543210",
        student_name="Test Student",
        absence_date="2026-09-22",
        correlation_id="test-call-123"
    )
    
    # Build assistant config
    assistant_config = provider._build_assistant_config(context)
    
    # Verify NO top-level systemPrompt
    assert "systemPrompt" not in assistant_config, \
        "assistant.systemPrompt should not exist (Vapi 400 error)"


@pytest.mark.asyncio
async def test_vapi_payload_system_prompt_in_model_messages():
    """Verify system prompt is in assistant.model.messages as system message."""
    from app.services.vapi_provider import VapiProvider
    from app.services.voice_provider import CallContext
    
    provider = VapiProvider()
    
    context = CallContext(
        phone_number="+919876543210",
        student_name="Test Student",
        absence_date="2026-09-22",
        correlation_id="test-call-123"
    )
    
    # Build assistant config
    assistant_config = provider._build_assistant_config(context)
    
    # Verify system prompt is in model.messages
    assert "model" in assistant_config
    assert "messages" in assistant_config["model"]
    
    messages = assistant_config["model"]["messages"]
    assert len(messages) > 0
    
    # Find system message
    system_messages = [m for m in messages if m["role"] == "system"]
    assert len(system_messages) == 1, "Should have exactly one system message"
    
    system_msg = system_messages[0]
    assert "content" in system_msg
    assert "Test Student" in system_msg["content"]
    assert "2026-09-22" in system_msg["content"]


@pytest.mark.asyncio
async def test_vapi_create_call_normalizes_phone():
    """Verify create_call normalizes phone number to E.164."""
    from unittest.mock import AsyncMock, patch, MagicMock
    from app.services.vapi_provider import VapiProvider
    from app.services.voice_provider import CallContext
    
    provider = VapiProvider()
    
    context = CallContext(
        phone_number="9876543210",  # Indian 10-digit, no +91
        student_name="Test Student",
        absence_date="2026-09-22",
        correlation_id="test-call-123"
    )
    
    # Mock httpx.AsyncClient
    with patch('app.services.vapi_provider.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "vapi_call_123",
            "status": "queued"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock()
        
        mock_client.return_value = mock_client_instance
        
        # Create call
        result = await provider.create_call(context)
        
        # Verify httpx.post was called
        assert mock_client_instance.post.called
        
        # Get the payload that was sent
        call_args = mock_client_instance.post.call_args
        payload = call_args[1]['json']
        
        # Verify phone was normalized to E.164
        assert payload['customer']['number'] == "+919876543210", \
            "Phone should be normalized to E.164 format"
        
        # Verify no top-level systemPrompt
        assert 'systemPrompt' not in payload['assistant'], \
            "assistant.systemPrompt should not exist"
        
        # Verify system prompt is in model.messages
        assert 'messages' in payload['assistant']['model']
        system_msgs = [m for m in payload['assistant']['model']['messages'] if m['role'] == 'system']
        assert len(system_msgs) == 1


# ============================================================================
# VoiceLink SIP Integration Tests
# ============================================================================


def test_voicelink_config_variables():
    """Verify VoiceLink SIP configuration variables are available."""
    from app.core.config import settings
    
    # These should be defined in config.py (even if empty)
    assert hasattr(settings, 'VOICELINK_SIP_GATEWAY_IP')
    assert hasattr(settings, 'VOICELINK_SIP_PORT')
    assert hasattr(settings, 'VOICELINK_SIP_USERNAME')
    assert hasattr(settings, 'VOICELINK_SIP_PASSWORD')
    assert hasattr(settings, 'VOICELINK_PHONE_NUMBER')
    assert hasattr(settings, 'VOICELINK_SIP_TRUNK_NAME')
    
    # Port should default to 5060
    assert settings.VOICELINK_SIP_PORT == 5060 or isinstance(settings.VOICELINK_SIP_PORT, int)


def test_voicelink_phone_number_format():
    """Verify VoiceLink phone number is in E.164 format if set."""
    from app.core.config import settings
    
    if settings.VOICELINK_PHONE_NUMBER:
        # Should start with + (E.164 format)
        assert settings.VOICELINK_PHONE_NUMBER.startswith('+'), \
            f"VOICELINK_PHONE_NUMBER should be in E.164 format (+91...), got: {settings.VOICELINK_PHONE_NUMBER}"
        
        # Should be at least 12 characters (+91 + 10 digits)
        assert len(settings.VOICELINK_PHONE_NUMBER) >= 12, \
            f"VOICELINK_PHONE_NUMBER too short: {settings.VOICELINK_PHONE_NUMBER}"


@pytest.mark.asyncio
async def test_vapi_uses_phone_number_id():
    """Verify VapiProvider uses VAPI_PHONE_NUMBER_ID in call payload."""
    from unittest.mock import AsyncMock, patch, MagicMock
    from app.services.vapi_provider import VapiProvider
    from app.services.voice_provider import CallContext
    from app.core.config import settings
    
    provider = VapiProvider()
    
    # Verify provider reads phone_number_id from settings
    assert provider.phone_number_id == settings.VAPI_PHONE_NUMBER_ID
    
    context = CallContext(
        phone_number="+919876543210",
        student_name="Test Student",
        absence_date="2026-09-23",
        correlation_id="test-call-voicelink"
    )
    
    # Mock httpx.AsyncClient
    with patch('app.services.vapi_provider.httpx.AsyncClient') as mock_client:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "id": "vapi_call_voicelink_123",
            "status": "queued"
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock()
        
        mock_client.return_value = mock_client_instance
        
        # Create call
        result = await provider.create_call(context)
        
        # Get the payload that was sent
        call_args = mock_client_instance.post.call_args
        payload = call_args[1]['json']
        
        # Verify phoneNumberId is used (this is what Vapi uses to route through SIP trunk)
        assert payload['phoneNumberId'] == settings.VAPI_PHONE_NUMBER_ID, \
            "Call payload must use VAPI_PHONE_NUMBER_ID (VoiceLink or Vapi number)"
        
        # Verify customer number is normalized
        assert payload['customer']['number'] == "+919876543210"
