"""
Analytics and reports router.

All endpoints require faculty or admin role.
"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_faculty
from app.models import User
from app.services.analytics_service import AnalyticsService

router = APIRouter()


def _today() -> date:
    return date.today()


@router.get("/summary")
async def get_summary(
    date_from: date = Query(None, description="Start date (defaults to 30 days ago)"),
    date_to: date = Query(None, description="End date (defaults to today)"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard summary: counts, rates, and key metrics for a date range."""
    end = date_to or _today()
    start = date_from or (end - __import__("datetime").timedelta(days=29))
    svc = AnalyticsService(db)
    return await svc.get_summary(start, end)


@router.get("/trends")
async def get_trends(
    date_from: date = Query(None),
    date_to: date = Query(None),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Day-by-day absentee and call trends."""
    end = date_to or _today()
    start = date_from or (end - __import__("datetime").timedelta(days=29))
    svc = AnalyticsService(db)
    return await svc.get_daily_trends(start, end)


@router.get("/call-metrics")
async def get_call_metrics(
    date_from: date = Query(None),
    date_to: date = Query(None),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Call-specific metrics: answer rate, completion rate, retry rate, duration."""
    end = date_to or _today()
    start = date_from or (end - __import__("datetime").timedelta(days=29))
    svc = AnalyticsService(db)
    return await svc.get_call_metrics(start, end)


@router.get("/absence-reasons")
async def get_absence_reasons(
    date_from: date = Query(None),
    date_to: date = Query(None),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Absence reason distribution by category."""
    end = date_to or _today()
    start = date_from or (end - __import__("datetime").timedelta(days=29))
    svc = AnalyticsService(db)
    return await svc.get_absence_reason_distribution(start, end)


@router.get("/reports/daily")
async def daily_report(
    report_date: date = Query(None, description="Report date (defaults to today)"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Generate a daily absence report."""
    svc = AnalyticsService(db)
    return await svc.get_daily_report(report_date or _today())


@router.get("/reports/weekly")
async def weekly_report(
    end_date: date = Query(None, description="End date of the week (defaults to today)"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Generate a weekly absence report (7-day window)."""
    svc = AnalyticsService(db)
    return await svc.get_weekly_report(end_date or _today())


@router.get("/reports/monthly")
async def monthly_report(
    year: int = Query(None, description="Year (defaults to current year)"),
    month: int = Query(None, description="Month 1-12 (defaults to current month)", ge=1, le=12),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Generate a monthly absence report."""
    today = _today()
    svc = AnalyticsService(db)
    return await svc.get_monthly_report(year or today.year, month or today.month)


@router.get("/reports/followup")
async def followup_report(
    date_from: date = Query(None),
    date_to: date = Query(None),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Follow-up report: counts by type, priority, status."""
    end = date_to or _today()
    start = date_from or (end - __import__("datetime").timedelta(days=29))
    svc = AnalyticsService(db)
    return await svc.get_followup_report(start, end)


@router.get("/reports/unreachable")
async def unreachable_report(
    date_from: date = Query(None),
    date_to: date = Query(None),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db),
):
    """Unreachable-parent report: calls that exhausted all retries."""
    end = date_to or _today()
    start = date_from or (end - __import__("datetime").timedelta(days=29))
    svc = AnalyticsService(db)
    return await svc.get_unreachable_report(start, end)
