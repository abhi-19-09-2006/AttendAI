"""
Follow-up task management router.
"""
from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.auth import require_faculty, get_current_user
from app.schemas import FollowUpResponse, FollowUpCreate, FollowUpUpdate
from app.models import User, FollowUp, Student, FollowUpStatus, FollowUpPriority

router = APIRouter()


@router.post("", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
async def create_followup(
    followup_data: FollowUpCreate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a follow-up task.

    - **student_id**: ID of the student
    - **type**: Type of follow-up
    - **priority**: Priority level
    - **description**: Task description
    - **due_date**: Optional due date
    """
    # Verify student exists
    student = await db.get(Student, followup_data.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    followup = FollowUp(**followup_data.model_dump())

    db.add(followup)
    await db.flush()
    await db.refresh(followup)
    await db.commit()

    return followup


@router.get("", response_model=List[FollowUpResponse])
async def list_followups(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    student_id: str = Query(None, description="Filter by student ID"),
    assigned_to: str = Query(None, description="Filter by assigned user ID"),
    status_filter: FollowUpStatus = Query(None, alias="status", description="Filter by status"),
    priority_filter: FollowUpPriority = Query(None, alias="priority", description="Filter by priority"),
    overdue: bool = Query(None, description="Filter for overdue tasks"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    List follow-up tasks with filtering.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **student_id**: Optional student ID filter
    - **assigned_to**: Optional assigned user filter
    - **status**: Optional status filter
    - **priority**: Optional priority filter
    - **overdue**: Filter for overdue tasks
    """
    query = select(FollowUp)

    filters = []
    if student_id:
        filters.append(FollowUp.student_id == student_id)
    if assigned_to:
        filters.append(FollowUp.assigned_to == assigned_to)
    if status_filter:
        filters.append(FollowUp.status == status_filter)
    if priority_filter:
        filters.append(FollowUp.priority == priority_filter)
    if overdue is True:
        today = date.today()
        filters.append(
            and_(
                FollowUp.due_date.isnot(None),
                FollowUp.due_date < today,
                FollowUp.status.in_([FollowUpStatus.PENDING, FollowUpStatus.IN_PROGRESS])
            )
        )

    if filters:
        query = query.where(and_(*filters))

    query = query.offset(skip).limit(limit).order_by(FollowUp.priority.desc(), FollowUp.due_date)

    result = await db.execute(query)
    followups = list(result.scalars().all())

    return followups


@router.get("/my-tasks", response_model=List[FollowUpResponse])
async def get_my_followups(
    status_filter: FollowUpStatus = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get follow-up tasks assigned to current user.

    - **status**: Optional status filter
    """
    query = select(FollowUp).where(FollowUp.assigned_to == current_user.id)

    if status_filter:
        query = query.where(FollowUp.status == status_filter)

    query = query.order_by(FollowUp.priority.desc(), FollowUp.due_date)

    result = await db.execute(query)
    followups = list(result.scalars().all())

    return followups


@router.get("/{followup_id}", response_model=FollowUpResponse)
async def get_followup(
    followup_id: str,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Get follow-up task by ID."""
    followup = await db.get(FollowUp, followup_id)

    if not followup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up task not found"
        )

    return followup


@router.put("/{followup_id}", response_model=FollowUpResponse)
async def update_followup(
    followup_id: str,
    followup_update: FollowUpUpdate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Update follow-up task."""
    followup = await db.get(FollowUp, followup_id)

    if not followup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up task not found"
        )

    # Update fields
    for field, value in followup_update.model_dump(exclude_unset=True).items():
        setattr(followup, field, value)

    # Set completed_at if status is completed
    if followup_update.status == FollowUpStatus.COMPLETED and not followup.completed_at:
        from datetime import datetime
        followup.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(followup)

    return followup


@router.post("/{followup_id}/assign", response_model=FollowUpResponse)
async def assign_followup(
    followup_id: str,
    user_id: str = Query(..., description="User ID to assign to"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign follow-up task to a user.

    - **user_id**: ID of the user to assign the task to
    """
    followup = await db.get(FollowUp, followup_id)

    if not followup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up task not found"
        )

    # Verify user exists
    from app.models import User as UserModel
    user = await db.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    followup.assigned_to = user_id
    if followup.status == FollowUpStatus.PENDING:
        followup.status = FollowUpStatus.IN_PROGRESS

    await db.commit()
    await db.refresh(followup)

    return followup


@router.post("/{followup_id}/complete", response_model=FollowUpResponse)
async def complete_followup(
    followup_id: str,
    resolution_notes: str = Query(..., description="Resolution notes"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark follow-up task as completed.

    - **resolution_notes**: Notes about how the task was resolved
    """
    followup = await db.get(FollowUp, followup_id)

    if not followup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow-up task not found"
        )

    from datetime import datetime
    followup.status = FollowUpStatus.COMPLETED
    followup.resolution_notes = resolution_notes
    followup.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(followup)

    return followup
