"""
Attendance management router.
"""
from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.auth import require_faculty, get_current_user
from app.schemas import (
    AttendanceResponse,
    AttendanceCreate,
    AttendanceBulkCreate,
    AttendanceUpdate,
    AbsenteeResponse
)
from app.models import User, Attendance, Student, Call, AttendanceStatus, CallStatus

router = APIRouter()


@router.post("", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
async def create_attendance(
    attendance_data: AttendanceCreate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Record attendance for a student.

    - **student_id**: ID of the student
    - **date**: Date of attendance
    - **status**: Attendance status (present, absent, late, excused)
    - **period**: Optional period/class identifier
    """
    # Verify student exists
    result = await db.execute(select(Student).where(Student.id == attendance_data.student_id))
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Check for duplicate
    existing = await db.execute(
        select(Attendance).where(
            and_(
                Attendance.student_id == attendance_data.student_id,
                Attendance.date == attendance_data.date,
                Attendance.period == attendance_data.period
            )
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attendance already recorded for this student, date, and period"
        )

    attendance = Attendance(
        **attendance_data.model_dump(),
        recorded_by=current_user.id
    )

    db.add(attendance)
    await db.flush()
    await db.refresh(attendance)
    await db.commit()

    return attendance


@router.post("/bulk", response_model=List[AttendanceResponse], status_code=status.HTTP_201_CREATED)
async def create_bulk_attendance(
    bulk_data: AttendanceBulkCreate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk create attendance records.

    - **records**: List of attendance records to create
    """
    created_records = []

    for attendance_data in bulk_data.records:
        # Check for duplicate
        existing = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.student_id == attendance_data.student_id,
                    Attendance.date == attendance_data.date,
                    Attendance.period == attendance_data.period
                )
            )
        )

        if existing.scalar_one_or_none():
            continue  # Skip duplicates

        attendance = Attendance(
            **attendance_data.model_dump(),
            recorded_by=current_user.id
        )

        db.add(attendance)
        await db.flush()
        await db.refresh(attendance)
        created_records.append(attendance)

    await db.commit()

    return created_records


@router.get("", response_model=List[AttendanceResponse])
async def list_attendance(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    student_id: str = Query(None, description="Filter by student ID"),
    date_from: date = Query(None, description="Start date filter"),
    date_to: date = Query(None, description="End date filter"),
    status_filter: AttendanceStatus = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    List attendance records with filtering.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **student_id**: Optional student ID filter
    - **date_from**: Optional start date filter
    - **date_to**: Optional end date filter
    - **status**: Optional status filter
    """
    query = select(Attendance)

    filters = []
    if student_id:
        filters.append(Attendance.student_id == student_id)
    if date_from:
        filters.append(Attendance.date >= date_from)
    if date_to:
        filters.append(Attendance.date <= date_to)
    if status_filter:
        filters.append(Attendance.status == status_filter)

    if filters:
        query = query.where(and_(*filters))

    query = query.offset(skip).limit(limit).order_by(Attendance.date.desc())

    result = await db.execute(query)
    attendance_records = list(result.scalars().all())

    return attendance_records


@router.get("/absentees/today", response_model=List[AbsenteeResponse])
async def get_todays_absentees(
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Get today's absentees with call status.

    Returns list of students marked absent today with information about
    whether a call has been initiated and its current status.
    """
    today = date.today()

    # Get today's absences with student information
    query = select(Attendance, Student).join(
        Student, Attendance.student_id == Student.id
    ).where(
        and_(
            Attendance.date == today,
            Attendance.status == AttendanceStatus.ABSENT
        )
    )

    result = await db.execute(query)
    absences = result.all()

    absentees = []

    for attendance, student in absences:
        # Check if there's a call for this attendance
        call_result = await db.execute(
            select(Call).where(Call.attendance_id == attendance.id)
        )
        call = call_result.scalar_one_or_none()

        absentees.append(AbsenteeResponse(
            attendance_id=attendance.id,
            student_id=student.id,
            student_name=f"{student.first_name} {student.last_name}",
            grade_level=student.grade_level,
            date=attendance.date,
            status=attendance.status,
            has_call=call is not None,
            call_status=call.status if call else None
        ))

    return absentees


@router.put("/{attendance_id}", response_model=AttendanceResponse)
async def update_attendance(
    attendance_id: str,
    attendance_update: AttendanceUpdate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Update attendance record."""
    result = await db.execute(select(Attendance).where(Attendance.id == attendance_id))
    attendance = result.scalar_one_or_none()

    if not attendance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendance record not found"
        )

    for field, value in attendance_update.model_dump(exclude_unset=True).items():
        setattr(attendance, field, value)

    await db.commit()
    await db.refresh(attendance)

    return attendance
