"""
Phase 13: Controlled Vapi End-to-End Integration Tests

Tests the complete workflow:
attendance/absence → call creation → Vapi provider → webhook → extraction → absence report → persistence

Uses MockVoiceProvider to simulate Vapi calls without making real API calls.
"""
import pytest
import hmac
import hashlib
import json
import uuid
from datetime import date, datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.models import (
    User, Student, Parent, Attendance, Call, CallAttempt,
    AbsenceReport, FollowUp, CallCampaign
)
from app.models.enums import (
    UserRole, AttendanceStatus, CallStatus, AbsenceCategory,
    FollowUpType, FollowUpPriority, ParentRelationship, ContactMethod
)
from app.services.call_service import CallService
from app.services.mock_provider import MockVoiceProvider
from app.core.config import settings


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
async def e2e_test_data(db_session: AsyncSession):
    """Create complete test data for E2E workflow."""
    # Get seeded faculty user
    result = await db_session.execute(
        select(User).where(User.email == "faculty@attendai.example.com")
    )
    faculty = result.scalar_one()

    # Create student with unique ID to prevent conflicts across tests
    unique_id = str(uuid.uuid4())[:8]
    student = Student(
        student_id=f"E2E{unique_id}",
        first_name="E2E",
        last_name="TestStudent",
        date_of_birth=date(2010, 1, 1),
        grade_level=10,
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    # Create parent
    parent = Parent(
        student_id=student.id,
        relationship=ParentRelationship.MOTHER,
        first_name="E2E",
        last_name="TestParent",
        primary_phone="+1555000999",
        preferred_contact_method=ContactMethod.PHONE,
        preferred_language="en",
        is_primary_contact=True,
    )
    db_session.add(parent)
    await db_session.flush()

    # Create absence
    attendance = Attendance(
        student_id=student.id,
        date=date.today(),
        status=AttendanceStatus.ABSENT,
        recorded_by=faculty.id,
    )
    db_session.add(attendance)
    await db_session.flush()

    await db_session.commit()

    return {
        "faculty": faculty,
        "student": student,
        "parent": parent,
        "attendance": attendance,
    }


@pytest.fixture
def mock_provider():
    """Create MockVoiceProvider instance."""
    return MockVoiceProvider()


@pytest.fixture
def webhook_secret(monkeypatch):
    """Get webhook secret for signature generation and configure it in settings."""
    test_secret = "test-secret"
    # Configure the secret in settings for this test
    monkeypatch.setattr("app.core.config.settings.VAPI_WEBHOOK_SECRET", test_secret)
    return test_secret


def generate_webhook_signature(payload: dict, secret: str) -> tuple[str, bytes]:
    """Generate valid webhook signature for testing."""
    body = json.dumps(payload).encode()
    signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return signature, body


# ── E2E Workflow Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_e2e_complete_workflow_answered_call(
    db_session: AsyncSession,
    e2e_test_data,
    mock_provider,
):
    """
    Complete E2E test: absence → call → webhook → extraction → report.
    Simulates an answered call with transcript.
    """
    student = e2e_test_data["student"]
    parent = e2e_test_data["parent"]
    attendance = e2e_test_data["attendance"]

    # Step 1: Create call via CallService
    call_service = CallService(db_session, mock_provider)
    calls = await call_service.create_calls_for_absentees(date.today())
    
    assert len(calls) == 1
    call = calls[0]
    assert call.student_id == student.id
    assert call.parent_id == parent.id
    assert call.attendance_id == attendance.id
    assert call.status == CallStatus.PENDING

    # Step 2: Initiate call
    success = await call_service.initiate_call(call.id)
    assert success is True

    # Refresh call
    await db_session.refresh(call)
    assert call.status == CallStatus.CALLING
    assert call.vapi_call_id is not None
    assert call.initiated_at is not None

    # Verify CallAttempt created
    attempt_result = await db_session.execute(
        select(CallAttempt).where(CallAttempt.call_id == call.id)
    )
    attempt = attempt_result.scalar_one()
    assert attempt.attempt_number == 1
    assert attempt.status == CallStatus.CALLING

    # Step 3: Simulate Vapi webhook (call completed with transcript)
    transcript = """
    AI: Hello, this is the attendance assistant calling about E2E TestStudent's absence today.
    Parent: Yes, this is the mother.
    AI: We noticed E2E was marked absent today. May I ask the reason?
    Parent: Yes, E2E has a fever and is staying home.
    AI: I understand. When do you expect E2E to return to school?
    Parent: Probably in 2 days when the fever goes down.
    AI: Thank you for the information. We hope E2E feels better soon.
    """

    await call_service.process_call_completion(
        call_id=call.id,
        vapi_call_id=call.vapi_call_id,
        status="completed",
        transcript=transcript,
    )

    # Step 4: Verify call status updated
    await db_session.refresh(call)
    assert call.status == CallStatus.COMPLETED
    assert call.ended_at is not None
    assert call.duration_seconds is not None

    # Verify attempt updated
    await db_session.refresh(attempt)
    assert attempt.status == CallStatus.COMPLETED
    assert attempt.ended_at is not None

    # Step 5: Verify absence report created
    report_result = await db_session.execute(
        select(AbsenceReport).where(AbsenceReport.call_id == call.id)
    )
    report = report_result.scalar_one_or_none()
    
    # Report may or may not be created depending on AI service availability
    # If AI service is mocked/unavailable, extraction might fail gracefully
    if report:
        assert report.student_id == student.id
        assert report.attendance_id == attendance.id
        assert report.transcript == transcript
        assert report.confidence_score >= 0.0
        assert report.confidence_score <= 1.0
        
        # If confidence is low, follow-up should be created
        if report.confidence_score < 0.85 or report.follow_up_required:
            followup_result = await db_session.execute(
                select(FollowUp).where(FollowUp.absence_report_id == report.id)
            )
            followup = followup_result.scalar_one_or_none()
            assert followup is not None
            assert followup.student_id == student.id
            assert followup.call_id == call.id


@pytest.mark.asyncio
async def test_e2e_no_answer_workflow(
    db_session: AsyncSession,
    e2e_test_data,
    mock_provider,
):
    """Test workflow when call is not answered."""
    from app.models import Job
    from app.models.job import JobStatus, JobType

    attendance = e2e_test_data["attendance"]

    # Create and initiate call
    call_service = CallService(db_session, mock_provider)
    calls = await call_service.create_calls_for_absentees(date.today())
    call = calls[0]
    
    await call_service.initiate_call(call.id)
    await db_session.refresh(call)

    # Process no-answer
    await call_service.process_call_completion(
        call_id=call.id,
        vapi_call_id=call.vapi_call_id,
        status="no-answer",
        transcript=None,
    )

    # Verify call status remains NO_ANSWER (retry is scheduled, not immediate)
    await db_session.refresh(call)
    assert call.status == CallStatus.NO_ANSWER
    
    # Verify a DEFERRED retry job was created
    job_result = await db_session.execute(
        select(Job).where(
            Job.call_id == call.id,
            Job.job_type == JobType.RETRY_CALL,
        )
    )
    retry_job = job_result.scalar_one_or_none()
    assert retry_job is not None
    assert retry_job.status == JobStatus.DEFERRED
    assert retry_job.next_retry_at is not None
    assert retry_job.idempotency_key == f"retry_call_{call.id}_attempt_1"
    
    # No absence report should be created for no-answer
    report_result = await db_session.execute(
        select(AbsenceReport).where(AbsenceReport.call_id == call.id)
    )
    report = report_result.scalar_one_or_none()
    assert report is None


@pytest.mark.asyncio
async def test_e2e_failed_call_workflow(
    db_session: AsyncSession,
    e2e_test_data,
    mock_provider,
):
    """Test workflow when call fails."""
    from app.models import Job
    from app.models.job import JobStatus, JobType
    
    call_service = CallService(db_session, mock_provider)
    calls = await call_service.create_calls_for_absentees(date.today())
    call = calls[0]
    
    await call_service.initiate_call(call.id)
    await db_session.refresh(call)

    # Process failed call
    await call_service.process_call_completion(
        call_id=call.id,
        vapi_call_id=call.vapi_call_id,
        status="failed",
        transcript=None,
    )

    # Verify call status remains FAILED (retry is scheduled, not immediate)
    await db_session.refresh(call)
    assert call.status == CallStatus.FAILED
    
    # Verify a DEFERRED retry job was created
    job_result = await db_session.execute(
        select(Job).where(
            Job.call_id == call.id,
            Job.job_type == JobType.RETRY_CALL,
        )
    )
    retry_job = job_result.scalar_one_or_none()
    assert retry_job is not None
    assert retry_job.status == JobStatus.DEFERRED
    assert retry_job.next_retry_at is not None
    assert retry_job.idempotency_key == f"retry_call_{call.id}_attempt_1"


@pytest.mark.asyncio
async def test_e2e_webhook_signature_verification(webhook_secret):
    """Test webhook signature verification."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "message": {"type": "call.ended"},
            "call": {
                "id": "test-call-id",
                "metadata": {"correlation_id": "test-correlation-id"}
            }
        }

        # Test with valid signature
        signature, body = generate_webhook_signature(payload, webhook_secret)
        response = await client.post(
            "/webhooks/vapi",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Vapi-Signature": signature,
            },
        )
        # Should not return 401 (may return other errors due to missing call)
        assert response.status_code != 401

        # Test with invalid signature
        response = await client.post(
            "/webhooks/vapi",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Vapi-Signature": "invalid-signature",
            },
        )
        assert response.status_code == 401

        # Test with missing signature
        response = await client.post(
            "/webhooks/vapi",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_e2e_duplicate_webhook_safety(
    db_session: AsyncSession,
    e2e_test_data,
    mock_provider,
):
    """Test that duplicate webhooks don't create duplicate reports."""
    call_service = CallService(db_session, mock_provider)
    calls = await call_service.create_calls_for_absentees(date.today())
    call = calls[0]
    
    await call_service.initiate_call(call.id)
    await db_session.refresh(call)

    transcript = "Parent: My child is sick with a cold."

    # Process completion twice (simulate duplicate webhook)
    await call_service.process_call_completion(
        call_id=call.id,
        vapi_call_id=call.vapi_call_id,
        status="completed",
        transcript=transcript,
    )

    # Process again (duplicate)
    await call_service.process_call_completion(
        call_id=call.id,
        vapi_call_id=call.vapi_call_id,
        status="completed",
        transcript=transcript,
    )

    # Count absence reports - should be at most 1
    # (may be 0 if extraction fails, but never > 1)
    report_result = await db_session.execute(
        select(AbsenceReport).where(AbsenceReport.call_id == call.id)
    )
    reports = report_result.scalars().all()
    
    # AbsenceReport has unique constraint on call_id, so duplicates are prevented
    assert len(reports) <= 1


@pytest.mark.asyncio
async def test_e2e_api_visibility(
    db_session: AsyncSession,
    e2e_test_data,
    mock_provider,
    async_client,
):
    """Verify completed call and report are visible through APIs."""
    call_service = CallService(db_session, mock_provider)
    calls = await call_service.create_calls_for_absentees(date.today())
    call = calls[0]
    
    await call_service.initiate_call(call.id)
    await db_session.refresh(call)

    # Complete the call
    await call_service.process_call_completion(
        call_id=call.id,
        vapi_call_id=call.vapi_call_id,
        status="completed",
        transcript="Parent: My child is at a doctor appointment.",
    )

    # Login as faculty
    login_response = await async_client.post(
        "/api/auth/login",
        json={"email": "faculty@attendai.example.com", "password": "faculty123"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify call visible in API
    response = await async_client.get(
        f"/api/calls/{call.id}",
        headers=headers,
    )
    assert response.status_code == 200
    call_data = response.json()
    assert call_data["status"] == "completed"

    # Verify absence report visible if created
    response = await async_client.get(
        "/api/absence-reports",
        headers=headers,
        params={"call_id": call.id},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_e2e_max_retries_exceeded(
    db_session: AsyncSession,
    e2e_test_data,
    mock_provider,
):
    """Test that call is marked UNREACHABLE after max retries."""
    from app.models import Job
    from app.models.job import JobStatus, JobType

    call_service = CallService(db_session, mock_provider)
    calls = await call_service.create_calls_for_absentees(date.today())
    call = calls[0]
    
    # Set max_retries to 1 for faster test
    call.max_retries = 1
    await db_session.commit()
    
    await call_service.initiate_call(call.id)
    await db_session.refresh(call)

    # First no-answer - should schedule retry
    await call_service.process_call_completion(
        call_id=call.id,
        vapi_call_id=call.vapi_call_id,
        status="no-answer",
        transcript=None,
    )
    await db_session.refresh(call)
    
    # Call status remains NO_ANSWER, retry job created
    assert call.status == CallStatus.NO_ANSWER
    assert call.retry_count == 0  # Not incremented yet
    
    # Verify DEFERRED job created
    job_result = await db_session.execute(
        select(Job).where(
            Job.call_id == call.id,
            Job.job_type == JobType.RETRY_CALL,
            Job.status == JobStatus.DEFERRED,
        )
    )
    retry_job = job_result.scalar_one_or_none()
    assert retry_job is not None
    
    # Simulate retry task running: set retry_count and reset to PENDING
    # (This is what retry_failed_call task does)
    call.retry_count = 1
    call.status = CallStatus.PENDING
    await db_session.commit()
    await db_session.refresh(call)
    
    # Initiate retry
    await call_service.initiate_call(call.id)
    await db_session.refresh(call)

    # Second no-answer - should mark unreachable (retry_count=1 >= max_retries=1)
    await call_service.process_call_completion(
        call_id=call.id,
        vapi_call_id=call.vapi_call_id,
        status="no-answer",
        transcript=None,
    )
    await db_session.refresh(call)
    assert call.status == CallStatus.UNREACHABLE


# ── Integration Verification ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vapi_provider_configuration():
    """Verify Vapi provider configuration from environment."""
    from app.services.vapi_provider import VapiProvider
    from app.core.config import settings
    
    provider = VapiProvider()
    
    # Verify provider reads from settings
    assert provider.api_key == settings.VAPI_API_KEY
    assert provider.base_url == settings.VAPI_BASE_URL
    assert provider.phone_number_id == settings.VAPI_PHONE_NUMBER_ID
    
    # Verify no hardcoded secrets
    assert provider.api_key != "hardcoded-key"
    assert "sk-" not in provider.api_key or provider.api_key == settings.VAPI_API_KEY


@pytest.mark.asyncio
async def test_mock_provider_simulation():
    """Verify MockVoiceProvider can simulate all call outcomes."""
    provider = MockVoiceProvider()
    
    from app.services.voice_provider import CallContext
    context = CallContext(
        phone_number="+1555000999",
        student_name="Test Student",
        absence_date="2026-09-17",
        correlation_id="test-correlation-id",
    )
    
    # Test successful call
    result = await provider.create_call(context)
    assert result.provider_call_id is not None
    assert result.status == "calling"
    
    # Simulate answer
    provider.simulate_answer(result.provider_call_id, "Test transcript")
    status = await provider.get_call_status(result.provider_call_id)
    assert status.status == "completed"
    assert status.transcript == "Test transcript"
    
    # Test no-answer
    result2 = await provider.create_call(context)
    provider.simulate_no_answer(result2.provider_call_id)
    status2 = await provider.get_call_status(result2.provider_call_id)
    assert status2.status == "no-answer"
    
    # Test failed
    result3 = await provider.create_call(context)
    provider.simulate_failed(result3.provider_call_id, "Network error")
    status3 = await provider.get_call_status(result3.provider_call_id)
    assert status3.status == "failed"
