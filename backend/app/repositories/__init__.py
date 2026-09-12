"""
Repositories package.
"""
from app.repositories.base import BaseRepository
from app.repositories.user_repository import UserRepository
from app.repositories.student_repository import StudentRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "StudentRepository",
]
