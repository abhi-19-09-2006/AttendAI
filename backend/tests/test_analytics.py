"""
Phase 11 tests — Analytics & Reports.

Tests the AnalyticsService aggregation queries and the /api/analytics endpoints.
Uses the shared seeded database (3 users + 1 student from conftest).
"""
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import (
    User, Student, Parent, Attendance, Call, AbsenceReport, FollowUp,
    UserRole, AttendanceStatus, CallStatus, AbsenceCategory,
    FollowUpType, FollowUpPriority, FollowUpStatus, ParentRelationship, ContactMethod,
)
from app.services.analytics_service import AnalyticsService


# ── Fixtures ────────────────────────────────────────────────────────────────

REPORT_DATE = date(2026, 9, 15)


@pytest.fixture
async def analytics_data(db_session: AsyncSession):
    """
    Seed attendance, calls, reports, and follow-ups for analytics testing.
    Creates a deterministic dataset for a known date range.
    """
    # Get the seeded student
    result = await db_session.execute(
        select(Student).where(Student.student_id == "AUTHSEED001")
    )
    student = result.scalar_one()

    # Get the seeded faculty user
    result = await db_session.execute(
        select(User).where(User.email == "faculty@attendai.example.com")
    )
    faculty = result.scalar_one()

    # Create a parent for the student
    parent = Parent(
        student_id=student.id,
        relationship=ParentRelationship.MOTHER,
        first_name="Test",
        last_name="Mom",
        primary_phone="+1555000111",
        preferred_contact_method=ContactMethod.PHONE,
        preferred_language="en",
        is_primary_contact=True,
    )
    db_session.add(parent)
    await db_session.flush()

    # Create 5 days of attendance + calls
    entries = []
    for i in range(5):
        d = REPORT_DATE - timedelta(days=i)

        att = Attendance(
            student_id=student.id,
            date=d,
            status=AttendanceStatus.ABSENT,
            recorded_by=faculty.id,
        )
        db_session.add(att)
        await db_session.flush()

        # Vary call statuses: 3 completed, 1 no_answer, 1 unreachable
        if i < 3:
            call_status = CallStatus.COMPLETED
            duration = 120 + i * 30
        elif i == 3:
            call_status = CallStatus.NO_ANSWER
            duration = None
        else:
            call_status = CallStatus.UNREACHABLE
            duration = None

        call = Call(
            student_id=student.id,
            parent_id=parent.id,
            attendance_id=att.id,
            status=call_status,
            phone_number_called=parent.primary_phone,
            retry_count=2 if call_status == CallStatus.UNREACHABLE else 0,
            max_retries=3,
            duration_seconds=duration,
        )
        db_session.add(call)
        await db_session.flush()

        entries.append({"attendance": att, "call": call, "date": d})

        # Create absence reports for completed calls
        if call_status == CallStatus.COMPLETED:
            categories = [AbsenceCategory.MEDICAL, AbsenceCategory.FAMILY, AbsenceCategory.PERSONAL]
            report = AbsenceReport(
                call_id=call.id,
                student_id=student.id,
                attendance_id=att.id,
                reason="Test reason",
                category=categories[i],
                parent_confirmed=True,
                follow_up_required=(i == 0),
                confidence_score=0.9 if i > 0 else 0.6,
            )
            db_session.add(report)
            await db_session.flush()

            if i == 0:
                fu = FollowUp(
                    student_id=student.id,
                    absence_report_id=report.id,
                    call_id=call.id,
                    type=FollowUpType.LOW_CONFIDENCE,
                    priority=FollowUpPriority.HIGH,
                    status=FollowUpStatus.PENDING,
                    description="Low confidence test",
                )
                db_session.add(fu)

    await db_session.commit()
    return entries


# ── Service Tests ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_summary_counts(db_session: AsyncSession, analytics_data):
    """Summary returns correct absentee, call, and follow-up counts."""
    svc = AnalyticsService(db_session)
    start = REPORT_DATE - timedelta(days=4)
    result = await svc.get_summary(start, REPORT_DATE)

    assert result["total_absentees"] == 5
    assert result["total_calls"] == 5
    assert result["completed_calls"] == 3
    assert result["no_answer_calls"] == 1
    assert result["unreachable_calls"] == 1
    assert result["total_followups"] == 1
    assert result["pending_followups"] == 1


@pytest.mark.asyncio
async def test_summary_rates(db_session: AsyncSession, analytics_data):
    """Summary calculates correct answer/failure rates."""
    svc = AnalyticsService(db_session)
    start = REPORT_DATE - timedelta(days=4)
    result = await svc.get_summary(start, REPORT_DATE)

    # 3 completed out of 5 = 60%
    assert result["answer_rate"] == 60.0
    # 1 no_answer out of 5 = 20%
    assert result["no_answer_rate"] == 20.0


@pytest.mark.asyncio
async def test_summary_average_duration(db_session: AsyncSession, analytics_data):
    """Average duration is computed from completed calls only."""
    svc = AnalyticsService(db_session)
    start = REPORT_DATE - timedelta(days=4)
    result = await svc.get_summary(start, REPORT_DATE)

    # Durations: 120, 150, 180 → avg = 150
    assert result["average_duration_seconds"] == 150.0


@pytest.mark.asyncio
async def test_daily_trends(db_session: AsyncSession, analytics_data):
    """Daily trends returns one row per day with attendance data."""
    svc = AnalyticsService(db_session)
    start = REPORT_DATE - timedelta(days=4)
    trends = await svc.get_daily_trends(start, REPORT_DATE)

    assert len(trends) == 5
    for t in trends:
        assert t["absentees"] == 1
        assert t["calls"] == 1


@pytest.mark.asyncio
async def test_call_metrics(db_session: AsyncSession, analytics_data):
    """Call metrics include status distribution, rates, retry rate."""
    svc = AnalyticsService(db_session)
    start = REPORT_DATE - timedelta(days=4)
    metrics = await svc.get_call_metrics(start, REPORT_DATE)

    assert metrics["total_calls"] == 5
    assert metrics["completion_rate"] == 60.0
    assert metrics["answer_rate"] == 60.0
    assert "completed" in metrics["status_distribution"]
    assert metrics["status_distribution"]["completed"] == 3
    # 1 unreachable call had retry_count=2
    assert metrics["retry_rate"] == 20.0


@pytest.mark.asyncio
async def test_absence_reason_distribution(db_session: AsyncSession, analytics_data):
    """Reason distribution groups by category correctly."""
    svc = AnalyticsService(db_session)
    start = REPORT_DATE - timedelta(days=4)
    dist = await svc.get_absence_reason_distribution(start, REPORT_DATE)

    categories = {d["category"]: d["count"] for d in dist}
    assert categories.get("medical") == 1
    assert categories.get("family") == 1
    assert categories.get("personal") == 1


@pytest.mark.asyncio
async def test_daily_report(db_session: AsyncSession, analytics_data):
    """Daily report composes summary + reasons for a single date."""
    svc = AnalyticsService(db_session)
    report = await svc.get_daily_report(REPORT_DATE)

    assert report["report_type"] == "daily"
    assert report["report_date"] == REPORT_DATE.isoformat()
    assert report["summary"]["total_absentees"] == 1
    assert "absence_reasons" in report


@pytest.mark.asyncio
async def test_weekly_report(db_session: AsyncSession, analytics_data):
    """Weekly report covers 7-day window."""
    svc = AnalyticsService(db_session)
    report = await svc.get_weekly_report(REPORT_DATE)

    assert report["report_type"] == "weekly"
    assert len(report["daily_trends"]) == 5  # only 5 days have data
    assert "call_metrics" in report


@pytest.mark.asyncio
async def test_followup_report(db_session: AsyncSession, analytics_data):
    """Follow-up report groups by type, priority, status."""
    svc = AnalyticsService(db_session)
    start = REPORT_DATE - timedelta(days=4)
    report = await svc.get_followup_report(start, REPORT_DATE)

    assert report["report_type"] == "followup"
    assert report["total"] == 1
    assert report["by_type"]["low_confidence"] == 1
    assert report["by_priority"]["high"] == 1
    assert report["by_status"]["pending"] == 1


@pytest.mark.asyncio
async def test_unreachable_report(db_session: AsyncSession, analytics_data):
    """Unreachable report lists calls that exhausted retries."""
    svc = AnalyticsService(db_session)
    start = REPORT_DATE - timedelta(days=4)
    report = await svc.get_unreachable_report(start, REPORT_DATE)

    assert report["report_type"] == "unreachable"
    assert report["total"] == 1
    assert report["entries"][0]["retry_count"] == 2


@pytest.mark.asyncio
async def test_summary_empty_range(db_session: AsyncSession, analytics_data):
    """Summary for a date range with no data returns zeros."""
    svc = AnalyticsService(db_session)
    far_past = date(2020, 1, 1)
    result = await svc.get_summary(far_past, far_past)

    assert result["total_absentees"] == 0
    assert result["total_calls"] == 0
    assert result["answer_rate"] == 0.0
    assert result["average_duration_seconds"] is None


# ── API Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_analytics_summary_requires_auth(client):
    """Summary endpoint requires authentication."""
    resp = client.get("/api/analytics/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_analytics_summary_authenticated(client, analytics_data):
    """Authenticated faculty can access summary."""
    # Login as faculty
    login = client.post("/api/auth/login", json={
        "email": "faculty@attendai.example.com",
        "password": "faculty123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    start = (REPORT_DATE - timedelta(days=4)).isoformat()
    end = REPORT_DATE.isoformat()
    resp = client.get(
        f"/api/analytics/summary?date_from={start}&date_to={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_absentees"] == 5
    assert data["completed_calls"] == 3


@pytest.mark.asyncio
async def test_analytics_call_metrics_endpoint(client, analytics_data):
    """Call metrics endpoint returns correct data."""
    login = client.post("/api/auth/login", json={
        "email": "faculty@attendai.example.com",
        "password": "faculty123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    start = (REPORT_DATE - timedelta(days=4)).isoformat()
    end = REPORT_DATE.isoformat()
    resp = client.get(
        f"/api/analytics/call-metrics?date_from={start}&date_to={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 5
    assert data["completion_rate"] == 60.0


@pytest.mark.asyncio
async def test_analytics_trends_endpoint(client, analytics_data):
    """Trends endpoint returns daily breakdown."""
    login = client.post("/api/auth/login", json={
        "email": "faculty@attendai.example.com",
        "password": "faculty123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    start = (REPORT_DATE - timedelta(days=4)).isoformat()
    end = REPORT_DATE.isoformat()
    resp = client.get(
        f"/api/analytics/trends?date_from={start}&date_to={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_analytics_reports_daily_endpoint(client, analytics_data):
    """Daily report endpoint works."""
    login = client.post("/api/auth/login", json={
        "email": "faculty@attendai.example.com",
        "password": "faculty123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get(
        f"/api/analytics/reports/daily?report_date={REPORT_DATE.isoformat()}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["report_type"] == "daily"


@pytest.mark.asyncio
async def test_analytics_reports_unreachable_endpoint(client, analytics_data):
    """Unreachable report endpoint works."""
    login = client.post("/api/auth/login", json={
        "email": "faculty@attendai.example.com",
        "password": "faculty123",
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    start = (REPORT_DATE - timedelta(days=4)).isoformat()
    end = REPORT_DATE.isoformat()
    resp = client.get(
        f"/api/analytics/reports/unreachable?date_from={start}&date_to={end}",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "unreachable"
    assert data["total"] == 1
