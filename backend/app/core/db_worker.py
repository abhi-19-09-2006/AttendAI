"""
Database utilities for RQ worker tasks.

Provides clean session lifecycle management for async tasks running in worker context.
Each RQ task must own its database session.
"""
import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger("db_utils")


@asynccontextmanager
async def get_worker_session() -> AsyncSession:
    """
    Provide a fresh AsyncSession for worker tasks.

    Usage:
        async with get_worker_session() as session:
            # do work
            await session.commit()

    This is the bridge between synchronous RQ execution and async app services.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session rollback due to error: {str(e)}")
            raise
        finally:
            await session.close()


def run_async_task(coro):
    """
    Execute an async coroutine from sync RQ task context.

    Safely creates event loop if needed for Python 3.12+.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - create new event loop for this task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    else:
        # Loop already running - should not happen in RQ context
        # but handle gracefully
        logger.warning("Unexpected: event loop already running in RQ task")
        raise RuntimeError(
            "Cannot run async task with existing event loop. "
            "RQ tasks should run in sync context."
        )
