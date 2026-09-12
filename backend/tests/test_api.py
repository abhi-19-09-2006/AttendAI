"""
API integration tests.
"""
import pytest
from fastapi import status
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login with seeded user."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "admin@attendai.local",
                "password": "admin123"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/login",
            json={
                "email": "admin@attendai.local",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user():
    """Test getting current user information."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login first
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "faculty@attendai.local",
                "password": "faculty123"
            }
        )
        token = login_response.json()["access_token"]

        # Get current user
        response = await client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "faculty@attendai.local"
        assert data["role"] == "FACULTY"


@pytest.mark.asyncio
async def test_list_students_unauthorized():
    """Test that unauthorized access is denied."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/students")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_list_students_authorized():
    """Test listing students with authorization."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as faculty
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "faculty@attendai.local",
                "password": "faculty123"
            }
        )
        token = login_response.json()["access_token"]

        # List students
        response = await client.get(
            "/api/students",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


@pytest.mark.asyncio
async def test_get_todays_absentees():
    """Test getting today's absentees."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as faculty
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "faculty@attendai.local",
                "password": "faculty123"
            }
        )
        token = login_response.json()["access_token"]

        # Get today's absentees
        response = await client.get(
            "/api/attendance/absentees/today",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_student():
    """Test creating a new student."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as faculty
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "faculty@attendai.local",
                "password": "faculty123"
            }
        )
        token = login_response.json()["access_token"]

        # Create student
        response = await client.post(
            "/api/students",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "student_id": "TEST999",
                "first_name": "Test",
                "last_name": "Student",
                "date_of_birth": "2010-01-01",
                "grade_level": 8
            }
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["student_id"] == "TEST999"
        assert data["first_name"] == "Test"


@pytest.mark.asyncio
async def test_staff_cannot_access_admin_endpoint():
    """Test that staff cannot access admin-only endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as staff
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "staff@attendai.local",
                "password": "staff123"
            }
        )
        token = login_response.json()["access_token"]

        # Try to list users (admin only)
        response = await client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
