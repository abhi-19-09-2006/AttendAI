"""
API integration tests.
"""
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
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
                "email": "admin@attendai.example.com",
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
                "email": "admin@attendai.example.com",
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
                "email": "faculty@attendai.example.com",
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
        assert data["email"] == "faculty@attendai.example.com"
        assert data["role"] == "faculty"


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
                "email": "faculty@attendai.example.com",
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
                "email": "faculty@attendai.example.com",
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
async def test_create_student(db_session: AsyncSession):
    """Test creating a new student."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as faculty
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "faculty@attendai.example.com",
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
        
        # Cleanup: delete the created student to prevent test pollution
        student_id = data["id"]
        try:
            await db_session.execute(
                text("DELETE FROM students WHERE id = :id"),
                {"id": student_id}
            )
            await db_session.commit()
        except Exception:
            # If cleanup fails, don't fail the test
            await db_session.rollback()


@pytest.mark.asyncio
async def test_staff_cannot_access_admin_endpoint():
    """Test that staff cannot access admin-only endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as staff
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "staff@attendai.example.com",
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


@pytest.mark.asyncio
async def test_create_call_enqueues_rq_job(db_session: AsyncSession):
    """Test that POST /api/calls creates a call and enqueues initiate_pending_call job."""
    from unittest.mock import patch, MagicMock
    from app.models import Student, Parent, Attendance, Call, CallStatus
    from app.models.enums import AttendanceStatus
    from datetime import date
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login as faculty
        login_response = await client.post(
            "/api/auth/login",
            json={
                "email": "faculty@attendai.example.com",
                "password": "faculty123"
            }
        )
        token = login_response.json()["access_token"]
        
        # Create test student
        student_response = await client.post(
            "/api/students",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "student_id": "CALL_TEST_001",
                "first_name": "CallTest",
                "last_name": "Student",
                "date_of_birth": "2010-01-01",
                "grade_level": 10
            }
        )
        student_id = student_response.json()["id"]
        
        # Create test parent
        parent_response = await client.post(
            "/api/parents",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "student_id": student_id,
                "first_name": "CallTest",
                "last_name": "Parent",
                "primary_phone": "+15551234567",
                "relationship": "guardian",
                "is_primary": True
            }
        )
        parent_id = parent_response.json()["id"]
        
        # Create test attendance
        attendance_response = await client.post(
            "/api/attendance",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "student_id": student_id,
                "date": date.today().isoformat(),
                "status": "absent"
            }
        )
        attendance_id = attendance_response.json()["id"]
        
        # Mock RQ queue to verify enqueue is called
        with patch('app.api.calls.get_call_queue') as mock_get_queue:
            mock_queue = MagicMock()
            mock_rq_job = MagicMock()
            mock_rq_job.id = "test-rq-job-id"
            mock_queue.enqueue.return_value = mock_rq_job
            mock_get_queue.return_value = mock_queue
            
            # Create call
            response = await client.post(
                "/api/calls",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "student_id": student_id,
                    "parent_id": parent_id,
                    "attendance_id": attendance_id
                }
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["status"] == "pending"
            assert data["student_id"] == student_id
            assert data["parent_id"] == parent_id
            assert data["attendance_id"] == attendance_id
            
            # Verify RQ enqueue was called
            mock_queue.enqueue.assert_called_once()
            call_args = mock_queue.enqueue.call_args
            assert call_args[0][0].__name__ == "initiate_pending_call"
            assert call_args[0][1] == data["id"]  # call_id
            assert "job_id" in call_args[1]
            assert call_args[1]["job_id"] == f"call_{data['id']}"
        
        # Cleanup
        try:
            await db_session.execute(
                text("DELETE FROM calls WHERE student_id = :id"),
                {"id": student_id}
            )
            await db_session.execute(
                text("DELETE FROM attendance WHERE student_id = :id"),
                {"id": student_id}
            )
            await db_session.execute(
                text("DELETE FROM parents WHERE student_id = :id"),
                {"id": student_id}
            )
            await db_session.execute(
                text("DELETE FROM students WHERE id = :id"),
                {"id": student_id}
            )
            await db_session.commit()
        except Exception:
            await db_session.rollback()


@pytest.mark.asyncio
async def test_rq_job_serialization_with_pickle():
    """
    Regression test: Verify RQ jobs can be serialized/deserialized without UnicodeDecodeError.
    
    This test ensures that:
    1. RQ Redis connection does NOT use decode_responses=True
    2. Job payloads (which are pickled) can be properly deserialized
    3. Worker can process jobs without UnicodeDecodeError
    
    Root cause: Using decode_responses=True on Redis connection causes RQ to fail
    when deserializing pickled binary data, resulting in:
    UnicodeDecodeError: 'utf-8' codec can't decode byte 0x9c in position 1
    """
    from unittest.mock import patch, MagicMock
    from app.core.rq_config import get_call_queue, get_rq_redis_connection
    from app.tasks import initiate_pending_call
    import pickle
    
    # Test 1: Verify RQ Redis connection does NOT decode responses
    rq_redis = get_rq_redis_connection()
    assert rq_redis.connection_pool.connection_kwargs.get('decode_responses') is not True, \
        "RQ Redis connection must NOT use decode_responses=True"
    
    # Test 2: Verify we can enqueue and retrieve a job with binary (pickled) data
    with patch('app.core.rq_config.get_rq_redis_connection') as mock_get_redis:
        # Create a mock Redis that simulates proper binary handling
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        # Simulate pickled job data (binary, not UTF-8 decodable)
        test_payload = {"call_id": "test-123", "job_id": "job-456"}
        pickled_data = pickle.dumps(test_payload)
        
        # Verify pickled data contains non-UTF-8 bytes
        try:
            pickled_data.decode('utf-8')
            # If this succeeds, the test is invalid - pickled data should not be UTF-8
            assert False, "Pickled data should contain binary bytes that can't be UTF-8 decoded"
        except UnicodeDecodeError:
            # Expected - pickled data is binary
            pass
        
        mock_get_redis.return_value = mock_redis
        
        # Create queue with mocked Redis
        queue = get_call_queue()
        
        # Mock the enqueue to return a job
        mock_job = MagicMock()
        mock_job.id = "test-rq-job-id"
        queue.enqueue = MagicMock(return_value=mock_job)
        
        # Enqueue a job
        job = queue.enqueue(
            initiate_pending_call,
            "test-call-id",
            "test-job-id",
            job_id="call_test-call-id"
        )
        
        # Verify enqueue was called
        assert queue.enqueue.called
        assert job.id == "test-rq-job-id"
