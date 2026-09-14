"""
Test database models and relationships.
"""
import pytest
from datetime import date, datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    Student,
    Parent,
    Attendance,
    Call,
    CallCampaign,
    AbsenceReport,
    FollowUp,
    UserRole,
    AttendanceStatus,
    CallStatus,
    CampaignStatus,
    ParentRelationship,
    AbsenceCategory,
)


@pytest.mark.asyncio
async def test_user_creation(db_session: AsyncSession):
    """Test user model creation."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        role=UserRole.FACULTY,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    saved_user = result.scalar_one()

    assert saved_user.email == "test@example.com"
    assert saved_user.full_name == "Test User"
    assert saved_user.role == UserRole.FACULTY
    assert saved_user.is_active is True


from sqlalchemy.orm import selectinload

@pytest.mark.asyncio
async def test_student_parent_relationship(db_session: AsyncSession):
    """Test student-parent relationship."""
    student = Student(
        student_id="TEST001",
        first_name="Test",
        last_name="Student",
        date_of_birth=date(2010, 1, 1),
        grade_level=7,
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    parent = Parent(
        student_id=student.id,
        relationship=ParentRelationship.MOTHER,
        first_name="Test",
        last_name="Parent",
        primary_phone="+1234567890",
        is_primary_contact=True,
    )
    db_session.add(parent)
    await db_session.commit()

    result = await db_session.execute(
        select(Student)
        .options(selectinload(Student.parents))
        .where(Student.student_id == "TEST001")
    )
    saved_student = result.scalar_one()

    assert saved_student.full_name == "Test Student"
    assert len(saved_student.parents) == 1
    assert saved_student.parents[0].full_name == "Test Parent"


@pytest.mark.asyncio
async def test_attendance_record(db_session: AsyncSession):
    """Test attendance record creation."""
    user = User(
        email="faculty@test.com",
        hashed_password="hashed",
        full_name="Faculty User",
        role=UserRole.FACULTY,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    student = Student(
        student_id="TEST002",
        first_name="Test",
        last_name="Student2",
        date_of_birth=date(2010, 1, 1),
        grade_level=8,
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    attendance = Attendance(
        student_id=student.id,
        date=date.today(),
        status=AttendanceStatus.ABSENT,
        recorded_by=user.id,
        notes="Test absence",
    )
    db_session.add(attendance)
    await db_session.commit()

    result = await db_session.execute(
        select(Attendance).where(Attendance.student_id == student.id)
    )
    saved_attendance = result.scalar_one()

    assert saved_attendance.status == AttendanceStatus.ABSENT
    assert saved_attendance.notes == "Test absence"


@pytest.mark.asyncio
async def test_call_campaign_and_calls(db_session: AsyncSession):
    """Test call campaign and call records."""
    user = User(
        email="admin@test.com",
        hashed_password="hashed",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    student = Student(
        student_id="TEST003",
        first_name="Test",
        last_name="Student3",
        date_of_birth=date(2010, 1, 1),
        grade_level=9,
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    parent = Parent(
        student_id=student.id,
        relationship=ParentRelationship.FATHER,
        first_name="Test",
        last_name="Parent",
        primary_phone="+1234567890",
        is_primary_contact=True,
    )
    db_session.add(parent)
    await db_session.flush()

    attendance = Attendance(
        student_id=student.id,
        date=date.today(),
        status=AttendanceStatus.ABSENT,
        recorded_by=user.id,
    )
    db_session.add(attendance)
    await db_session.flush()

    campaign = CallCampaign(
        name="Test Campaign",
        description="Test Description",
        status=CampaignStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(campaign)
    await db_session.flush()

    call = Call(
        campaign_id=campaign.id,
        student_id=student.id,
        parent_id=parent.id,
        attendance_id=attendance.id,
        status=CallStatus.PENDING,
        phone_number_called=parent.primary_phone,
        retry_count=0,
        max_retries=3,
    )
    db_session.add(call)
    await db_session.commit()

    result = await db_session.execute(
        select(Call).where(Call.student_id == student.id)
    )
    saved_call = result.scalar_one()

    assert saved_call.status == CallStatus.PENDING
    assert saved_call.phone_number_called == "+1234567890"
    assert saved_call.retry_count == 0


@pytest.mark.asyncio
async def test_absence_report_creation(db_session: AsyncSession):
    """Test absence report with confidence score."""
    user = User(
        email="faculty2@test.com",
        hashed_password="hashed",
        full_name="Faculty User",
        role=UserRole.FACULTY,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    student = Student(
        student_id="TEST004",
        first_name="Test",
        last_name="Student4",
        date_of_birth=date(2010, 1, 1),
        grade_level=7,
        is_active=True,
    )
    db_session.add(student)
    await db_session.flush()

    parent = Parent(
        student_id=student.id,
        relationship=ParentRelationship.MOTHER,
        first_name="Test",
        last_name="Parent",
        primary_phone="+1234567890",
        is_primary_contact=True,
    )
    db_session.add(parent)
    await db_session.flush()

    attendance = Attendance(
        student_id=student.id,
        date=date.today(),
        status=AttendanceStatus.ABSENT,
        recorded_by=user.id,
    )
    db_session.add(attendance)
    await db_session.flush()

    call = Call(
        student_id=student.id,
        parent_id=parent.id,
        attendance_id=attendance.id,
        status=CallStatus.COMPLETED,
        phone_number_called=parent.primary_phone,
        retry_count=0,
        max_retries=3,
    )
    db_session.add(call)
    await db_session.flush()

    report = AbsenceReport(
        call_id=call.id,
        student_id=student.id,
        attendance_id=attendance.id,
        reason="Student has fever",
        category=AbsenceCategory.MEDICAL,
        duration="1 day",
        expected_return_date=date.today(),
        parent_confirmed=True,
        follow_up_required=False,
        confidence_score=0.95,
    )
    db_session.add(report)
    await db_session.commit()

    result = await db_session.execute(
        select(AbsenceReport).where(AbsenceReport.call_id == call.id)
    )
    saved_report = result.scalar_one()

    assert saved_report.category == AbsenceCategory.MEDICAL
    assert saved_report.confidence_score == 0.95
    assert saved_report.parent_confirmed is True
