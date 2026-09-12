"""
AttendAI FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.api import health, auth, users, students, parents, attendance, calls, absence_reports, followups

# Setup logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("AttendAI backend starting up...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    yield

    # Shutdown
    logger.info("AttendAI backend shutting down...")


app = FastAPI(
    title="AttendAI API",
    description="AI-Powered Automated Student Absence Communication Platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(students.router, prefix="/api/students", tags=["Students"])
app.include_router(parents.router, prefix="/api/parents", tags=["Parents"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(absence_reports.router, prefix="/api/absence-reports", tags=["Absence Reports"])
app.include_router(followups.router, prefix="/api/followups", tags=["Follow-ups"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AttendAI API",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.APP_ENV
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "type": type(exc).__name__
            }
        )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
