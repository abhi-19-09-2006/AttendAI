"""
Absence report management router.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.auth import require_faculty, get_current_user
from app.schemas import AbsenceReportResponse, AbsenceReportCreate, AbsenceReportUpdate
from app.models import User, AbsenceReport, Call, Student, Attendance

router = APIRouter()


@router.post("", response_model=AbsenceReportResponse, status_code=status.HTTP_201_CREATED)
async def create_absence_report(
    report_data: AbsenceReportCreate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Create an absence report.

    - **call_id**: ID of the call
    - **student_id**: ID of the student
    - **attendance_id**: ID of the attendance record
    - **confidence_score**: AI confidence score (0.0-1.0)
    - **reason**: Reason for absence
    - **category**: Absence category
    """
    # Verify entities exist
    call = await db.get(Call, report_data.call_id)
    student = await db.get(Student, report_data.student_id)
    attendance = await db.get(Attendance, report_data.attendance_id)

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    # Check if report already exists for this call
    existing = await db.execute(
        select(AbsenceReport).where(AbsenceReport.call_id == report_data.call_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Absence report already exists for this call"
        )

    report = AbsenceReport(**report_data.model_dump())

    db.add(report)
    await db.flush()
    await db.refresh(report)
    await db.commit()

    return report


@router.get("", response_model=List[AbsenceReportResponse])
async def list_absence_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    student_id: str = Query(None, description="Filter by student ID"),
    call_id: str = Query(None, description="Filter by call ID"),
    min_confidence: float = Query(None, ge=0.0, le=1.0, description="Minimum confidence score"),
    requires_review: bool = Query(None, description="Filter reports requiring review"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    List absence reports with filtering.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **student_id**: Optional student ID filter
    - **call_id**: Optional call ID filter
    - **min_confidence**: Optional minimum confidence filter
    - **requires_review**: Filter for reports needing review (confidence < 0.85 or follow_up_required)
    """
    query = select(AbsenceReport)

    filters = []
    if student_id:
        filters.append(AbsenceReport.student_id == student_id)
    if call_id:
        filters.append(AbsenceReport.call_id == call_id)
    if min_confidence is not None:
        filters.append(AbsenceReport.confidence_score >= min_confidence)
    if requires_review is True:
        filters.append(
            and_(
                AbsenceReport.reviewed_by.is_(None),
                (AbsenceReport.confidence_score < 0.85) | (AbsenceReport.follow_up_required == True)
            )
        )

    if filters:
        query = query.where(and_(*filters))

    query = query.offset(skip).limit(limit).order_by(AbsenceReport.created_at.desc())

    result = await db.execute(query)
    reports = list(result.scalars().all())

    return reports


@router.get("/{report_id}", response_model=AbsenceReportResponse)
async def get_absence_report(
    report_id: str,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Get absence report by ID."""
    report = await db.get(AbsenceReport, report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence report not found"
        )

    return report


@router.put("/{report_id}", response_model=AbsenceReportResponse)
async def update_absence_report(
    report_id: str,
    report_update: AbsenceReportUpdate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Update absence report.

    Allows faculty to review and correct AI-extracted information.
    """
    report = await db.get(AbsenceReport, report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence report not found"
        )

    # Update fields
    for field, value in report_update.model_dump(exclude_unset=True).items():
        setattr(report, field, value)

    # Mark as reviewed if not already
    if not report.reviewed_by:
        report.reviewed_by = current_user.id
        from datetime import datetime
        report.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(report)

    return report


@router.post("/{report_id}/review", response_model=AbsenceReportResponse)
async def review_absence_report(
    report_id: str,
    review_notes: str = Query(..., description="Review notes"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark absence report as reviewed by faculty.

    - **review_notes**: Notes from the reviewer
    """
    report = await db.get(AbsenceReport, report_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence report not found"
        )

    from datetime import datetime
    report.reviewed_by = current_user.id
    report.reviewed_at = datetime.utcnow()
    report.review_notes = review_notes

    await db.commit()
    await db.refresh(report)

    return report
