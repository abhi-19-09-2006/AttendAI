"""
Call management router.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.auth import require_faculty
from app.schemas import CallResponse, CallCreate, CallUpdate, CampaignResponse, CampaignCreate, CampaignUpdate
from app.models import User, Call, CallCampaign, Student, Parent, Attendance, CallStatus

router = APIRouter()


# Campaign endpoints
@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new call campaign.

    - **name**: Campaign name
    - **description**: Optional campaign description
    - **scheduled_start**: Optional start date/time
    """
    campaign = CallCampaign(
        **campaign_data.model_dump(),
        created_by=current_user.id
    )

    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    await db.commit()

    return campaign


@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    List all call campaigns.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    result = await db.execute(
        select(CallCampaign).offset(skip).limit(limit).order_by(CallCampaign.created_at.desc())
    )
    campaigns = list(result.scalars().all())

    return campaigns


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Get campaign by ID."""
    result = await db.execute(select(CallCampaign).where(CallCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    campaign_update: CampaignUpdate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Update campaign."""
    result = await db.execute(select(CallCampaign).where(CallCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    for field, value in campaign_update.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)

    await db.commit()
    await db.refresh(campaign)

    return campaign


# Call endpoints
@router.post("", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def create_call(
    call_data: CallCreate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new call record.

    - **student_id**: ID of the student
    - **parent_id**: ID of the parent to call
    - **attendance_id**: ID of the attendance record
    - **campaign_id**: Optional campaign ID
    """
    # Verify entities exist
    student = await db.get(Student, call_data.student_id)
    parent = await db.get(Parent, call_data.parent_id)
    attendance = await db.get(Attendance, call_data.attendance_id)

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    # Verify parent belongs to student
    if parent.student_id != student.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent does not belong to this student"
        )

    call = Call(
        **call_data.model_dump(),
        status=CallStatus.PENDING,
        phone_number_called=parent.primary_phone,
        retry_count=0,
        max_retries=3
    )

    db.add(call)
    await db.flush()
    await db.refresh(call)
    await db.commit()

    return call


@router.get("", response_model=List[CallResponse])
async def list_calls(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    student_id: str = Query(None, description="Filter by student ID"),
    campaign_id: str = Query(None, description="Filter by campaign ID"),
    status_filter: CallStatus = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    List calls with filtering.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **student_id**: Optional student ID filter
    - **campaign_id**: Optional campaign ID filter
    - **status**: Optional status filter
    """
    query = select(Call)

    filters = []
    if student_id:
        filters.append(Call.student_id == student_id)
    if campaign_id:
        filters.append(Call.campaign_id == campaign_id)
    if status_filter:
        filters.append(Call.status == status_filter)

    if filters:
        query = query.where(and_(*filters))

    query = query.offset(skip).limit(limit).order_by(Call.created_at.desc())

    result = await db.execute(query)
    calls = list(result.scalars().all())

    return calls


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Get call by ID."""
    call = await db.get(Call, call_id)

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    return call


@router.put("/{call_id}", response_model=CallResponse)
async def update_call(
    call_id: str,
    call_update: CallUpdate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Update call status."""
    call = await db.get(Call, call_id)

    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )

    for field, value in call_update.model_dump(exclude_unset=True).items():
        setattr(call, field, value)

    await db.commit()
    await db.refresh(call)

    return call
