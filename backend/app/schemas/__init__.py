"""
Pydantic schemas for API request/response validation.
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict

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


# ============================================================================
# Authentication Schemas
# ============================================================================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Token refresh request."""
    refresh_token: str


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str
    role: UserRole
    department: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update schema."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Student Schemas
# ============================================================================

class StudentBase(BaseModel):
    """Base student schema."""
    student_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    grade_level: int = Field(..., ge=1, le=12)
    department: Optional[str] = None


class StudentCreate(StudentBase):
    """Student creation schema."""
    pass


class StudentUpdate(BaseModel):
    """Student update schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    grade_level: Optional[int] = Field(None, ge=1, le=12)
    department: Optional[str] = None
    is_active: Optional[bool] = None


class StudentResponse(StudentBase):
    """Student response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Parent Schemas
# ============================================================================

class ParentBase(BaseModel):
    """Base parent schema."""
    student_id: str
    relationship: ParentRelationship
    first_name: str
    last_name: str
    primary_phone: str
    secondary_phone: Optional[str] = None
    email: Optional[EmailStr] = None
    preferred_contact_method: ContactMethod = ContactMethod.PHONE
    preferred_language: str = "en"
    is_primary_contact: bool = False


class ParentCreate(ParentBase):
    """Parent creation schema."""
    pass


class ParentUpdate(BaseModel):
    """Parent update schema."""
    relationship: Optional[ParentRelationship] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    primary_phone: Optional[str] = None
    secondary_phone: Optional[str] = None
    email: Optional[EmailStr] = None
    preferred_contact_method: Optional[ContactMethod] = None
    preferred_language: Optional[str] = None
    is_primary_contact: Optional[bool] = None


class ParentResponse(ParentBase):
    """Parent response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Attendance Schemas
# ============================================================================

class AttendanceBase(BaseModel):
    """Base attendance schema."""
    student_id: str
    date: date
    status: AttendanceStatus
    period: Optional[str] = None
    notes: Optional[str] = None


class AttendanceCreate(AttendanceBase):
    """Attendance creation schema."""
    pass


class AttendanceBulkCreate(BaseModel):
    """Bulk attendance creation."""
    records: List[AttendanceCreate]


class AttendanceUpdate(BaseModel):
    """Attendance update schema."""
    status: Optional[AttendanceStatus] = None
    notes: Optional[str] = None


class AttendanceResponse(AttendanceBase):
    """Attendance response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    recorded_by: str
    created_at: datetime
    updated_at: datetime


class AbsenteeResponse(BaseModel):
    """Absentee response with student details."""
    model_config = ConfigDict(from_attributes=True)

    attendance_id: str
    student_id: str
    student_name: str
    grade_level: int
    date: date
    status: AttendanceStatus
    has_call: bool = False
    call_status: Optional[CallStatus] = None


# ============================================================================
# Call Campaign Schemas
# ============================================================================

class CampaignBase(BaseModel):
    """Base campaign schema."""
    name: str
    description: Optional[str] = None
    scheduled_start: Optional[datetime] = None


class CampaignCreate(CampaignBase):
    """Campaign creation schema."""
    pass


class CampaignUpdate(BaseModel):
    """Campaign update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CampaignStatus] = None
    scheduled_start: Optional[datetime] = None


class CampaignResponse(CampaignBase):
    """Campaign response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: CampaignStatus
    created_by: str
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Call Schemas
# ============================================================================

class CallBase(BaseModel):
    """Base call schema."""
    student_id: str
    parent_id: str
    attendance_id: str
    campaign_id: Optional[str] = None


class CallCreate(CallBase):
    """Call creation schema."""
    pass


class CallUpdate(BaseModel):
    """Call update schema."""
    status: Optional[CallStatus] = None


class CallResponse(CallBase):
    """Call response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: CallStatus
    phone_number_called: str
    vapi_call_id: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    initiated_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Absence Report Schemas
# ============================================================================

class AbsenceReportBase(BaseModel):
    """Base absence report schema."""
    reason: Optional[str] = None
    category: AbsenceCategory = AbsenceCategory.UNKNOWN
    duration: Optional[str] = None
    expected_return_date: Optional[date] = None
    parent_confirmed: bool = False
    follow_up_required: bool = False


class AbsenceReportCreate(AbsenceReportBase):
    """Absence report creation schema."""
    call_id: str
    student_id: str
    attendance_id: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    transcript: Optional[str] = None
    raw_extraction: Optional[dict] = None


class AbsenceReportUpdate(BaseModel):
    """Absence report update schema."""
    reason: Optional[str] = None
    category: Optional[AbsenceCategory] = None
    duration: Optional[str] = None
    expected_return_date: Optional[date] = None
    parent_confirmed: Optional[bool] = None
    follow_up_required: Optional[bool] = None
    review_notes: Optional[str] = None


class AbsenceReportResponse(AbsenceReportBase):
    """Absence report response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    call_id: str
    student_id: str
    attendance_id: str
    confidence_score: float
    transcript: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Follow-up Schemas
# ============================================================================

class FollowUpBase(BaseModel):
    """Base follow-up schema."""
    student_id: str
    type: FollowUpType
    priority: FollowUpPriority = FollowUpPriority.MEDIUM
    description: str
    due_date: Optional[date] = None


class FollowUpCreate(FollowUpBase):
    """Follow-up creation schema."""
    absence_report_id: Optional[str] = None
    call_id: Optional[str] = None
    assigned_to: Optional[str] = None


class FollowUpUpdate(BaseModel):
    """Follow-up update schema."""
    status: Optional[FollowUpStatus] = None
    priority: Optional[FollowUpPriority] = None
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None
    description: Optional[str] = None
    resolution_notes: Optional[str] = None


class FollowUpResponse(FollowUpBase):
    """Follow-up response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    absence_report_id: Optional[str] = None
    call_id: Optional[str] = None
    assigned_to: Optional[str] = None
    status: FollowUpStatus
    resolution_notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Pagination Schemas
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    total: int
    skip: int
    limit: int
    items: List[BaseModel]
