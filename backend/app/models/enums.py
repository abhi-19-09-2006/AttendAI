"""
Database models enums.
"""
import enum


class UserRole(str, enum.Enum):
    """User role enumeration."""
    ADMIN = "admin"
    FACULTY = "faculty"
    STAFF = "staff"


class AttendanceStatus(str, enum.Enum):
    """Attendance status enumeration."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"


class CallStatus(str, enum.Enum):
    """Call status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    CALLING = "calling"
    ANSWERED = "answered"
    COMPLETED = "completed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    INVALID_NUMBER = "invalid_number"
    CALLBACK_REQUESTED = "callback_requested"
    FOLLOW_UP_REQUIRED = "follow_up_required"
    UNREACHABLE = "unreachable"
    CANCELLED = "cancelled"


class CampaignStatus(str, enum.Enum):
    """Call campaign status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class AbsenceCategory(str, enum.Enum):
    """Absence reason category."""
    MEDICAL = "medical"
    FAMILY = "family"
    PERSONAL = "personal"
    OTHER = "other"
    UNKNOWN = "unknown"


class FollowUpType(str, enum.Enum):
    """Follow-up task type."""
    CALLBACK_REQUESTED = "callback_requested"
    LOW_CONFIDENCE = "low_confidence"
    MEDICAL_VERIFICATION = "medical_verification"
    OTHER = "other"


class FollowUpPriority(str, enum.Enum):
    """Follow-up priority level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FollowUpStatus(str, enum.Enum):
    """Follow-up status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ParentRelationship(str, enum.Enum):
    """Parent/guardian relationship to student."""
    MOTHER = "mother"
    FATHER = "father"
    GUARDIAN = "guardian"
    STEPMOTHER = "stepmother"
    STEPFATHER = "stepfather"
    GRANDPARENT = "grandparent"
    OTHER = "other"


class ContactMethod(str, enum.Enum):
    """Preferred contact method."""
    PHONE = "phone"
    EMAIL = "email"
    SMS = "sms"
