"""
Database connection management
异步数据库连接管理，支持 SQLite WAL 模式
"""

import logging
from typing import AsyncGenerator

from sqlalchemy import event, pool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings
from src.database.base import Base

logger = logging.getLogger(__name__)

# Global async engine instance
engine: AsyncEngine | None = None

# Async session factory
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def _configure_sqlite_pragma(dbapi_conn, connection_record) -> None:
    """
    Configure SQLite pragma settings for optimal performance

    - WAL mode: Write-Ahead Logging for better concurrency
    - NORMAL synchronous: Balance between safety and performance
    - Foreign keys: Enforce referential integrity
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


def create_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine with optimized settings

    Returns:
        AsyncEngine: Configured async database engine
    """
    global engine

    if engine is not None:
        return engine

    logger.info(f"Creating database engine: {settings.DATABASE_URL}")

    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,  # Log SQL queries in debug mode
        poolclass=pool.NullPool if "sqlite" in settings.DATABASE_URL else pool.QueuePool,
        pool_size=5 if "sqlite" not in settings.DATABASE_URL else None,
        max_overflow=10 if "sqlite" not in settings.DATABASE_URL else None,
        pool_pre_ping=True,  # Verify connections before using
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    )

    # Configure SQLite-specific settings
    if "sqlite" in settings.DATABASE_URL:
        event.listens_for(engine.sync_engine, "connect")(_configure_sqlite_pragma)
        logger.info("SQLite WAL mode enabled")

    return engine


def create_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Create async session factory

    Returns:
        async_sessionmaker: Session factory for creating database sessions
    """
    global AsyncSessionLocal, engine

    if AsyncSessionLocal is not None:
        return AsyncSessionLocal

    if engine is None:
        engine = create_engine()

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Prevent lazy loading after commit
        autocommit=False,
        autoflush=False,
    )

    logger.info("Async session factory created")
    return AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection function for FastAPI

    Provides async database session with automatic commit/rollback

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session
    """
    if AsyncSessionLocal is None:
        create_session_factory()

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database: create tables and insert default data

    Creates all tables defined in SQLAlchemy models if they don't exist.
    This function is idempotent - safe to call multiple times.
    """
    global engine

    if engine is None:
        engine = create_engine()

    logger.info("Initializing database...")

    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

        # Insert default data (e.g., UserPreferences)
        # This will be implemented after creating the models
        # async with AsyncSessionLocal() as session:
        #     # Check if default preferences exist
        #     result = await session.execute(
        #         select(UserPreferences).where(UserPreferences.id == 1)
        #     )
        #     if not result.scalar_one_or_none():
        #         default_prefs = UserPreferences(id=1)
        #         session.add(default_prefs)
        #         await session.commit()
        #         logger.info("Default user preferences created")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_db() -> None:
    """
    Close database connections and cleanup resources

    Should be called on application shutdown to gracefully close
    all database connections and clean up the connection pool.
    """
    global engine, AsyncSessionLocal

    if engine is not None:
        logger.info("Closing database connections...")
        await engine.dispose()
        engine = None
        AsyncSessionLocal = None
        logger.info("Database connections closed")


# Initialize on module import
def init_connection() -> None:
    """Initialize database connection on module import"""
    create_engine()
    create_session_factory()
