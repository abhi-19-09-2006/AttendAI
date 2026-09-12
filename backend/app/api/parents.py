"""
Parent management router.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.auth import require_faculty
from app.schemas import ParentResponse, ParentCreate, ParentUpdate
from app.models import User, Parent, Student

router = APIRouter()


@router.post("", response_model=ParentResponse, status_code=status.HTTP_201_CREATED)
async def create_parent(
    parent_data: ParentCreate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new parent/guardian.

    - **student_id**: ID of the student
    - **relationship**: Relationship to student
    - **first_name**: Parent's first name
    - **last_name**: Parent's last name
    - **primary_phone**: Primary phone number
    """
    # Verify student exists
    result = await db.execute(select(Student).where(Student.id == parent_data.student_id))
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    parent = Parent(**parent_data.model_dump())
    db.add(parent)
    await db.flush()
    await db.refresh(parent)
    await db.commit()

    return parent


@router.get("", response_model=List[ParentResponse])
async def list_parents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    student_id: str = Query(None, description="Filter by student ID"),
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """
    List parents with optional filtering by student.

    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    - **student_id**: Optional student ID filter
    """
    query = select(Parent).offset(skip).limit(limit)

    if student_id:
        query = query.where(Parent.student_id == student_id)

    result = await db.execute(query)
    parents = list(result.scalars().all())

    return parents


@router.get("/{parent_id}", response_model=ParentResponse)
async def get_parent(
    parent_id: str,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Get parent by ID."""
    result = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent not found"
        )

    return parent


@router.put("/{parent_id}", response_model=ParentResponse)
async def update_parent(
    parent_id: str,
    parent_update: ParentUpdate,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Update parent information."""
    result = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent not found"
        )

    for field, value in parent_update.model_dump(exclude_unset=True).items():
        setattr(parent, field, value)

    await db.commit()
    await db.refresh(parent)

    return parent


@router.delete("/{parent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parent(
    parent_id: str,
    current_user: User = Depends(require_faculty),
    db: AsyncSession = Depends(get_db)
):
    """Delete parent."""
    result = await db.execute(select(Parent).where(Parent.id == parent_id))
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent not found"
        )

    await db.delete(parent)
    await db.commit()

    return None
