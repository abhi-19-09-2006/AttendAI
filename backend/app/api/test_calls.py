"""
Test call endpoint for single test calls.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.auth import require_faculty
from app.models import User, Call, Student, Parent, Attendance, AbsenceReport
from app.services.call_service import CallService
from app.core.logging import get_logger

logger = get_logger("test_calls")
router = APIRouter()


class TestCallRequest(BaseModel):
    """Request to make a test call."""
    attendance_id: str


class TestCallResponse(BaseModel):
    """Response from test call."""
    call_id: str
    provider_call_id: str
    status: str
    message: str


@router.post("/test-call", response_model=TestCallResponse)
async def create_test_call(
    request: TestCallRequest,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a single test call for an absence.

    This endpoint is for testing the voice calling integration with a single call
    before enabling mass calling campaigns.

    - **attendance_id**: ID of the attendance record to call about
    """
    # Get attendance record
    attendance = await db.get(Attendance, request.attendance_id)
    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    # Verify it's an absence
    if attendance.status != "absent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only create calls for absences"
        )

    # Check if call already exists
    from sqlalchemy import select
    existing = await db.execute(
        select(Call).where(Call.attendance_id == attendance.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call already exists for this attendance record"
        )

    # Get student
    student = await db.get(Student, attendance.student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Get primary parent
    from sqlalchemy import and_
    parent_query = select(Parent).where(
        and_(
            Parent.student_id == student.id,
            Parent.is_primary_contact == True
        )
    )
    parent_result = await db.execute(parent_query)
    parent = parent_result.scalar_one_or_none()

    if not parent:
        # Get any parent
        parent_query = select(Parent).where(Parent.student_id == student.id).limit(1)
        parent_result = await db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No parent contact found for student"
        )

    # Create call record
    call = Call(
        student_id=student.id,
        parent_id=parent.id,
        attendance_id=attendance.id,
        status="pending",
        phone_number_called=parent.primary_phone,
        retry_count=0,
        max_retries=1  # Only 1 attempt for test calls
    )

    db.add(call)
    await db.flush()
    await db.refresh(call)
    await db.commit()

    # Initiate the call
    call_service = CallService(db)
    success = await call_service.initiate_call(call.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate call"
        )

    # Refresh to get updated data
    await db.refresh(call)

    logger.info(
        f"Test call created by {current_user.email}: "
        f"Call {call.id} for {student.first_name} {student.last_name}"
    )

    return TestCallResponse(
        call_id=call.id,
        provider_call_id=call.vapi_call_id,
        status=call.status.value,
        message=f"Test call initiated to {parent.primary_phone} for {student.first_name} {student.last_name}"
    )


@router.get("/test-call/{call_id}")
async def get_test_call_status(
    call_id: str,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the status of a test call.

    - **call_id**: ID of the call to check
    """
    call = await db.get(Call, call_id)
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    # Get related data
    student = await db.get(Student, call.student_id)

    # Get absence report if exists
    from sqlalchemy import select
    report_query = select(AbsenceReport).where(AbsenceReport.call_id == call.id)
    report_result = await db.execute(report_query)
    report = report_result.scalar_one_or_none()

    response = {
        "call_id": call.id,
        "provider_call_id": call.vapi_call_id,
        "status": call.status.value,
        "student_name": f"{student.first_name} {student.last_name}" if student else None,
        "phone_number": call.phone_number_called,
        "initiated_at": call.initiated_at.isoformat() if call.initiated_at else None,
        "answered_at": call.answered_at.isoformat() if call.answered_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "duration_seconds": call.duration_seconds,
        "absence_report": None
    }

    if report:
        response["absence_report"] = {
            "reason": report.reason,
            "category": report.category.value,
            "confidence_score": report.confidence_score,
            "parent_confirmed": report.parent_confirmed,
            "follow_up_required": report.follow_up_required
        }

    return response
