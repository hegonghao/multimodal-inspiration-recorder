"""
Models package

Exports all SQLAlchemy models and Pydantic schemas
"""

from src.models.inspiration import (
    InspirationRecord,
    InspirationRecordCreate,
    InspirationRecordUpdate,
    InspirationRecordResponse,
    InspirationRecordListResponse,
    InputType,
    SyncStatus,
    AIProcessingStatus,
    parse_category_tags,
    serialize_category_tags,
)
from src.models.sync_queue import (
    SyncQueue,
    SyncTaskCreate,
    SyncTaskUpdate,
    SyncTaskResponse,
    SyncStatusResponse,
    SyncQueueListResponse,
    SyncOperation,
    SyncQueueStatus,
    SyncPriority,
)
from src.models.user_preferences import (
    UserPreferences,
    UserPreferencesUpdate,
    UserPreferencesResponse,
    NotionConnectionTest,
    LLMConnectionTest,
    ConnectionTestResponse,
)

__all__ = [
    # Models
    "InspirationRecord",
    "SyncQueue",
    "UserPreferences",
    # Inspiration schemas
    "InspirationRecordCreate",
    "InspirationRecordUpdate",
    "InspirationRecordResponse",
    "InspirationRecordListResponse",
    # Sync schemas
    "SyncTaskCreate",
    "SyncTaskUpdate",
    "SyncTaskResponse",
    "SyncStatusResponse",
    "SyncQueueListResponse",
    # Preferences schemas
    "UserPreferencesUpdate",
    "UserPreferencesResponse",
    "NotionConnectionTest",
    "LLMConnectionTest",
    "ConnectionTestResponse",
    # Enums
    "InputType",
    "SyncStatus",
    "AIProcessingStatus",
    "SyncOperation",
    "SyncQueueStatus",
    "SyncPriority",
    # Utilities
    "parse_category_tags",
    "serialize_category_tags",
]
