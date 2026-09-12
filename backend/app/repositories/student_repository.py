"""
Student repository.
"""
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Student
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    """Student repository."""

    def __init__(self, db: AsyncSession):
        super().__init__(Student, db)

    async def get_by_student_id(self, student_id: str) -> Optional[Student]:
        """Get student by student ID."""
        result = await self.db.execute(
            select(Student).where(Student.student_id == student_id)
        )
        return result.scalar_one_or_none()

    async def search(self, query: str, skip: int = 0, limit: int = 50) -> List[Student]:
        """Search students by name or student ID."""
        search_query = select(Student).where(
            or_(
                Student.first_name.ilike(f"%{query}%"),
                Student.last_name.ilike(f"%{query}%"),
                Student.student_id.ilike(f"%{query}%")
            )
        ).offset(skip).limit(limit)

        result = await self.db.execute(search_query)
        return list(result.scalars().all())
