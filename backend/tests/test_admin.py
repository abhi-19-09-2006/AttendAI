"""
Focused tests for Phase 12: Admin Features

Tests admin dashboard, user management, and campaign administration endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.models import User, UserRole, CallCampaign, CampaignStatus


@pytest.mark.asyncio
async def test_admin_dashboard_requires_admin_role():
    """Admin dashboard should only be accessible to admin users."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as faculty
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "faculty@attendai.example.com", "password": "faculty123"},
        )
        token = login_response.json()["access_token"]

        # Try to access admin dashboard
        response = await client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_dashboard_success():
    """Admin dashboard should return system metrics for admin users."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "admin@attendai.example.com", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # Access admin dashboard
        response = await client.get(
            "/api/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "users" in data
        assert "students" in data
        assert "campaigns" in data
        assert "calls" in data
        assert "jobs" in data

        # Check user metrics
        assert "total" in data["users"]
        assert "admins" in data["users"]
        assert "faculty" in data["users"]
        assert "staff" in data["users"]

        # Check campaign metrics
        assert "total" in data["campaigns"]
        assert "active" in data["campaigns"]
        assert "paused" in data["campaigns"]
        assert "completed" in data["campaigns"]


@pytest.mark.asyncio
async def test_admin_reset_password_requires_admin_role(db_session: AsyncSession):
    """Password reset should only be accessible to admin users."""
    # Get faculty user
    result = await db_session.execute(
        select(User).where(User.email == "faculty@attendai.example.com")
    )
    faculty_user = result.scalar_one_or_none()

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as faculty
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "faculty@attendai.example.com", "password": "faculty123"},
        )
        token = login_response.json()["access_token"]

        # Try to reset password
        response = await client.post(
            f"/api/admin/users/{faculty_user.id}/reset-password",
            json={"new_password": "newpassword123"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_reset_password_success(db_session: AsyncSession):
    """Admin should be able to reset user passwords."""
    # Get staff user to reset
    result = await db_session.execute(
        select(User).where(User.email == "staff@attendai.example.com")
    )
    staff_user = result.scalar_one_or_none()

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "admin@attendai.example.com", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # Reset password
        response = await client.post(
            f"/api/admin/users/{staff_user.id}/reset-password",
            json={"new_password": "newpassword123"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert "password reset successfully" in response.json()["message"].lower()

        # Reset back to original password for other tests
        await client.post(
            f"/api/admin/users/{staff_user.id}/reset-password",
            json={"new_password": "staff123"},
            headers={"Authorization": f"Bearer {token}"},
        )


@pytest.mark.asyncio
async def test_admin_reset_password_rejects_short_password(db_session: AsyncSession):
    """Password reset should reject passwords shorter than 8 characters."""
    # Get staff user
    result = await db_session.execute(
        select(User).where(User.email == "staff@attendai.example.com")
    )
    staff_user = result.scalar_one_or_none()

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "admin@attendai.example.com", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # Try to reset with short password
        response = await client.post(
            f"/api/admin/users/{staff_user.id}/reset-password",
            json={"new_password": "short"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_admin_update_campaign_status_requires_admin(db_session: AsyncSession):
    """Campaign status updates should only be accessible to admin users."""
    # Get faculty user
    result = await db_session.execute(
        select(User).where(User.email == "faculty@attendai.example.com")
    )
    faculty_user = result.scalar_one_or_none()

    # Create a campaign
    campaign = CallCampaign(
        name="Test Admin Campaign",
        description="Test Description",
        status=CampaignStatus.DRAFT,
        created_by=faculty_user.id,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as faculty
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "faculty@attendai.example.com", "password": "faculty123"},
        )
        token = login_response.json()["access_token"]

        # Try to update campaign status
        response = await client.patch(
            f"/api/admin/campaigns/{campaign.id}/status",
            json={"status": "active"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_update_campaign_status_success(db_session: AsyncSession):
    """Admin should be able to update campaign status with valid transitions."""
    # Get admin user
    result = await db_session.execute(
        select(User).where(User.email == "admin@attendai.example.com")
    )
    admin_user = result.scalar_one_or_none()

    # Create a campaign in draft status
    campaign = CallCampaign(
        name="Test Admin Campaign 2",
        description="Test Description",
        status=CampaignStatus.DRAFT,
        created_by=admin_user.id,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "admin@attendai.example.com", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # Update campaign status to active
        response = await client.patch(
            f"/api/admin/campaigns/{campaign.id}/status",
            json={"status": "active"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["new_status"] == "active"

        # Pause the campaign
        response = await client.patch(
            f"/api/admin/campaigns/{campaign.id}/status",
            json={"status": "paused"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["new_status"] == "paused"


@pytest.mark.asyncio
async def test_admin_update_campaign_status_invalid_transition(db_session: AsyncSession):
    """Campaign status updates should reject invalid transitions."""
    # Get admin user
    result = await db_session.execute(
        select(User).where(User.email == "admin@attendai.example.com")
    )
    admin_user = result.scalar_one_or_none()

    # Create a completed campaign
    campaign = CallCampaign(
        name="Completed Campaign",
        description="Test Description",
        status=CampaignStatus.COMPLETED,
        created_by=admin_user.id,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "admin@attendai.example.com", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # Try to reactivate completed campaign (invalid transition)
        response = await client.patch(
            f"/api/admin/campaigns/{campaign.id}/status",
            json={"status": "active"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_list_users():
    """Admin should be able to list all users."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "admin@attendai.example.com", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # List users
        response = await client.get(
            "/api/users",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0


@pytest.mark.asyncio
async def test_admin_list_campaigns():
    """Admin should be able to list all campaigns."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as admin
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "admin@attendai.example.com", "password": "admin123"},
        )
        token = login_response.json()["access_token"]

        # List campaigns
        response = await client.get(
            "/api/calls/campaigns",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        campaigns = response.json()
        assert isinstance(campaigns, list)
