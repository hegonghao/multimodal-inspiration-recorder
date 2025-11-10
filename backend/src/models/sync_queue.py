"""
SyncQueue Model and Schemas

Manages background synchronization tasks with Notion API,
including retry logic and priority handling.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.sql import func

from src.database.base import Base


# ==================== Enums ====================


class SyncOperation(str, Enum):
    """Sync operation type"""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class SyncQueueStatus(int, Enum):
    """Sync task status"""

    PENDING = 0
    PROCESSING = 1
    COMPLETED = 2
    FAILED = 3


class SyncPriority(int, Enum):
    """Sync task priority"""

    NORMAL = 0
    HIGH = 1
    URGENT = 2


# ==================== SQLAlchemy Model ====================


class SyncQueue(Base):
    """
    SyncQueue table manages background synchronization tasks
    with retry logic, priority handling, and exponential backoff.
    """

    __tablename__ = "sync_queue"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key to inspiration_records
    record_id = Column(
        Integer,
        ForeignKey("inspiration_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Operation details
    operation = Column(String(20), nullable=False)
    status = Column(Integer, nullable=False, default=0, index=True)

    # Retry management
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=5)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    error_message = Column(Text, nullable=True)

    # Priority
    priority = Column(Integer, nullable=False, default=0, index=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "operation IN ('create', 'update', 'delete')", name="chk_operation"
        ),
        CheckConstraint("status BETWEEN 0 AND 3", name="chk_status"),
        CheckConstraint(
            "retry_count >= 0 AND retry_count <= max_retries",
            name="chk_retry_count",
        ),
        CheckConstraint("priority BETWEEN 0 AND 2", name="chk_priority"),
        CheckConstraint("max_retries >= 1", name="chk_max_retries"),
        # Composite index for efficient queue processing
        Index(
            "idx_queue_processing", status, priority.desc(), created_at.asc()
        ),
        # Index for failed task retry scheduling
        Index("idx_retry_schedule", next_retry_at),
    )

    def __repr__(self) -> str:
        return f"<SyncQueue(id={self.id}, record_id={self.record_id}, operation={self.operation}, status={self.status})>"

    def calculate_next_retry(self) -> datetime:
        """
        Calculate next retry time using exponential backoff.
        Formula: min(4 * (2 ** retry_count), 60) seconds
        Results: 4s, 8s, 16s, 32s, 60s (capped)
        """
        from datetime import timedelta

        delay_seconds = min(4 * (2**self.retry_count), 60)
        return datetime.utcnow() + timedelta(seconds=delay_seconds)


# ==================== Pydantic Schemas ====================


class SyncTaskCreate(BaseModel):
    """Schema for creating a new sync task"""

    record_id: int = Field(..., gt=0, description="关联的灵感记录ID")
    operation: SyncOperation
    priority: SyncPriority = SyncPriority.NORMAL

    model_config = {
        "json_schema_extra": {
            "example": {
                "record_id": 1,
                "operation": "create",
                "priority": 1,
            }
        }
    }


class SyncTaskUpdate(BaseModel):
    """Schema for updating a sync task"""

    status: Optional[SyncQueueStatus] = None
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    error_message: Optional[str] = Field(None, max_length=1000)
    priority: Optional[SyncPriority] = None

    @field_validator("error_message")
    @classmethod
    def truncate_error_message(cls, v: Optional[str]) -> Optional[str]:
        """Truncate error message to prevent database bloat"""
        if v and len(v) > 1000:
            return v[:997] + "..."
        return v


class SyncTaskResponse(BaseModel):
    """Schema for sync task responses"""

    id: int
    record_id: int
    operation: SyncOperation
    status: SyncQueueStatus
    retry_count: int
    max_retries: int
    last_attempt_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None
    priority: SyncPriority
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "record_id": 1,
                "operation": "create",
                "status": 2,
                "retry_count": 0,
                "max_retries": 5,
                "last_attempt_at": "2025-10-27T10:31:00Z",
                "next_retry_at": None,
                "error_message": None,
                "priority": 1,
                "created_at": "2025-10-27T10:30:05Z",
                "completed_at": "2025-10-27T10:31:15Z",
            }
        },
    }


class SyncStatusResponse(BaseModel):
    """Schema for overall sync status"""

    total_records: int
    synced_count: int
    pending_count: int
    failed_count: int
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None
    sync_enabled: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_records": 100,
                "synced_count": 85,
                "pending_count": 10,
                "failed_count": 5,
                "last_sync_at": "2025-10-27T10:00:00Z",
                "next_sync_at": "2025-10-27T10:30:00Z",
                "sync_enabled": True,
            }
        }
    }


class SyncQueueListResponse(BaseModel):
    """Schema for sync queue list"""

    tasks: list[SyncTaskResponse]
    total_count: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "tasks": [
                    {
                        "id": 1,
                        "record_id": 1,
                        "operation": "create",
                        "status": 0,
                    }
                ],
                "total_count": 10,
            }
        }
    }
