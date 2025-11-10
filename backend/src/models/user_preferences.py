"""
UserPreferences Model and Schemas

Stores user configuration and integration credentials
for Notion API, LLM services, and application settings.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    CheckConstraint,
)
from sqlalchemy.sql import func

from src.database.base import Base


# ==================== SQLAlchemy Model ====================


class UserPreferences(Base):
    """
    UserPreferences table stores user configuration.
    Single-user mode: always uses id=1
    """

    __tablename__ = "user_preferences"

    # Primary key (always 1 for single-user mode)
    id = Column(Integer, primary_key=True, default=1)

    # Notion integration
    notion_token = Column(String(500), nullable=True)  # Encrypted
    notion_database_id = Column(String(100), nullable=True)

    # LLM API configuration
    openai_base_url = Column(
        String(500), nullable=False, default="http://localhost:11434/v1"
    )
    openai_api_key = Column(String(500), nullable=True)  # Encrypted
    openai_model = Column(String(100), nullable=False, default="llama3.1")

    # Deepgram API configuration
    deepgram_api_key = Column(
        String(500),
        nullable=False,
        default="44e90ac460009a2a7cd9adfee1a65de28aba654b"
    )  # Encrypted

    # Security settings
    encryption_enabled = Column(Boolean, nullable=False, default=False)

    # Sync settings
    sync_interval = Column(Integer, nullable=False, default=1800)  # 30 minutes
    sync_on_network = Column(Boolean, nullable=False, default=True)

    # UI settings
    ui_language = Column(String(10), nullable=False, default="zh_CN")
    theme_mode = Column(String(10), nullable=False, default="system")

    # Feature settings
    max_voice_duration = Column(Integer, nullable=False, default=300)  # 5 minutes
    auto_classify = Column(Boolean, nullable=False, default=True)
    auto_summarize = Column(Boolean, nullable=False, default=True)

    # Timestamp
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_single_user"),
        CheckConstraint(
            "sync_interval = 0 OR sync_interval >= 300",
            name="chk_sync_interval",
        ),
        CheckConstraint(
            "max_voice_duration >= 60 AND max_voice_duration <= 600",
            name="chk_voice_duration",
        ),
        CheckConstraint(
            "ui_language IN ('zh_CN', 'en_US')", name="chk_ui_language"
        ),
        CheckConstraint(
            "theme_mode IN ('system', 'light', 'dark')", name="chk_theme_mode"
        ),
    )

    def __repr__(self) -> str:
        return f"<UserPreferences(id={self.id}, openai_model='{self.openai_model}', sync_interval={self.sync_interval})>"


# ==================== Pydantic Schemas ====================


class UserPreferencesUpdate(BaseModel):
    """Schema for updating user preferences"""

    # Notion integration (empty string will be converted to None)
    notion_token: Optional[str] = Field(None, max_length=500)
    notion_database_id: Optional[str] = Field(None, max_length=100)

    # LLM API configuration
    openai_base_url: Optional[str] = Field(None, pattern=r"^https?://.*")
    openai_api_key: Optional[str] = Field(None, max_length=500)
    openai_model: Optional[str] = Field(None, min_length=1, max_length=100)

    # Deepgram API configuration
    deepgram_api_key: Optional[str] = Field(None, max_length=500)

    # Security settings
    encryption_enabled: Optional[bool] = None

    # Sync settings
    sync_interval: Optional[int] = Field(None, ge=0, le=86400)  # 0-24 hours
    sync_on_network: Optional[bool] = None

    # UI settings
    ui_language: Optional[str] = Field(None, pattern=r"^(zh_CN|en_US)$")
    theme_mode: Optional[str] = Field(None, pattern=r"^(system|light|dark)$")

    # Feature settings
    max_voice_duration: Optional[int] = Field(None, ge=60, le=600)  # 1-10 minutes
    auto_classify: Optional[bool] = None
    auto_summarize: Optional[bool] = None

    @field_validator("sync_interval")
    @classmethod
    def validate_sync_interval(cls, v: Optional[int]) -> Optional[int]:
        """Ensure sync interval is either 0 (disabled) or >= 5 minutes"""
        if v is not None and v > 0 and v < 300:
            raise ValueError("同步间隔不能小于5分钟(300秒),设为0可禁用自动同步")
        return v

    @field_validator("notion_token", "notion_database_id", "openai_api_key", "deepgram_api_key")
    @classmethod
    def empty_string_to_none(cls, v: Optional[str]) -> Optional[str]:
        """Convert empty strings to None"""
        if v == "":
            return None
        return v

    @field_validator("notion_token")
    @classmethod
    def validate_notion_token(cls, v: Optional[str]) -> Optional[str]:
        """Validate Notion token format"""
        if v and not (v.startswith("secret_") or v.startswith("ntn_")):
            raise ValueError("Notion token格式不正确,应以'secret_'或'ntn_'开头")
        # Validate minimum length when present
        if v and len(v) < 50:
            raise ValueError("Notion token长度至少需要50个字符")
        return v

    @field_validator("notion_database_id")
    @classmethod
    def validate_notion_database_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate Notion database ID format"""
        if v and len(v) < 32:
            raise ValueError("Notion database ID长度至少需要32个字符")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "notion_token": "secret_abc123...",
                "notion_database_id": "a1b2c3d4e5f67890",
                "openai_base_url": "http://localhost:11434/v1",
                "openai_model": "llama3.1",
                "deepgram_api_key": "44e90ac460009a2a7cd9adfee1a65de28aba654b",
                "sync_interval": 1800,
                "max_voice_duration": 300,
                "auto_classify": True,
                "auto_summarize": True,
            }
        }
    }


class UserPreferencesResponse(BaseModel):
    """Schema for user preferences responses"""

    id: int
    notion_database_id: Optional[str] = None
    openai_base_url: str
    openai_model: str
    encryption_enabled: bool
    sync_interval: int
    sync_on_network: bool
    ui_language: str
    theme_mode: str
    max_voice_duration: int
    auto_classify: bool
    auto_summarize: bool
    updated_at: datetime

    # Sensitive fields are excluded (notion_token, openai_api_key)
    # They are write-only and never returned in responses

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "notion_database_id": "a1b2c3d4e5f67890",
                "openai_base_url": "http://localhost:11434/v1",
                "openai_model": "llama3.1",
                "encryption_enabled": True,
                "sync_interval": 1800,
                "sync_on_network": True,
                "ui_language": "zh_CN",
                "theme_mode": "system",
                "max_voice_duration": 300,
                "auto_classify": True,
                "auto_summarize": True,
                "updated_at": "2025-10-27T09:00:00Z",
            }
        },
    }


class NotionConnectionTest(BaseModel):
    """Schema for testing Notion connection"""

    notion_token: str = Field(..., min_length=40)
    notion_database_id: str = Field(..., min_length=32)

    model_config = {
        "json_schema_extra": {
            "example": {
                "notion_token": "secret_abc123...",
                "notion_database_id": "a1b2c3d4e5f67890",
            }
        }
    }


class LLMConnectionTest(BaseModel):
    """Schema for testing LLM connection"""

    openai_base_url: str = Field(..., pattern=r"^https?://.*")
    openai_api_key: Optional[str] = None
    openai_model: str = Field(..., min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "openai_base_url": "http://localhost:11434/v1",
                "openai_model": "llama3.1",
            }
        }
    }


class ConnectionTestResponse(BaseModel):
    """Schema for connection test responses"""

    success: bool
    message: str
    details: Optional[dict] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "连接成功",
                "details": {"response_time_ms": 250, "model": "llama3.1"},
            }
        }
    }
