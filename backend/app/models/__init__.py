"""
Database models package.
"""
from app.core.database import Base
from app.models.enums import (
    UserRole,
    AttendanceStatus,
    CallStatus,
    CampaignStatus,
    AbsenceCategory,
    FollowUpType,
    FollowUpPriority,
    FollowUpStatus,
    ParentRelationship,
    ContactMethod,
)
from app.models.user import User
from app.models.student import Student
from app.models.parent import Parent
from app.models.attendance import Attendance
from app.models.call_campaign import CallCampaign
from app.models.call import Call, CallAttempt
from app.models.absence_report import AbsenceReport
from app.models.followup import FollowUp
from app.models.audit_log import AuditLog

__all__ = [
    "Base",
    # Enums
    "UserRole",
    "AttendanceStatus",
    "CallStatus",
    "CampaignStatus",
    "AbsenceCategory",
    "FollowUpType",
    "FollowUpPriority",
    "FollowUpStatus",
    "ParentRelationship",
    "ContactMethod",
    # Models
    "User",
    "Student",
    "Parent",
    "Attendance",
    "CallCampaign",
    "Call",
    "CallAttempt",
    "AbsenceReport",
    "FollowUp",
    "AuditLog",
]
