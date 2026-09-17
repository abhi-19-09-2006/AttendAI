"""
Admin router for system management and oversight.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.auth import require_admin
from app.core.security import get_password_hash
from app.models import User, CallCampaign, CampaignStatus
from app.services.admin_service import AdminService
from app.repositories.user_repository import UserRepository

router = APIRouter()


class AdminPasswordReset(BaseModel):
    """Schema for admin password reset."""
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class CampaignStatusUpdate(BaseModel):
    """Schema for campaign status transitions."""
    status: CampaignStatus


@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin dashboard: system-wide counts and health indicators.
    Returns aggregated counts for users, students, campaigns, calls, and jobs.
    """
    service = AdminService(db)
    return await service.get_dashboard()


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_user_password(
    user_id: str,
    password_data: AdminPasswordReset,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin-only: Reset a user's password.
    Returns success message with user email.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from resetting their own password via this endpoint
    # (they should use the regular password change flow)
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset your own password via admin endpoint"
        )

    user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    return {
        "message": "Password reset successfully",
        "user_email": user.email,
    }


@router.patch("/campaigns/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: str,
    status_data: CampaignStatusUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin-only: Update campaign status with validation.
    Supports pause/resume/cancel transitions.
    """
    result = await db.execute(
        select(CallCampaign).where(CallCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )

    # Validate status transitions
    current = campaign.status
    target = status_data.status

    # Define allowed transitions using existing CampaignStatus values
    allowed_transitions = {
        CampaignStatus.DRAFT: {CampaignStatus.ACTIVE, CampaignStatus.PAUSED},
        CampaignStatus.ACTIVE: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED},
        CampaignStatus.PAUSED: {CampaignStatus.ACTIVE, CampaignStatus.COMPLETED},
        CampaignStatus.COMPLETED: set(),  # Terminal state
    }

    if target not in allowed_transitions.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {current.value} to {target.value}"
        )

    campaign.status = target
    await db.commit()
    await db.refresh(campaign)

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "previous_status": current.value,
        "new_status": target.value,
    }
