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
