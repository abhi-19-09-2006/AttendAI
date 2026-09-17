"""
Admin service for system-wide aggregation and management operations.
"""
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.logging import get_logger
from app.models import (
    User, Student, Call, CallCampaign, Job,
    UserRole, CallStatus, CampaignStatus, JobStatus,
)

logger = get_logger("admin_service")


class AdminService:
    """Admin dashboard and management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard(self) -> Dict[str, Any]:
        """
        Admin dashboard: system-wide counts and health indicators.
        """
        # User counts by role
        user_q = select(
            func.count(User.id).label("total"),
            func.count(func.case((User.role == UserRole.ADMIN, 1))).label("admins"),
            func.count(func.case((User.role == UserRole.FACULTY, 1))).label("faculty"),
            func.count(func.case((User.role == UserRole.STAFF, 1))).label("staff"),
            func.count(func.case((User.is_active == True, 1))).label("active"),
        )
        user_row = (await self.db.execute(user_q)).one()

        # Student counts
        student_q = select(
            func.count(Student.id).label("total"),
            func.count(func.case((Student.is_active == True, 1))).label("active"),
        )
        student_row = (await self.db.execute(student_q)).one()

        # Campaign counts
        campaign_q = select(
            func.count(CallCampaign.id).label("total"),
            func.count(func.case((CallCampaign.status == CampaignStatus.ACTIVE, 1))).label("active"),
            func.count(func.case((CallCampaign.status == CampaignStatus.PAUSED, 1))).label("paused"),
            func.count(func.case((CallCampaign.status == CampaignStatus.COMPLETED, 1))).label("completed"),
        )
        campaign_row = (await self.db.execute(campaign_q)).one()

        # Call counts
        call_q = select(
            func.count(Call.id).label("total"),
            func.count(func.case((Call.status == CallStatus.COMPLETED, 1))).label("completed"),
            func.count(func.case((Call.status == CallStatus.FAILED, 1))).label("failed"),
            func.count(func.case((Call.status == CallStatus.PENDING, 1))).label("pending"),
        )
        call_row = (await self.db.execute(call_q)).one()

        # Job counts
        job_q = select(
            func.count(Job.id).label("total"),
            func.count(func.case((Job.status == JobStatus.QUEUED, 1))).label("queued"),
            func.count(func.case((Job.status == JobStatus.STARTED, 1))).label("started"),
            func.count(func.case((Job.status == JobStatus.FAILED, 1))).label("failed"),
        )
        job_row = (await self.db.execute(job_q)).one()

        return {
            "users": {
                "total": user_row.total or 0,
                "admins": user_row.admins or 0,
                "faculty": user_row.faculty or 0,
                "staff": user_row.staff or 0,
                "active": user_row.active or 0,
            },
            "students": {
                "total": student_row.total or 0,
                "active": student_row.active or 0,
            },
            "campaigns": {
                "total": campaign_row.total or 0,
                "active": campaign_row.active or 0,
                "paused": campaign_row.paused or 0,
                "completed": campaign_row.completed or 0,
            },
            "calls": {
                "total": call_row.total or 0,
                "completed": call_row.completed or 0,
                "failed": call_row.failed or 0,
                "pending": call_row.pending or 0,
            },
            "jobs": {
                "total": job_row.total or 0,
                "queued": job_row.queued or 0,
                "started": job_row.started or 0,
                "failed": job_row.failed or 0,
            },
        }
