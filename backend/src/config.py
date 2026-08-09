"""
Configuration Management
应用配置管理，支持环境变量和多环境配置
"""

import os
import json
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "多模输入灵感记录器"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/inspirations.db"

    # Redis (for caching and rate limiting)
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: Optional[str] = None

    # LLM API Configuration
    OPENAI_API_KEY: str = "not-needed-for-ollama"  # Default for local Ollama
    OPENAI_BASE_URL: str = "http://localhost:11434/v1"
    OPENAI_MODEL: str = "llama3.1"
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TEMPERATURE: float = 0.7

    # Alternative LLM providers
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None

    # Request Configuration
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour

    # Cost Control
    MAX_DAILY_TOKENS: int = 100000
    COST_PER_TOKEN: float = 0.000002  # Approximate cost

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Monitoring
    METRICS_ENABLED: bool = True
    SENTRY_DSN: Optional[str] = None

    # Legacy compatibility alias. The canonical setting is ALLOWED_ORIGINS.
    CORS_ORIGINS: Optional[str] = None

    # Notion Integration
    # Note: .env uses NOTION_TOKEN, config uses NOTION_API_KEY (for consistency with OpenAI)
    # Both are accepted, NOTION_TOKEN takes precedence
    NOTION_TOKEN: Optional[str] = None  # Primary
    NOTION_API_KEY: Optional[str] = None  # Alias for backward compatibility
    NOTION_DATABASE_ID: Optional[str] = None
    NOTION_SYNC_ENABLED: bool = False
    NOTION_SYNC_INTERVAL_MINUTES: int = 15
    NOTION_SYNC_BATCH_SIZE: int = 10

    # Speech-to-Text (Deepgram)
    DEEPGRAM_API_KEY: Optional[str] = None

    # OCR (PaddleOCR-VL)
    PADDLEOCR_API_URL: Optional[str] = None
    PADDLEOCR_TOKEN: Optional[str] = None
    PADDLEOCR_MODEL: str = "PP-OCRv6"
    PADDLEOCR_POLL_INTERVAL: float = 5.0
    PADDLEOCR_JOB_TIMEOUT: float = 300.0
    PADDLEOCR_REQUEST_TIMEOUT: float = 60.0

    # Feature Flags
    ENABLE_VOICE_INPUT: bool = True
    ENABLE_IMAGE_OCR: bool = True
    ENABLE_TEXT_INPUT: bool = True
    ENABLE_NOTION_SYNC: bool = False
    ENABLE_AI_PROCESSING: bool = True

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("["):
                return json.loads(v)
            return [host.strip() for host in v.split(",")]
        return v

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Validate settings that would make a production container unsafe."""
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be false in production")
            if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.startswith("dev-"):
                raise ValueError("SECRET_KEY must be a random value of at least 32 characters")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        enable_decoding=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
