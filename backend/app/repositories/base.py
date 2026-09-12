"""
Base repository class with common CRUD operations.
"""
from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: str) -> Optional[ModelType]:
        """Get a single record by ID."""
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[List[Any]] = None
    ) -> List[ModelType]:
        """Get multiple records with pagination."""
        query = select(self.model)

        if filters:
            query = query.where(*filters)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: Optional[List[Any]] = None) -> int:
        """Count total records."""
        query = select(func.count()).select_from(self.model)

        if filters:
            query = query.where(*filters)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, obj_in: ModelType) -> ModelType:
        """Create a new record."""
        self.db.add(obj_in)
        await self.db.flush()
        await self.db.refresh(obj_in)
        return obj_in

    async def update(self, db_obj: ModelType, **update_data) -> ModelType:
        """Update a record."""
        for field, value in update_data.items():
            if value is not None and hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, id: str) -> bool:
        """Delete a record."""
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.flush()
            return True
        return False
