"""
Health endpoint tests.
"""
from fastapi import status


def test_root_endpoint(client):
    """Test root endpoint returns basic info."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "AttendAI API"
    assert data["status"] == "running"
    assert "version" in data


def test_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "environment" in data
    assert "version" in data


def test_detailed_health_check(client):
    """Test detailed health check endpoint."""
    response = client.get("/health/detailed")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "api" in data["services"]


def test_readiness_check(client):
    """Test readiness probe endpoint."""
    response = client.get("/health/ready")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ready"


def test_liveness_check(client):
    """Test liveness probe endpoint."""
    response = client.get("/health/live")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "alive"
