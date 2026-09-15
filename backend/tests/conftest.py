"""
Pytest fixtures and configuration.
"""
import pytest
import asyncio
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import exc
from fastapi.testclient import TestClient

# Set test DATABASE_URL before importing app
os.environ["DATABASE_URL"] = "postgresql+asyncpg://attendai:attendai_dev_password@localhost:5432/attendai_db"

from app.core.database import Base
from app.core.config import settings
from app.main import app

# Import all models to ensure they're registered with SQLAlchemy
from app.models import (
    User, Student, Parent, Attendance, CallCampaign, Call, CallAttempt,
    AbsenceReport, FollowUp, AuditLog, Job
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
    """Create a new database session for a test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create test client for FastAPI endpoints."""
    return TestClient(app)
