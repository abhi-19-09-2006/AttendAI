"""
Pytest fixtures and configuration.
"""
import pytest
import asyncio
import os
from datetime import date
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import exc, text
from fastapi.testclient import TestClient

# Set test DATABASE_URL before importing app
os.environ["DATABASE_URL"] = "postgresql+asyncpg://attendai:attendai_dev_password@localhost:5432/attendai_db"

from app.core.database import Base, engine as app_engine
from app.core.config import settings
from app.core.security import get_password_hash
from app.main import app

# Import all models to ensure they're registered with SQLAlchemy
from app.models import (
    User, Student, Parent, Attendance, CallCampaign, Call, CallAttempt,
    AbsenceReport, FollowUp, AuditLog, Job, UserRole
)

# Credentials the API auth tests expect to be seeded (see scripts/seed_data.py)
SEED_USERS = (
    ("admin@attendai.example.com", "admin123", "Admin User", UserRole.ADMIN, "Administration"),
    ("faculty@attendai.example.com", "faculty123", "Jane Faculty", UserRole.FACULTY, "Mathematics"),
    ("staff@attendai.example.com", "staff123", "John Staff", UserRole.STAFF, "Office"),
)


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine and initialize schema once per session."""
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        db_url,
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables from SQLAlchemy metadata (idempotent)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        # If any error, log and continue (tables may already exist or have enum conflicts)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Schema creation encountered an issue (may be acceptable): {e}")

    yield engine

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test with proper isolation.
    
    Uses a connection-scoped transaction that's rolled back after the test,
    even if the test code commits. This ensures test isolation.
    """
    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create test client for FastAPI endpoints."""
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
async def seeded_db(test_engine):
    """Reset relational tables and seed the auth users the API tests expect.

    Several model tests commit their own rows (explicit ``commit()`` bypasses
    the ``db_session`` rollback), so the shared database accumulates test rows
    that collide on re-run.  Truncating in FK-safe order at session start makes
    the suite reproducible from any prior state.  Then the three login users
    (documented in scripts/seed_data.py) and a student are seeded so the auth
    API tests can authenticate and list students.
    """
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        await session.execute(text(
            "TRUNCATE absence_reports, followups, jobs, call_attempts, calls, "
            "attendance, call_campaigns, parents, students, audit_logs, users CASCADE"
        ))
        for email, password, full_name, role, department in SEED_USERS:
            session.add(User(
                email=email,
                hashed_password=get_password_hash(password),
                full_name=full_name,
                role=role,
                department=department,
                is_active=True,
            ))
        session.add(Student(
            student_id="AUTHSEED001",
            first_name="Auth",
            last_name="Seed",
            date_of_birth=date(2010, 1, 1),
            grade_level=8,
            is_active=True,
        ))
        await session.commit()


@pytest.fixture(autouse=True)
async def _dispose_app_engine():
    """Dispose the shared app engine before and after each test.

    pytest-asyncio runs each test on a fresh event loop, but the app engine
    pools asyncpg connections.  Reusing a pooled connection from a previous
    (already closed) loop on Windows crashes with
    ``AttributeError: 'NoneType' object has no attribute 'send'`` because the
    old ProactorEventLoop's ``_proactor`` is gone.  Disposing before each test
    ensures no stale connections exist, and disposing after ensures cleanup.
    """
    await app_engine.dispose()
    yield
    await app_engine.dispose()
