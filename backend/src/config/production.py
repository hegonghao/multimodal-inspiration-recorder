"""
Production configuration settings
Security-hardened settings for production deployment
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class ProductionConfig(BaseSettings):
    """Production environment configuration"""

    # ==================== Application ====================
    APP_NAME: str = "Multimodal Inspiration Recorder"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    TESTING: bool = False

    # ==================== Server ====================
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")  # CPU cores * 2 + 1
    RELOAD: bool = False  # Never reload in production

    # ==================== Security ====================
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # Required in production
    ALLOWED_HOSTS: list[str] = Field(
        default=["*"],  # Should be restricted in actual deployment
        env="ALLOWED_HOSTS",
    )
    CORS_ORIGINS: list[str] = Field(
        default=["https://yourdomain.com"],
        env="CORS_ORIGINS",
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # API Keys (must be set via environment variables)
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    DEEPGRAM_API_KEY: Optional[str] = Field(default=None, env="DEEPGRAM_API_KEY")
    NOTION_API_KEY: Optional[str] = Field(default=None, env="NOTION_API_KEY")
    NOTION_DATABASE_ID: Optional[str] = Field(default=None, env="NOTION_DATABASE_ID")

    # ==================== Database ====================
    DATABASE_URL: str = Field(
        default="sqlite:///./data/inspirations.db",
        env="DATABASE_URL",
    )
    DATABASE_ECHO: bool = False  # No SQL logging in production
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600  # 1 hour

    # ==================== Redis ====================
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL",
    )
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5

    # ==================== Logging ====================
    LOG_LEVEL: str = "INFO"  # Production should use INFO or WARNING
    LOG_FORMAT: str = "json"  # Structured logging for production
    LOG_FILE: Optional[str] = Field(default="logs/app.log", env="LOG_FILE")
    LOG_MAX_SIZE: int = 100 * 1024 * 1024  # 100MB
    LOG_BACKUP_COUNT: int = 10
    LOG_ROTATION: str = "midnight"  # Rotate daily at midnight

    # ==================== File Storage ====================
    UPLOAD_DIR: str = Field(default="./data/uploads", env="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list[str] = [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".mp3",
        ".wav",
        ".m4a",
    ]

    # ==================== API Rate Limiting ====================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # Requests per window
    RATE_LIMIT_WINDOW: int = 60  # Window size in seconds (1 minute)

    # ==================== Performance ====================
    # Timeouts
    REQUEST_TIMEOUT: int = 30  # 30 seconds
    EXTERNAL_API_TIMEOUT: int = 30  # 30 seconds

    # Caching
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300  # 5 minutes
    CACHE_MAX_SIZE: int = 1000

    # Background Tasks
    ARQ_REDIS_URL: str = Field(
        default="redis://localhost:6379/1",
        env="ARQ_REDIS_URL",
    )
    ARQ_MAX_JOBS: int = 100
    ARQ_JOB_TIMEOUT: int = 600  # 10 minutes

    # ==================== Monitoring ====================
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")

    ENABLE_HEALTHCHECK: bool = True
    HEALTHCHECK_PATH: str = "/health"

    # Sentry (Error Tracking)
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    SENTRY_ENVIRONMENT: str = "production"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # 10% of transactions

    # ==================== Feature Flags ====================
    ENABLE_VOICE_INPUT: bool = True
    ENABLE_IMAGE_OCR: bool = True
    ENABLE_TEXT_INPUT: bool = True
    ENABLE_NOTION_SYNC: bool = True
    ENABLE_AI_PROCESSING: bool = True

    # ==================== Validators ====================

    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        """Ensure secret key is set and secure in production"""
        if not v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be set and at least 32 characters in production"
            )
        return v

    @validator("WORKERS")
    def validate_workers(cls, v):
        """Ensure reasonable worker count"""
        if v < 1:
            raise ValueError("WORKERS must be at least 1")
        if v > 32:
            raise ValueError("WORKERS should not exceed 32 for most deployments")
        return v

    @validator("CORS_ORIGINS")
    def validate_cors_origins(cls, v):
        """Warn if CORS is too permissive"""
        if "*" in v:
            import warnings

            warnings.warn(
                "CORS_ORIGINS includes '*' which is insecure for production. "
                "Please specify allowed origins explicitly."
            )
        return v

    class Config:
        env_file = ".env.production"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Singleton instance
_config: Optional[ProductionConfig] = None


def get_production_config() -> ProductionConfig:
    """Get production configuration singleton"""
    global _config
    if _config is None:
        _config = ProductionConfig()
    return _config


# Deployment checklist
PRODUCTION_CHECKLIST = {
    "security": [
        "SECRET_KEY is set and secure (min 32 chars)",
        "CORS_ORIGINS is restricted to allowed domains",
        "API keys are set via environment variables (not in code)",
        "DEBUG is set to False",
        "ALLOWED_HOSTS is restricted",
        "HTTPS is enforced",
        "Security headers are configured",
        "SQL injection protection is enabled",
    ],
    "database": [
        "Database backups are configured",
        "Database connection pool is sized appropriately",
        "Database indexes are created",
        "Database migrations are applied",
        "WAL mode is enabled for SQLite",
    ],
    "performance": [
        "Image cache limits are configured",
        "Rate limiting is enabled",
        "Request timeouts are configured",
        "Background tasks are working",
        "Redis connection is stable",
    ],
    "monitoring": [
        "Health check endpoint is working",
        "Metrics collection is enabled",
        "Error tracking (Sentry) is configured",
        "Log aggregation is set up",
        "Alerts are configured",
    ],
    "reliability": [
        "Graceful shutdown is implemented",
        "Error handling covers all endpoints",
        "Retry logic is in place for external APIs",
        "Circuit breakers are configured",
        "Timeouts are set for all operations",
    ],
    "testing": [
        "All tests pass (unit + integration)",
        "Performance tests pass",
        "Security tests pass",
        "Load testing completed",
        "End-to-end tests pass",
    ],
}


def validate_production_readiness() -> dict:
    """Validate production readiness and return status"""
    config = get_production_config()
    issues = []
    warnings = []

    # Security checks
    if config.DEBUG:
        issues.append("DEBUG must be False in production")

    if len(config.SECRET_KEY) < 32:
        issues.append("SECRET_KEY must be at least 32 characters")

    if not config.OPENAI_API_KEY and config.ENABLE_AI_PROCESSING:
        warnings.append("OPENAI_API_KEY not set but AI processing is enabled")

    if not config.NOTION_API_KEY and config.ENABLE_NOTION_SYNC:
        warnings.append("NOTION_API_KEY not set but Notion sync is enabled")

    # Performance checks
    if config.WORKERS < 2:
        warnings.append("WORKERS count is low, consider increasing for production")

    if not config.RATE_LIMIT_ENABLED:
        warnings.append("Rate limiting is disabled, consider enabling for production")

    # Monitoring checks
    if not config.SENTRY_DSN:
        warnings.append("SENTRY_DSN not set, error tracking will not work")

    return {
        "ready": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "checklist": PRODUCTION_CHECKLIST,
    }
