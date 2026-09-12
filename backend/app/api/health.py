"""
Health Check Endpoints
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("health")
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    environment: str
    version: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""
    status: str
    timestamp: datetime
    environment: str
    version: str
    services: Dict[str, Any]


@router.get("", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if service is running.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        environment=settings.APP_ENV,
        version="0.1.0"
    )


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check including service dependencies.
    """
    services = {
        "api": {"status": "healthy", "message": "API is operational"},
        "database": {"status": "pending", "message": "Database connection not yet implemented"},
        "redis": {"status": "pending", "message": "Redis connection not yet implemented"},
        "vapi": {"status": "pending", "message": "Vapi integration not yet implemented"}
    }

    # Overall status (all must be healthy)
    overall_status = "healthy" if all(
        svc["status"] == "healthy" for svc in services.values()
    ) else "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        environment=settings.APP_ENV,
        version="0.1.0",
        services=services
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    Returns 200 when service is ready to accept traffic.
    """
    return {"status": "ready"}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    Returns 200 if service is alive.
    """
    return {"status": "alive"}
