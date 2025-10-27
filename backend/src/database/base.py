"""
SQLAlchemy declarative base and common mixins
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Base class for all database models"""

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""

    created_at: Column[DateTime] = Column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Column[DateTime] = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class IDMixin:
    """Mixin for auto-incrementing integer primary key"""

    id: Column[Integer] = Column(Integer, primary_key=True, autoincrement=True)


class TableNameMixin:
    """Mixin for automatic table name generation from class name"""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (convert CamelCase to snake_case)"""
        import re

        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()
