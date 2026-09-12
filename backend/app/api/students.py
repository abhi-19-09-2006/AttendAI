"""
Student management router.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_faculty
from app.schemas import StudentResponse, StudentCreate, StudentUpdate
from app.repositories.student_repository import StudentRepository
from app.models import User, Student

router = APIRouter()


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create_student(
    student_data: StudentCreate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new student.

    - **student_id**: Unique student identifier
    - **first_name**: Student's first name
    - **last_name**: Student's last name
    - **date_of_birth**: Student's date of birth
    - **grade_level**: Grade level (1-12)
    """
    student_repo = StudentRepository(db)

    # Check if student ID already exists
    existing = await student_repo.get_by_student_id(student_data.student_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID already exists"
        )

    student = Student(
        **student_data.model_dump(),
        is_active=True
    )

    created_student = await student_repo.create(student)
    await db.commit()

    return created_student


@router.get("", response_model=List[StudentResponse])
async def list_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str = Query(None, description="Search by name or student ID"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    List all students with pagination and optional search.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **search**: Optional search query
    """
    student_repo = StudentRepository(db)

    if search:
        students = await student_repo.search(search, skip=skip, limit=limit)
    else:
        students = await student_repo.get_multi(skip=skip, limit=limit)

    return students


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Get student by ID."""
    student_repo = StudentRepository(db)
    student = await student_repo.get(student_id)

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    return student


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    student_update: StudentUpdate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Update student information."""
    student_repo = StudentRepository(db)
    student = await student_repo.get(student_id)

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    updated_student = await student_repo.update(
        student,
        **student_update.model_dump(exclude_unset=True)
    )

    await db.commit()

    return updated_student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(
    student_id: str,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Delete student (soft delete by setting is_active=False)."""
    student_repo = StudentRepository(db)
    student = await student_repo.get(student_id)

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    # Soft delete
    await student_repo.update(student, is_active=False)
    await db.commit()

    return None
