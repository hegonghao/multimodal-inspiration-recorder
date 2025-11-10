"""
InspirationRecord Model and Schemas

Defines the core data model for storing multimodal inspiration records
with SQLAlchemy ORM and Pydantic validation schemas.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Index,
    CheckConstraint,
)
from sqlalchemy.sql import func

from src.database.base import Base


# ==================== Enums ====================


class InputType(str, Enum):
    """Input method for inspiration capture"""

    VOICE = "voice"
    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"  # Added: PDF document support


class SyncStatus(int, Enum):
    """Synchronization status with Notion"""

    PENDING = 0
    SYNCING = 1
    SYNCED = 2
    FAILED = 3
    CONFLICT = 4


class AIProcessingStatus(int, Enum):
    """AI processing status for classification and summarization"""

    PENDING = 0
    PROCESSING = 1
    COMPLETED = 2
    FAILED = 3


# ==================== SQLAlchemy Model ====================


class InspirationRecord(Base):
    """
    InspirationRecord table stores user-generated inspirations
    from multiple input sources (voice, text, image) with AI-generated
    metadata (categories, summaries) and sync tracking.
    """

    __tablename__ = "inspiration_records"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Core content fields
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Plain text content
    content_markdown = Column(Text, nullable=True)  # Markdown-formatted content (for OCR/PDF)
    input_type = Column(String(20), nullable=False, index=True)

    # AI-generated metadata
    category_tags = Column(Text, nullable=True)  # JSON array as string
    summary = Column(Text, nullable=True)

    # Notion sync tracking
    notion_page_id = Column(String(100), nullable=True, unique=True, index=True)
    sync_status = Column(Integer, nullable=False, default=0, index=True)

    # Timestamps and versioning
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )
    version = Column(Integer, nullable=False, default=1)

    # Media file paths (local storage)
    audio_file_path = Column(String(500), nullable=True)
    image_file_path = Column(String(500), nullable=True)
    pdf_file_path = Column(String(500), nullable=True)  # Added: PDF file path
    ocr_confidence = Column(Float, nullable=True)
    page_count = Column(Integer, nullable=True)  # Added: Number of pages (for PDF)
    processing_options = Column(Text, nullable=True)  # JSON: OCR options (chart recognition, etc.)

    # AI processing status
    ai_processing_status = Column(Integer, nullable=False, default=0, index=True)
    ai_error_message = Column(Text, nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "input_type IN ('voice', 'text', 'image', 'pdf')", name="chk_input_type"
        ),
        CheckConstraint("sync_status BETWEEN 0 AND 4", name="chk_sync_status"),
        CheckConstraint("version > 0", name="chk_version_positive"),
        CheckConstraint(
            "ai_processing_status BETWEEN 0 AND 3", name="chk_ai_status"
        ),
        CheckConstraint("ocr_confidence IS NULL OR (ocr_confidence BETWEEN 0 AND 1)", name="chk_ocr_confidence"),
        CheckConstraint("page_count IS NULL OR page_count > 0", name="chk_page_count_positive"),
        # Performance indexes
        Index("idx_created_at_desc", created_at.desc()),
        Index("idx_updated_at_desc", updated_at.desc()),
        Index("idx_sync_pending", sync_status, updated_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<InspirationRecord(id={self.id}, title='{self.title[:30]}...', input_type={self.input_type})>"


# ==================== Pydantic Schemas ====================


class InspirationRecordCreate(BaseModel):
    """Schema for creating a new inspiration record"""

    title: str = Field(..., min_length=1, max_length=200, description="灵感标题")
    content: str = Field(..., min_length=1, max_length=10000, description="原始内容")
    input_type: InputType
    audio_file_path: Optional[str] = Field(None, max_length=500)
    image_file_path: Optional[str] = Field(None, max_length=500)
    ocr_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

    @field_validator("content")
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Ensure content has minimum 10 characters"""
        stripped = v.strip()
        if len(stripped) < 10:
            raise ValueError("内容至少需要10个字符")
        return stripped

    @field_validator("audio_file_path")
    @classmethod
    def validate_audio_path(cls, v: Optional[str], info) -> Optional[str]:
        """Validate audio file path for voice input"""
        if info.data.get("input_type") == InputType.VOICE and not v:
            raise ValueError("语音输入必须提供音频文件路径")
        return v

    @field_validator("image_file_path")
    @classmethod
    def validate_image_path(cls, v: Optional[str], info) -> Optional[str]:
        """Validate image file path for image input"""
        if info.data.get("input_type") == InputType.IMAGE and not v:
            raise ValueError("图片输入必须提供图片文件路径")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "AI产品创意:智能会议助手",
                "content": "今天开会时想到可以做一个AI会议助手,自动记录会议内容、生成摘要和待办事项。",
                "input_type": "voice",
                "audio_file_path": "/storage/audio/20251027_103000.m4a",
            }
        }
    }


class InspirationRecordUpdate(BaseModel):
    """Schema for updating an existing inspiration record"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=10, max_length=10000)
    category_tags: Optional[List[str]] = Field(None, max_length=10)
    summary: Optional[str] = Field(None, max_length=200)
    version: int = Field(..., ge=1, description="当前版本号(用于乐观锁)")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 10:
            raise ValueError("内容至少需要10个字符")
        return v.strip() if v else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "AI产品创意:智能会议助手(更新)",
                "summary": "AI会议助手产品构想:实时转写+智能摘要+待办提醒",
                "version": 1,
            }
        }
    }


class InspirationRecordResponse(BaseModel):
    """Schema for inspiration record responses"""

    id: int
    title: str
    content: str
    content_markdown: Optional[str] = None  # Added: Markdown content
    input_type: InputType
    category_tags: Optional[List[str]] = None
    summary: Optional[str] = None
    notion_page_id: Optional[str] = None
    sync_status: SyncStatus
    created_at: datetime
    updated_at: datetime
    version: int
    audio_file_path: Optional[str] = None
    image_file_path: Optional[str] = None
    pdf_file_path: Optional[str] = None  # Added: PDF file path
    ocr_confidence: Optional[float] = None
    page_count: Optional[int] = None  # Added: Number of pages
    processing_options: Optional[str] = None  # Added: Processing options
    ai_processing_status: AIProcessingStatus
    ai_error_message: Optional[str] = None

    @field_validator("category_tags", mode="before")
    @classmethod
    def parse_category_tags_json(cls, v):
        """Parse category_tags from JSON string if needed"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "AI产品创意:智能会议助手",
                "content": "今天开会时想到可以做一个AI会议助手...",
                "input_type": "voice",
                "category_tags": ["产品创意", "技术灵感"],
                "summary": "AI会议助手产品构想:实时转写+智能摘要+待办提醒",
                "notion_page_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "sync_status": 2,
                "created_at": "2025-10-27T10:30:00Z",
                "updated_at": "2025-10-27T10:31:15Z",
                "version": 1,
                "audio_file_path": "/storage/audio/20251027_103000.m4a",
                "image_file_path": None,
                "ocr_confidence": None,
                "ai_processing_status": 2,
                "ai_error_message": None,
            }
        },
    }


class InspirationRecordListResponse(BaseModel):
    """Schema for paginated list of inspiration records"""

    data: List[InspirationRecordResponse]
    pagination: dict

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "id": 1,
                        "title": "AI产品创意",
                        "content": "...",
                        "input_type": "voice",
                    }
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 5,
                    "total_count": 100,
                    "has_next": True,
                    "has_prev": False,
                },
            }
        }
    }


# ==================== Helper Functions ====================


def parse_category_tags(tags_json: Optional[str]) -> Optional[List[str]]:
    """Parse category tags from JSON string to list"""
    if not tags_json:
        return None

    import json

    try:
        tags = json.loads(tags_json)
        return tags if isinstance(tags, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


def serialize_category_tags(tags: Optional[List[str]]) -> Optional[str]:
    """Serialize category tags from list to JSON string"""
    if not tags:
        return None

    import json

    return json.dumps(tags, ensure_ascii=False)
