"""
ARQ Task Queue Worker

Background worker for processing Notion sync tasks asynchronously.
Handles create, update, and delete operations with retry logic.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import structlog
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from arq.cron import cron
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.connection import create_session_factory
from src.models.inspiration import InspirationRecord, SyncStatus
from src.models.sync_queue import (
    SyncQueue,
    SyncOperation,
    SyncQueueStatus,
)
from src.services.notion_sync import NotionSyncService

logger = structlog.get_logger(__name__)


# ==================== Worker Configuration ====================


class WorkerSettings:
    """ARQ worker configuration"""

    # Redis connection
    @staticmethod
    def _parse_redis_url():
        """Parse Redis URL to extract host and port"""
        redis_url_parts = settings.REDIS_URL.split("://")[-1]  # redis:6379/0
        if ":" in redis_url_parts:
            host_port = redis_url_parts.split("/")[0]  # redis:6379
            host, port_str = host_port.split(":")
            return host, int(port_str)
        else:
            host = redis_url_parts.split("/")[0]
            return host, 6379

    _host, _port = _parse_redis_url()

    redis_settings = RedisSettings(
        host=_host,
        port=_port,
        password=settings.REDIS_PASSWORD,
    )

    # Worker settings
    max_jobs = 10  # Process up to 10 jobs concurrently
    job_timeout = 300  # 5 minutes timeout per job
    max_tries = 5  # Max retry attempts
    keep_result = 3600  # Keep job results for 1 hour

    # Queue name
    queue_name = "notion_sync_queue"


# ==================== Database Helper ====================


async def get_db_session() -> AsyncSession:
    """Get database session for worker tasks"""
    session_factory = create_session_factory()
    return session_factory()


# ==================== Sync Task Processing ====================


async def sync_inspiration_to_notion(
    ctx: dict,
    sync_task_id: int,
) -> dict:
    """
    Process a single sync task from the queue.

    This is the main ARQ job function that:
    1. Fetches the sync task and associated record from database
    2. Performs the appropriate Notion API operation
    3. Updates sync status in database
    4. Handles errors and retry logic

    Args:
        ctx: ARQ context (contains worker state)
        sync_task_id: ID of the SyncQueue task to process

    Returns:
        Dict with sync result information

    Raises:
        Exception: Re-raises exceptions for ARQ retry handling
    """
    logger.info(
        "sync_task_started",
        sync_task_id=sync_task_id,
        job_id=ctx.get("job_id"),
    )

    session: Optional[AsyncSession] = None
    notion_service: Optional[NotionSyncService] = None

    try:
        # Get database session
        session = await get_db_session()

        # Fetch sync task from queue
        result = await session.execute(
            select(SyncQueue).where(SyncQueue.id == sync_task_id)
        )
        sync_task = result.scalar_one_or_none()

        if not sync_task:
            logger.error(
                "sync_task_not_found",
                sync_task_id=sync_task_id,
            )
            return {
                "status": "error",
                "message": "Sync task not found",
                "sync_task_id": sync_task_id,
            }

        # Check if task is already completed or processing
        if sync_task.status in [SyncQueueStatus.COMPLETED, SyncQueueStatus.PROCESSING]:
            # Convert status int to enum for .name access
            status_enum = SyncQueueStatus(sync_task.status) if isinstance(sync_task.status, int) else sync_task.status
            logger.warning(
                "sync_task_already_processed",
                sync_task_id=sync_task_id,
                status=sync_task.status,
            )
            return {
                "status": "skipped",
                "message": f"Task already {status_enum.name}",
                "sync_task_id": sync_task_id,
            }

        # Update task status to PROCESSING
        await session.execute(
            update(SyncQueue)
            .where(SyncQueue.id == sync_task_id)
            .values(
                status=SyncQueueStatus.PROCESSING,
                last_attempt_at=datetime.utcnow(),
            )
        )
        await session.commit()

        # Fetch associated inspiration record
        result = await session.execute(
            select(InspirationRecord).where(
                InspirationRecord.id == sync_task.record_id
            )
        )
        record = result.scalar_one_or_none()

        if not record:
            logger.error(
                "inspiration_record_not_found",
                record_id=sync_task.record_id,
                sync_task_id=sync_task_id,
            )
            await _mark_task_failed(
                session,
                sync_task,
                "Inspiration record not found",
            )
            return {
                "status": "error",
                "message": "Inspiration record not found",
                "sync_task_id": sync_task_id,
            }

        # Check if Notion sync is enabled
        # Priority: user preferences > environment variables from settings
        from src.models.user_preferences import UserPreferences

        prefs_result = await session.execute(
            select(UserPreferences).where(UserPreferences.id == 1)
        )
        prefs = prefs_result.scalar_one_or_none()

        # Determine Notion credentials
        notion_token = None
        database_id = None

        # Check user preferences first, fallback to environment variables
        if prefs and prefs.notion_token and prefs.notion_token.strip():
            # User has configured Notion in preferences
            notion_token = prefs.notion_token
            database_id = prefs.notion_database_id
        else:
            # Fallback to environment variables from settings
            notion_token = getattr(settings, 'NOTION_TOKEN', None) or getattr(settings, 'NOTION_API_KEY', None)
            database_id = getattr(settings, 'NOTION_DATABASE_ID', None)

        # Validate credentials
        if not notion_token or not notion_token.strip() or not database_id or not database_id.strip():
            logger.warning(
                "notion_credentials_missing",
                sync_task_id=sync_task_id,
                has_prefs=prefs is not None,
                has_env_token=bool(getattr(settings, 'NOTION_TOKEN', None)),
            )
            await _mark_task_failed(
                session,
                sync_task,
                "Notion credentials not configured in preferences or environment",
            )
            return {
                "status": "skipped",
                "message": "Notion credentials not configured",
                "sync_task_id": sync_task_id,
            }

        # Initialize Notion service with credentials
        try:
            notion_service = NotionSyncService(
                notion_token=notion_token,
                database_id=database_id,
            )
        except ValueError as e:
            logger.error(
                "notion_service_init_failed",
                error=str(e),
                sync_task_id=sync_task_id,
            )
            await _mark_task_failed(
                session,
                sync_task,
                f"Notion service initialization failed: {str(e)}",
            )
            return {
                "status": "error",
                "message": str(e),
                "sync_task_id": sync_task_id,
            }

        # Perform sync operation based on type
        success = False
        error_message = None
        notion_page_id = None

        if sync_task.operation == SyncOperation.CREATE:
            # Create new page in Notion
            notion_page_id = await notion_service.create_page(record)
            if notion_page_id:
                # Update record with Notion page ID
                await session.execute(
                    update(InspirationRecord)
                    .where(InspirationRecord.id == record.id)
                    .values(
                        notion_page_id=notion_page_id,
                        sync_status=SyncStatus.SYNCED,
                    )
                )
                success = True
            else:
                error_message = "Failed to create Notion page"

        elif sync_task.operation == SyncOperation.UPDATE:
            # Update existing page in Notion
            if not record.notion_page_id:
                error_message = "Cannot update: Record has no Notion page ID"
                logger.error(
                    "update_missing_page_id",
                    record_id=record.id,
                    sync_task_id=sync_task_id,
                )
            else:
                success = await notion_service.update_page(
                    record.notion_page_id, record
                )
                if success:
                    # Update sync status
                    await session.execute(
                        update(InspirationRecord)
                        .where(InspirationRecord.id == record.id)
                        .values(sync_status=SyncStatus.SYNCED)
                    )
                else:
                    error_message = "Failed to update Notion page"

        elif sync_task.operation == SyncOperation.DELETE:
            # Archive page in Notion
            if not record.notion_page_id:
                logger.warning(
                    "delete_missing_page_id",
                    record_id=record.id,
                    sync_task_id=sync_task_id,
                )
                # Consider it successful if there's nothing to delete
                success = True
            else:
                success = await notion_service.archive_page(record.notion_page_id)
                if not success:
                    error_message = "Failed to archive Notion page"

        else:
            error_message = f"Unknown sync operation: {sync_task.operation}"
            logger.error(
                "unknown_sync_operation",
                operation=sync_task.operation,
                sync_task_id=sync_task_id,
            )

        # Update task status based on result
        if success:
            # Mark task as completed
            await session.execute(
                update(SyncQueue)
                .where(SyncQueue.id == sync_task_id)
                .values(
                    status=SyncQueueStatus.COMPLETED,
                    completed_at=datetime.utcnow(),
                    error_message=None,
                )
            )
            await session.commit()

            logger.info(
                "sync_task_completed",
                sync_task_id=sync_task_id,
                operation=sync_task.operation,
                record_id=record.id,
                notion_page_id=notion_page_id,
            )

            return {
                "status": "success",
                "sync_task_id": sync_task_id,
                "operation": sync_task.operation,  # Already a string, not enum
                "record_id": record.id,
                "notion_page_id": notion_page_id,
            }

        else:
            # Handle failure with retry logic
            await _handle_task_failure(
                session,
                sync_task,
                error_message or "Unknown error",
            )

            logger.warning(
                "sync_task_failed",
                sync_task_id=sync_task_id,
                operation=sync_task.operation,
                record_id=record.id,
                error=error_message,
                retry_count=sync_task.retry_count + 1,
            )

            # Re-raise exception if retries not exhausted
            if sync_task.retry_count < sync_task.max_retries:
                raise Exception(error_message)

            return {
                "status": "failed",
                "sync_task_id": sync_task_id,
                "error": error_message,
                "retry_count": sync_task.retry_count,
            }

    except Exception as e:
        logger.error(
            "sync_task_exception",
            sync_task_id=sync_task_id,
            error=str(e),
            exc_info=True,
        )

        # Try to mark task as failed in database
        if session and sync_task:
            try:
                await _handle_task_failure(session, sync_task, str(e))
            except Exception as db_error:
                logger.error(
                    "failed_to_update_task_status",
                    sync_task_id=sync_task_id,
                    error=str(db_error),
                )

        # Re-raise for ARQ retry
        raise

    finally:
        # Cleanup
        if notion_service:
            await notion_service.close()

        if session:
            await session.close()


async def _mark_task_failed(
    session: AsyncSession,
    sync_task: SyncQueue,
    error_message: str,
) -> None:
    """Mark a sync task as permanently failed"""
    await session.execute(
        update(SyncQueue)
        .where(SyncQueue.id == sync_task.id)
        .values(
            status=SyncQueueStatus.FAILED,
            error_message=error_message[:1000],  # Truncate to prevent overflow
            retry_count=sync_task.max_retries,  # Exhaust retries
        )
    )

    # Update record sync status
    await session.execute(
        update(InspirationRecord)
        .where(InspirationRecord.id == sync_task.record_id)
        .values(sync_status=SyncStatus.FAILED)
    )

    await session.commit()


async def _handle_task_failure(
    session: AsyncSession,
    sync_task: SyncQueue,
    error_message: str,
) -> None:
    """Handle task failure with retry logic"""
    new_retry_count = sync_task.retry_count + 1

    if new_retry_count >= sync_task.max_retries:
        # Exhausted retries, mark as failed
        await _mark_task_failed(session, sync_task, error_message)
    else:
        # Calculate next retry time with exponential backoff
        next_retry_at = sync_task.calculate_next_retry()

        await session.execute(
            update(SyncQueue)
            .where(SyncQueue.id == sync_task.id)
            .values(
                status=SyncQueueStatus.PENDING,  # Reset to pending for retry
                retry_count=new_retry_count,
                next_retry_at=next_retry_at,
                error_message=error_message[:1000],
            )
        )

        await session.commit()

        logger.info(
            "sync_task_scheduled_retry",
            sync_task_id=sync_task.id,
            retry_count=new_retry_count,
            next_retry_at=next_retry_at.isoformat(),
        )


# ==================== Scheduled Jobs ====================


async def scheduled_sync_check(ctx: dict) -> dict:
    """
    Scheduled job that checks for pending sync tasks and enqueues them.

    This job runs periodically (every 1 minute) to:
    1. Find pending sync tasks that are ready to retry
    2. Enqueue them for processing
    3. Batch process tasks for efficiency

    Args:
        ctx: ARQ context

    Returns:
        Dict with statistics about enqueued tasks
    """
    logger.info("scheduled_sync_check_started")

    session: Optional[AsyncSession] = None
    redis: Optional[ArqRedis] = None

    try:
        session = await get_db_session()
        redis = await create_pool(WorkerSettings.redis_settings)

        # Find pending tasks ready for retry
        now = datetime.utcnow()
        result = await session.execute(
            select(SyncQueue)
            .where(
                SyncQueue.status == SyncQueueStatus.PENDING,
                (SyncQueue.next_retry_at.is_(None)) | (SyncQueue.next_retry_at <= now),
            )
            .order_by(SyncQueue.priority.desc(), SyncQueue.created_at.asc())
            .limit(settings.NOTION_SYNC_BATCH_SIZE)
        )

        pending_tasks = result.scalars().all()

        if not pending_tasks:
            logger.debug("no_pending_sync_tasks")
            return {
                "status": "success",
                "enqueued_count": 0,
            }

        # Enqueue tasks
        enqueued_count = 0
        for task in pending_tasks:
            try:
                await redis.enqueue_job(
                    "sync_inspiration_to_notion",
                    task.id,
                    _queue_name=WorkerSettings.queue_name,
                )
                enqueued_count += 1
                logger.debug(
                    "sync_task_enqueued",
                    sync_task_id=task.id,
                    operation=task.operation,
                )
            except Exception as e:
                logger.error(
                    "failed_to_enqueue_task",
                    sync_task_id=task.id,
                    error=str(e),
                )

        logger.info(
            "scheduled_sync_check_completed",
            enqueued_count=enqueued_count,
            total_pending=len(pending_tasks),
        )

        return {
            "status": "success",
            "enqueued_count": enqueued_count,
        }

    except Exception as e:
        logger.error(
            "scheduled_sync_check_failed",
            error=str(e),
            exc_info=True,
        )
        return {
            "status": "error",
            "error": str(e),
        }

    finally:
        if redis:
            await redis.close()

        if session:
            await session.close()


async def _get_notion_service_for_worker(
    session: AsyncSession,
) -> NotionSyncService | None:
    """Create a Notion service for scheduled worker jobs."""
    from src.models.user_preferences import UserPreferences

    prefs_result = await session.execute(select(UserPreferences).where(UserPreferences.id == 1))
    prefs = prefs_result.scalar_one_or_none()

    if prefs and prefs.notion_token and prefs.notion_token.strip():
        if not prefs.notion_database_id or not prefs.notion_database_id.strip():
            return None
        return NotionSyncService(
            notion_token=prefs.notion_token,
            database_id=prefs.notion_database_id,
        )

    notion_token = getattr(settings, "NOTION_TOKEN", None) or getattr(
        settings,
        "NOTION_API_KEY",
        None,
    )
    database_id = getattr(settings, "NOTION_DATABASE_ID", None)
    if not notion_token or not notion_token.strip() or not database_id or not database_id.strip():
        return None

    return NotionSyncService(notion_token=notion_token, database_id=database_id)


async def scheduled_notion_deletion_check(ctx: dict) -> dict:
    """Remove local records whose Notion pages were deleted/archived in Notion."""
    logger.info("scheduled_notion_deletion_check_started")

    session: Optional[AsyncSession] = None
    notion_service: Optional[NotionSyncService] = None

    try:
        session = await get_db_session()
        notion_service = await _get_notion_service_for_worker(session)
        if not notion_service:
            logger.debug("notion_deletion_check_skipped_missing_credentials")
            return {
                "status": "skipped",
                "message": "Notion credentials not configured",
                "deleted_count": 0,
            }

        result = await session.execute(
            select(InspirationRecord)
            .where(InspirationRecord.notion_page_id.isnot(None))
            .order_by(func.random())
            .limit(settings.NOTION_SYNC_BATCH_SIZE)
        )
        records = result.scalars().all()

        deleted_count = 0
        for record in records:
            if await notion_service.is_page_archived_or_missing(record.notion_page_id):
                await session.execute(delete(SyncQueue).where(SyncQueue.record_id == record.id))
                await session.delete(record)
                deleted_count += 1
                logger.info(
                    "local_record_deleted_after_notion_delete",
                    record_id=record.id,
                    notion_page_id=record.notion_page_id,
                )

        if deleted_count:
            await session.commit()

        logger.info(
            "scheduled_notion_deletion_check_completed",
            checked_count=len(records),
            deleted_count=deleted_count,
        )
        return {
            "status": "success",
            "checked_count": len(records),
            "deleted_count": deleted_count,
        }

    except Exception as e:
        logger.error(
            "scheduled_notion_deletion_check_failed",
            error=str(e),
            exc_info=True,
        )
        if session:
            await session.rollback()
        return {
            "status": "error",
            "error": str(e),
        }

    finally:
        if notion_service:
            await notion_service.close()
        if session:
            await session.close()


# ==================== Worker Registration ====================


# Register job functions
async def startup(ctx: dict) -> None:
    """Worker startup hook"""
    logger.info("arq_worker_starting")
    session: Optional[AsyncSession] = None
    notion_service: Optional[NotionSyncService] = None
    try:
        session = await get_db_session()
        notion_service = await _get_notion_service_for_worker(session)
        if notion_service:
            schema_ready = await notion_service.ensure_database_schema()
            if not schema_ready:
                logger.warning("notion_schema_reconcile_skipped_or_failed")
    except Exception as e:
        logger.warning("notion_schema_reconcile_startup_failed", error=str(e))
    finally:
        if notion_service:
            await notion_service.close()
        if session:
            await session.close()


async def shutdown(ctx: dict) -> None:
    """Worker shutdown hook"""
    logger.info("arq_worker_shutting_down")


# ARQ worker class configuration
class WorkerSettingsClass:
    """
    ARQ worker settings class for arq worker command.

    Usage:
        arq backend.src.app.worker.WorkerSettingsClass
    """

    functions = [sync_inspiration_to_notion]

    # Scheduled jobs (run every 1 minute)
    cron_jobs = [
        # Check for pending sync tasks every minute
        cron(scheduled_sync_check, minute=set(range(0, 60, 1)), unique=True),
        # Check for pages deleted directly in Notion every 5 minutes
        cron(scheduled_notion_deletion_check, minute=set(range(0, 60, 5)), unique=True),
    ]

    on_startup = startup
    on_shutdown = shutdown

    redis_settings = WorkerSettings.redis_settings
    max_jobs = WorkerSettings.max_jobs
    job_timeout = WorkerSettings.job_timeout
    max_tries = WorkerSettings.max_tries
    keep_result = WorkerSettings.keep_result
    queue_name = WorkerSettings.queue_name
