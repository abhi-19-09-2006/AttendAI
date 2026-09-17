"""
Analytics service for aggregating attendance, call, and follow-up metrics.

All queries operate on existing models — no new tables or infrastructure.
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case, cast, Date

from app.core.logging import get_logger
from app.models import (
    Attendance, Call, CallAttempt, AbsenceReport, FollowUp,
    AttendanceStatus, CallStatus, AbsenceCategory, FollowUpStatus,
)

logger = get_logger("analytics_service")


class AnalyticsService:
    """Aggregation queries for faculty analytics and reports."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Summary ────────────────────────────────────────────────────────────

    async def get_summary(
        self,
        date_from: date,
        date_to: date,
    ) -> Dict[str, Any]:
        """
        High-level summary for a date range.

        Returns counts and rates derived from Attendance, Call, FollowUp,
        and AbsenceReport rows within [date_from, date_to].
        """
        # Attendance counts
        att_q = select(
            func.count(Attendance.id).label("total"),
            func.count(case((Attendance.status == AttendanceStatus.ABSENT, 1))).label("absent"),
        ).where(
            and_(Attendance.date >= date_from, Attendance.date <= date_to)
        )
        att_row = (await self.db.execute(att_q)).one()
        total_attendance = att_row.total or 0
        total_absentees = att_row.absent or 0

        # Call counts — join to attendance to scope by date range
        call_q = select(
            func.count(Call.id).label("total"),
            func.count(case((Call.status == CallStatus.COMPLETED, 1))).label("completed"),
            func.count(case((Call.status == CallStatus.NO_ANSWER, 1))).label("no_answer"),
            func.count(case((Call.status == CallStatus.BUSY, 1))).label("busy"),
            func.count(case((Call.status == CallStatus.FAILED, 1))).label("failed"),
            func.count(case((Call.status == CallStatus.UNREACHABLE, 1))).label("unreachable"),
            func.count(case((Call.status == CallStatus.PENDING, 1))).label("pending"),
            func.count(case((Call.status == CallStatus.CALLING, 1))).label("calling"),
        ).join(Attendance, Call.attendance_id == Attendance.id).where(
            and_(Attendance.date >= date_from, Attendance.date <= date_to)
        )
        call_row = (await self.db.execute(call_q)).one()
        total_calls = call_row.total or 0
        completed_calls = call_row.completed or 0
        no_answer_calls = call_row.no_answer or 0
        busy_calls = call_row.busy or 0
        failed_calls = call_row.failed or 0
        unreachable_calls = call_row.unreachable or 0

        # Average call duration (only completed calls with duration data)
        dur_q = select(func.avg(Call.duration_seconds)).join(
            Attendance, Call.attendance_id == Attendance.id
        ).where(
            and_(
                Attendance.date >= date_from,
                Attendance.date <= date_to,
                Call.duration_seconds.isnot(None),
                Call.duration_seconds > 0,
            )
        )
        avg_duration = (await self.db.execute(dur_q)).scalar()

        # Follow-up counts
        fu_q = select(
            func.count(FollowUp.id).label("total"),
            func.count(case((FollowUp.status == FollowUpStatus.PENDING, 1))).label("pending"),
            func.count(case((FollowUp.status == FollowUpStatus.COMPLETED, 1))).label("completed"),
        ).join(Call, FollowUp.call_id == Call.id).join(
            Attendance, Call.attendance_id == Attendance.id
        ).where(
            and_(Attendance.date >= date_from, Attendance.date <= date_to)
        )
        fu_row = (await self.db.execute(fu_q)).one()

        # Rates
        answer_rate = (completed_calls / total_calls * 100) if total_calls else 0.0
        no_answer_rate = (no_answer_calls / total_calls * 100) if total_calls else 0.0
        failure_rate = (failed_calls / total_calls * 100) if total_calls else 0.0

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "total_attendance": total_attendance,
            "total_absentees": total_absentees,
            "total_calls": total_calls,
            "completed_calls": completed_calls,
            "no_answer_calls": no_answer_calls,
            "busy_calls": busy_calls,
            "failed_calls": failed_calls,
            "unreachable_calls": unreachable_calls,
            "pending_calls": call_row.pending or 0,
            "answer_rate": round(answer_rate, 1),
            "no_answer_rate": round(no_answer_rate, 1),
            "failure_rate": round(failure_rate, 1),
            "average_duration_seconds": round(avg_duration, 1) if avg_duration else None,
            "total_followups": fu_row.total or 0,
            "pending_followups": fu_row.pending or 0,
            "completed_followups": fu_row.completed or 0,
        }

    # ── Trends ─────────────────────────────────────────────────────────────

    async def get_daily_trends(
        self,
        date_from: date,
        date_to: date,
    ) -> List[Dict[str, Any]]:
        """
        Day-by-day absentee and call counts for the date range.
        """
        q = select(
            Attendance.date.label("date"),
            func.count(Attendance.id).label("total_attendance"),
            func.count(case((Attendance.status == AttendanceStatus.ABSENT, 1))).label("absentees"),
        ).where(
            and_(Attendance.date >= date_from, Attendance.date <= date_to)
        ).group_by(Attendance.date).order_by(Attendance.date)

        rows = (await self.db.execute(q)).all()

        # Build a lookup for call counts per date
        call_q = select(
            Attendance.date.label("date"),
            func.count(Call.id).label("total_calls"),
            func.count(case((Call.status == CallStatus.COMPLETED, 1))).label("completed"),
        ).join(Attendance, Call.attendance_id == Attendance.id).where(
            and_(Attendance.date >= date_from, Attendance.date <= date_to)
        ).group_by(Attendance.date)

        call_rows = (await self.db.execute(call_q)).all()
        call_map = {r.date: {"total_calls": r.total_calls, "completed": r.completed} for r in call_rows}

        results = []
        for row in rows:
            call_data = call_map.get(row.date, {"total_calls": 0, "completed": 0})
            results.append({
                "date": row.date.isoformat(),
                "total_attendance": row.total_attendance,
                "absentees": row.absentees,
                "calls": call_data["total_calls"],
                "completed_calls": call_data["completed"],
            })

        return results

    # ── Call Metrics ───────────────────────────────────────────────────────

    async def get_call_metrics(
        self,
        date_from: date,
        date_to: date,
    ) -> Dict[str, Any]:
        """
        Call-specific metrics: answer rate, completion rate, retry rate,
        average duration, status distribution.
        """
        base = select(Call).join(Attendance, Call.attendance_id == Attendance.id).where(
            and_(Attendance.date >= date_from, Attendance.date <= date_to)
        )
        calls_result = await self.db.execute(base)
        calls = list(calls_result.scalars().all())

        if not calls:
            return {
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "total_calls": 0,
                "status_distribution": {},
                "answer_rate": 0.0,
                "completion_rate": 0.0,
                "retry_rate": 0.0,
                "average_duration_seconds": None,
            }

        total = len(calls)

        # Status distribution
        status_dist: Dict[str, int] = {}
        for c in calls:
            key = c.status.value
            status_dist[key] = status_dist.get(key, 0) + 1

        completed = status_dist.get(CallStatus.COMPLETED.value, 0)
        answered = completed + status_dist.get(CallStatus.ANSWERED.value, 0)
        retried = sum(1 for c in calls if c.retry_count > 0)
        durations = [c.duration_seconds for c in calls if c.duration_seconds and c.duration_seconds > 0]

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "total_calls": total,
            "status_distribution": status_dist,
            "answer_rate": round(answered / total * 100, 1),
            "completion_rate": round(completed / total * 100, 1),
            "retry_rate": round(retried / total * 100, 1),
            "average_duration_seconds": round(sum(durations) / len(durations), 1) if durations else None,
        }

    # ── Absence Reason Distribution ────────────────────────────────────────

    async def get_absence_reason_distribution(
        self,
        date_from: date,
        date_to: date,
    ) -> List[Dict[str, Any]]:
        """
        Count of absence reports grouped by category.
        """
        q = select(
            AbsenceReport.category,
            func.count(AbsenceReport.id).label("count"),
        ).join(Call, AbsenceReport.call_id == Call.id).join(
            Attendance, Call.attendance_id == Attendance.id
        ).where(
            and_(Attendance.date >= date_from, Attendance.date <= date_to)
        ).group_by(AbsenceReport.category).order_by(func.count(AbsenceReport.id).desc())

        rows = (await self.db.execute(q)).all()
        return [{"category": row.category.value, "count": row.count} for row in rows]

    # ── Reports ────────────────────────────────────────────────────────────

    async def get_daily_report(self, report_date: date) -> Dict[str, Any]:
        """Daily absence report for a single date."""
        summary = await self.get_summary(report_date, report_date)
        reasons = await self.get_absence_reason_distribution(report_date, report_date)
        return {
            "report_type": "daily",
            "report_date": report_date.isoformat(),
            "summary": summary,
            "absence_reasons": reasons,
        }

    async def get_weekly_report(self, end_date: date) -> Dict[str, Any]:
        """Weekly report ending on the given date (7-day window)."""
        start = end_date - timedelta(days=6)
        summary = await self.get_summary(start, end_date)
        trends = await self.get_daily_trends(start, end_date)
        reasons = await self.get_absence_reason_distribution(start, end_date)
        call_metrics = await self.get_call_metrics(start, end_date)
        return {
            "report_type": "weekly",
            "date_from": start.isoformat(),
            "date_to": end_date.isoformat(),
            "summary": summary,
            "daily_trends": trends,
            "absence_reasons": reasons,
            "call_metrics": call_metrics,
        }

    async def get_monthly_report(self, year: int, month: int) -> Dict[str, Any]:
        """Monthly report for the given year/month."""
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        summary = await self.get_summary(start, end)
        trends = await self.get_daily_trends(start, end)
        reasons = await self.get_absence_reason_distribution(start, end)
        call_metrics = await self.get_call_metrics(start, end)
        return {
            "report_type": "monthly",
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "summary": summary,
            "daily_trends": trends,
            "absence_reasons": reasons,
            "call_metrics": call_metrics,
        }

    async def get_followup_report(
        self,
        date_from: date,
        date_to: date,
    ) -> Dict[str, Any]:
        """Follow-up report: counts by type, priority, status."""
        q = select(FollowUp).join(Call, FollowUp.call_id == Call.id).join(
            Attendance, Call.attendance_id == Attendance.id
        ).where(
            and_(Attendance.date >= date_from, Attendance.date <= date_to)
        )
        result = await self.db.execute(q)
        followups = list(result.scalars().all())

        by_type: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}
        by_status: Dict[str, int] = {}

        for fu in followups:
            t = fu.type.value
            p = fu.priority.value
            s = fu.status.value
            by_type[t] = by_type.get(t, 0) + 1
            by_priority[p] = by_priority.get(p, 0) + 1
            by_status[s] = by_status.get(s, 0) + 1

        return {
            "report_type": "followup",
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "total": len(followups),
            "by_type": by_type,
            "by_priority": by_priority,
            "by_status": by_status,
        }

    async def get_unreachable_report(
        self,
        date_from: date,
        date_to: date,
    ) -> Dict[str, Any]:
        """Report on parents that could not be reached after all retries."""
        q = select(
            Call.id,
            Call.student_id,
            Call.phone_number_called,
            Call.retry_count,
            Call.updated_at,
        ).join(Attendance, Call.attendance_id == Attendance.id).where(
            and_(
                Attendance.date >= date_from,
                Attendance.date <= date_to,
                Call.status == CallStatus.UNREACHABLE,
            )
        ).order_by(Attendance.date.desc())

        result = await self.db.execute(q)
        rows = result.all()

        return {
            "report_type": "unreachable",
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "total": len(rows),
            "entries": [
                {
                    "call_id": r.id,
                    "student_id": r.student_id,
                    "phone_number": r.phone_number_called,
                    "retry_count": r.retry_count,
                    "last_updated": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ],
        }
