"""
Call orchestration service - main business logic for managing calls.
"""
from typing import List, Optional
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.logging import get_logger
from app.models import Call, CallAttempt, Student, Parent, Attendance, AbsenceReport, FollowUp
from app.models.enums import CallStatus, AttendanceStatus, AbsenceCategory, FollowUpType, FollowUpPriority
from app.services.voice_provider import VoiceProvider, CallContext
from app.services.vapi_provider import VapiProvider
from app.services.ai_service import AIService

logger = get_logger("call_service")


class CallService:
    """Service for orchestrating absence calls."""

    def __init__(self, db: AsyncSession, voice_provider: Optional[VoiceProvider] = None):
        self.db = db
        self.voice_provider = voice_provider or VapiProvider()
        self.ai_service = AIService()

    async def create_calls_for_absentees(
        self,
        absence_date: date,
        campaign_id: Optional[str] = None
    ) -> List[Call]:
        """
        Create call records for all students marked absent on given date.

        Args:
            absence_date: Date to check for absences
            campaign_id: Optional campaign to associate calls with

        Returns:
            List of created Call objects
        """
        # Find all absences for the date
        query = select(Attendance).where(
            and_(
                Attendance.date == absence_date,
                Attendance.status == AttendanceStatus.ABSENT
            )
        )
        result = await self.db.execute(query)
        absences = result.scalars().all()

        logger.info(f"Found {len(absences)} absences for {absence_date}")

        created_calls = []

        for attendance in absences:
            # Check if call already exists for this attendance
            existing_call = await self.db.execute(
                select(Call).where(Call.attendance_id == attendance.id)
            )
            if existing_call.scalar_one_or_none():
                logger.debug(f"Call already exists for attendance {attendance.id}")
                continue

            # Get primary parent contact
            parent_query = select(Parent).where(
                and_(
                    Parent.student_id == attendance.student_id,
                    Parent.is_primary_contact == True
                )
            )
            parent_result = await self.db.execute(parent_query)
            parent = parent_result.scalar_one_or_none()

            # If no primary contact, get any parent
            if not parent:
                parent_query = select(Parent).where(
                    Parent.student_id == attendance.student_id
                ).limit(1)
                parent_result = await self.db.execute(parent_query)
                parent = parent_result.scalar_one_or_none()

            if not parent:
                logger.warning(f"No parent found for student {attendance.student_id}")
                continue

            # Create call record
            call = Call(
                campaign_id=campaign_id,
                student_id=attendance.student_id,
                parent_id=parent.id,
                attendance_id=attendance.id,
                status=CallStatus.PENDING,
                phone_number_called=parent.primary_phone,
                retry_count=0,
                max_retries=3
            )

            self.db.add(call)
            await self.db.flush()
            await self.db.refresh(call)

            created_calls.append(call)
            logger.info(f"Created call {call.id} for student {attendance.student_id}")

        await self.db.commit()

        return created_calls

    async def initiate_call(self, call_id: str) -> bool:
        """
        Initiate a call via Vapi.

        Args:
            call_id: ID of the call to initiate

        Returns:
            True if successful
        """
        call = await self.db.get(Call, call_id)
        if not call:
            logger.error(f"Call {call_id} not found")
            return False

        # Get student info for context
        student = await self.db.get(Student, call.student_id)
        if not student:
            logger.error(f"Student {call.student_id} not found")
            return False

        # Get attendance info
        attendance = await self.db.get(Attendance, call.attendance_id)
        if not attendance:
            logger.error(f"Attendance {call.attendance_id} not found")
            return False

        try:
            # Update status to queued
            call.status = CallStatus.QUEUED
            await self.db.commit()

            # Initiate call via voice provider
            student_name = f"{student.first_name} {student.last_name}"
            absence_date = attendance.date.isoformat()

            context = CallContext(
                phone_number=call.phone_number_called,
                student_name=student_name,
                absence_date=absence_date,
                correlation_id=call.id  # Use our call ID for correlation
            )

            call_result = await self.voice_provider.create_call(context)

            # Update call with provider ID and status
            call.vapi_call_id = call_result.provider_call_id
            call.status = CallStatus.CALLING
            call.initiated_at = call_result.initiated_at

            # Create attempt record
            attempt = CallAttempt(
                call_id=call.id,
                attempt_number=call.retry_count + 1,
                status=CallStatus.CALLING,
                vapi_call_id=call.vapi_call_id,
                initiated_at=call.initiated_at
            )

            self.db.add(attempt)
            await self.db.commit()

            logger.info(f"Initiated call {call_id} via provider: {call.vapi_call_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to initiate call {call_id}: {str(e)}")
            call.status = CallStatus.FAILED
            await self.db.commit()
            return False

    async def process_call_completion(
        self,
        call_id: str,
        vapi_call_id: str,
        status: str,
        transcript: Optional[str] = None
    ) -> bool:
        """
        Process a completed call and extract absence information.

        Args:
            call_id: Internal call ID
            vapi_call_id: Vapi call ID
            status: Final call status
            transcript: Call transcript if available

        Returns:
            True if processed successfully
        """
        call = await self.db.get(Call, call_id)
        if not call:
            logger.error(f"Call {call_id} not found")
            return False

        # Map Vapi status to our CallStatus
        status_mapping = {
            "completed": CallStatus.COMPLETED,
            "no-answer": CallStatus.NO_ANSWER,
            "busy": CallStatus.BUSY,
            "failed": CallStatus.FAILED
        }

        call.status = status_mapping.get(status, CallStatus.COMPLETED)
        call.ended_at = datetime.utcnow()

        # Update current attempt
        attempt_query = select(CallAttempt).where(
            CallAttempt.vapi_call_id == vapi_call_id
        )
        attempt_result = await self.db.execute(attempt_query)
        attempt = attempt_result.scalar_one_or_none()

        if attempt:
            attempt.status = call.status
            attempt.ended_at = datetime.utcnow()

        # Calculate duration
        if call.initiated_at and call.ended_at:
            duration = (call.ended_at - call.initiated_at).total_seconds()
            call.duration_seconds = int(duration)
            if attempt:
                attempt.duration_seconds = int(duration)

        await self.db.commit()

        # Extract information if call was answered and has transcript
        if call.status in [CallStatus.COMPLETED, CallStatus.ANSWERED] and transcript:
            await self._extract_and_save_absence_info(call, transcript)

        # Handle retries for failed calls
        if call.status in [CallStatus.NO_ANSWER, CallStatus.BUSY, CallStatus.FAILED]:
            await self._handle_retry(call)

        logger.info(f"Processed call completion for {call_id}: {call.status}")
        return True

    async def _extract_and_save_absence_info(self, call: Call, transcript: str):
        """Extract and save absence information from transcript."""

        try:
            # Check if absence report already exists (idempotency for duplicate webhooks)
            existing_report = await self.db.execute(
                select(AbsenceReport).where(AbsenceReport.call_id == call.id)
            )
            if existing_report.scalar_one_or_none():
                logger.info(f"Absence report already exists for call {call.id}, skipping")
                return
            
            # Get student for context
            student = await self.db.get(Student, call.student_id)
            attendance = await self.db.get(Attendance, call.attendance_id)

            if not student or not attendance:
                logger.error("Missing student or attendance data")
                return

            # Extract information using AI
            student_name = f"{student.first_name} {student.last_name}"
            extraction = await self.ai_service.extract_absence_info(
                transcript=transcript,
                student_name=student_name,
                absence_date=attendance.date
            )

            # Map category string to AbsenceCategory enum
            category_mapping = {
                "medical": AbsenceCategory.MEDICAL,
                "family": AbsenceCategory.FAMILY,
                "personal": AbsenceCategory.PERSONAL,
                "other": AbsenceCategory.OTHER,
                "unknown": AbsenceCategory.UNKNOWN,
                "transportation": AbsenceCategory.OTHER,  # map transportation to other for DB enum
            }
            category_enum = category_mapping.get(str(extraction.category.value if hasattr(extraction.category, 'value') else extraction.category), AbsenceCategory.UNKNOWN)

            # Create absence report
            report = AbsenceReport(
                call_id=call.id,
                student_id=call.student_id,
                attendance_id=call.attendance_id,
                reason=extraction.reason,
                category=category_enum,
                duration=extraction.duration,
                expected_return_date=extraction.expected_return_date,
                parent_confirmed=extraction.parent_confirmed,
                follow_up_required=extraction.follow_up_required,
                confidence_score=extraction.confidence_score,
                transcript=transcript,
                raw_extraction=extraction.model_dump(mode="json")
            )

            self.db.add(report)
            await self.db.flush()

            # Create follow-up if needed
            if report.follow_up_required or report.confidence_score < 0.85:
                await self._create_followup(report)

            await self.db.commit()

            logger.info(f"Created absence report {report.id} with confidence {report.confidence_score}")

        except Exception as e:
            logger.error(f"Failed to extract absence info: {str(e)}")
            await self.db.rollback()

    async def _create_followup(self, report: AbsenceReport):
        """Create a follow-up task for low confidence or flagged reports."""

        followup_type = FollowUpType.LOW_CONFIDENCE
        priority = FollowUpPriority.MEDIUM
        description = f"Review absence report - confidence: {report.confidence_score:.2f}"

        if report.confidence_score < 0.5:
            priority = FollowUpPriority.HIGH
            description = f"Low confidence extraction ({report.confidence_score:.2f}) - verify information"
        elif report.category == AbsenceCategory.MEDICAL:
            followup_type = FollowUpType.MEDICAL_VERIFICATION
            description = "Medical absence - verify and collect documentation if needed"

        followup = FollowUp(
            student_id=report.student_id,
            absence_report_id=report.id,
            call_id=report.call_id,
            type=followup_type,
            priority=priority,
            description=description
        )

        self.db.add(followup)
        logger.info(f"Created follow-up for report {report.id}")

    async def _handle_retry(self, call: Call):
        """
        Handle retry logic for failed calls.
        
        Schedules a retry through the RQ job infrastructure instead of
        immediately resetting status to PENDING. The actual retry will
        be executed by the retry_failed_call task after the backoff delay.
        """
        # Import here to avoid circular dependency
        from app.tasks import _schedule_retry_async
        
        next_retry_number = call.retry_count + 1
        
        if next_retry_number > call.max_retries:
            call.status = CallStatus.UNREACHABLE
            await self.db.commit()
            logger.warning(f"Call {call.id} exceeded max retries ({call.max_retries})")
            return
        
        # Schedule retry through RQ infrastructure
        # This creates a DEFERRED job with backoff delay
        # The call status remains as NO_ANSWER/BUSY/FAILED so the scheduler
        # can verify it's still retryable when the job runs
        result = await _schedule_retry_async(
            call_id=call.id,
            retry_number=next_retry_number,
            session=self.db
        )
        
        if result.get("status") == "scheduled":
            logger.info(
                f"Scheduled retry {next_retry_number} for call {call.id} "
                f"at {result.get('next_retry_at')}"
            )
        elif result.get("status") == "skipped":
            reason = result.get("reason", "unknown")
            logger.info(f"Retry skipped for call {call.id}: {reason}")
        else:
            logger.error(f"Failed to schedule retry for call {call.id}: {result}")

    async def get_call_statistics(self, campaign_id: Optional[str] = None) -> dict:
        """
        Get call statistics for a campaign or overall.

        Args:
            campaign_id: Optional campaign ID to filter by

        Returns:
            Dictionary with call statistics
        """
        query = select(Call)
        if campaign_id:
            query = query.where(Call.campaign_id == campaign_id)

        result = await self.db.execute(query)
        calls = result.scalars().all()

        stats = {
            "total_calls": len(calls),
            "by_status": {},
            "average_duration": 0,
            "success_rate": 0
        }

        # Count by status
        for status in CallStatus:
            count = sum(1 for c in calls if c.status == status)
            stats["by_status"][status.value] = count

        # Calculate average duration
        durations = [c.duration_seconds for c in calls if c.duration_seconds]
        if durations:
            stats["average_duration"] = sum(durations) / len(durations)

        # Calculate success rate
        completed = stats["by_status"].get(CallStatus.COMPLETED.value, 0)
        if stats["total_calls"] > 0:
            stats["success_rate"] = (completed / stats["total_calls"]) * 100

        return stats
