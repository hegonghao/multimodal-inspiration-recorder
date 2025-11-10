"""
Sync Queue Management Service

Manages the synchronization queue for Notion API operations.
Handles enqueueing, priority management, and status tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

import structlog
from arq import create_pool
from arq.connections import ArqRedis
from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.inspiration import InspirationRecord, SyncStatus
from src.models.sync_queue import (
    SyncQueue,
    SyncOperation,
    SyncQueueStatus,
    SyncPriority,
    SyncStatusResponse,
)
from src.app.worker import WorkerSettings

logger = structlog.get_logger(__name__)


# ==================== Sync Service ====================


class SyncQueueService:
    """
    Service for managing Notion sync queue operations.

    Features:
    - Enqueue sync tasks with priority
    - Track sync status and statistics
    - Trigger manual sync operations
    - Clean up completed/failed tasks
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize sync queue service.

        Args:
            db: Database session
        """
        self.db = db
        self.redis: Optional[ArqRedis] = None

    async def _get_redis_pool(self) -> ArqRedis:
        """Get or create Redis connection pool"""
        if self.redis is None:
            self.redis = await create_pool(WorkerSettings.redis_settings)
        return self.redis

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self.redis = None

    # ==================== Queue Management ====================

    async def enqueue_sync_task(
        self,
        record_id: int,
        operation: SyncOperation,
        priority: SyncPriority = SyncPriority.NORMAL,
        immediate: bool = False,
    ) -> Optional[SyncQueue]:
        """
        Enqueue a new sync task for background processing.

        Args:
            record_id: InspirationRecord ID to sync
            operation: Sync operation type (create/update/delete)
            priority: Task priority level
            immediate: If True, enqueue to ARQ immediately; if False, wait for scheduled check

        Returns:
            Created SyncQueue task or None if failed

        Raises:
            Exception: If record not found or enqueue fails
        """
        logger.info(
            "enqueue_sync_task",
            record_id=record_id,
            operation=operation.value,
            priority=priority.value,
            immediate=immediate,
        )

        # Verify record exists
        result = await self.db.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = result.scalar_one_or_none()

        if not record:
            logger.error(
                "record_not_found_for_sync",
                record_id=record_id,
            )
            raise ValueError(f"InspirationRecord {record_id} not found")

        # Check if task already exists in pending/processing state
        existing_task_result = await self.db.execute(
            select(SyncQueue).where(
                and_(
                    SyncQueue.record_id == record_id,
                    SyncQueue.operation == operation,
                    SyncQueue.status.in_([SyncQueueStatus.PENDING, SyncQueueStatus.PROCESSING]),
                )
            )
        )
        existing_task = existing_task_result.scalar_one_or_none()

        if existing_task:
            logger.warning(
                "sync_task_already_exists",
                sync_task_id=existing_task.id,
                record_id=record_id,
                operation=operation.value,
            )
            return existing_task

        # Create new sync task
        sync_task = SyncQueue(
            record_id=record_id,
            operation=operation.value,
            status=SyncQueueStatus.PENDING,
            priority=priority.value,
            retry_count=0,
            max_retries=5,
            created_at=datetime.utcnow(),
        )

        self.db.add(sync_task)
        await self.db.commit()
        await self.db.refresh(sync_task)

        # Update record sync status to PENDING
        await self.db.execute(
            update(InspirationRecord)
            .where(InspirationRecord.id == record_id)
            .values(sync_status=SyncStatus.PENDING)
        )
        await self.db.commit()

        logger.info(
            "sync_task_created",
            sync_task_id=sync_task.id,
            record_id=record_id,
            operation=operation.value,
        )

        # Enqueue to ARQ immediately if requested
        if immediate and settings.NOTION_SYNC_ENABLED:
            try:
                redis = await self._get_redis_pool()
                await redis.enqueue_job(
                    "sync_inspiration_to_notion",
                    sync_task.id,
                    _queue_name=WorkerSettings.queue_name,
                )
                logger.info(
                    "sync_task_enqueued_immediately",
                    sync_task_id=sync_task.id,
                )
            except Exception as e:
                logger.error(
                    "failed_to_enqueue_immediate",
                    sync_task_id=sync_task.id,
                    error=str(e),
                )
                # Don't fail the request, task will be picked up by scheduled job

        return sync_task

    async def trigger_manual_sync(
        self,
        batch_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Manually trigger sync for pending tasks.

        Args:
            batch_size: Number of tasks to sync (default from settings)

        Returns:
            Dict with sync statistics

        Raises:
            Exception: If Redis connection or enqueue fails
        """
        if batch_size is None:
            batch_size = settings.NOTION_SYNC_BATCH_SIZE

        logger.info(
            "trigger_manual_sync",
            batch_size=batch_size,
        )

        # Check if Notion sync is enabled
        # Priority: user preferences > environment variables
        from src.models.user_preferences import UserPreferences

        # Get user preferences to check if Notion is configured
        prefs_result = await self.db.execute(
            select(UserPreferences).where(UserPreferences.id == 1)
        )
        prefs = prefs_result.scalar_one_or_none()

        # Check user preferences first, fallback to environment variables
        if prefs and prefs.notion_token and prefs.notion_token.strip():
            # User has configured Notion in preferences
            notion_sync_enabled = (
                prefs.notion_database_id is not None and
                prefs.notion_database_id.strip() != ""
            )
        else:
            # Fallback to environment variables from settings
            # Note: config uses NOTION_API_KEY but .env uses NOTION_TOKEN (inconsistent naming)
            notion_api_key = getattr(settings, 'NOTION_TOKEN', None) or getattr(settings, 'NOTION_API_KEY', None)
            notion_sync_enabled = (
                settings.NOTION_SYNC_ENABLED and
                notion_api_key is not None and
                notion_api_key.strip() != "" and
                settings.NOTION_DATABASE_ID is not None and
                settings.NOTION_DATABASE_ID.strip() != ""
            )

        if not notion_sync_enabled:
            logger.warning("notion_sync_disabled_in_preferences")
            return {
                "status": "disabled",
                "message": "Notion sync is disabled in settings",
                "enqueued_count": 0,
            }

        # Find pending tasks
        now = datetime.utcnow()
        result = await self.db.execute(
            select(SyncQueue)
            .where(
                SyncQueue.status == SyncQueueStatus.PENDING,
                (SyncQueue.next_retry_at.is_(None)) | (SyncQueue.next_retry_at <= now),
            )
            .order_by(SyncQueue.priority.desc(), SyncQueue.created_at.asc())
            .limit(batch_size)
        )

        pending_tasks = result.scalars().all()

        if not pending_tasks:
            logger.info("no_pending_tasks_to_sync")
            return {
                "status": "success",
                "message": "No pending tasks to sync",
                "enqueued_count": 0,
            }

        # Enqueue tasks
        redis = await self._get_redis_pool()
        enqueued_count = 0
        failed_count = 0

        for task in pending_tasks:
            try:
                await redis.enqueue_job(
                    "sync_inspiration_to_notion",
                    task.id,
                    _queue_name=WorkerSettings.queue_name,
                )
                enqueued_count += 1
                logger.debug(
                    "manual_sync_task_enqueued",
                    sync_task_id=task.id,
                )
            except Exception as e:
                failed_count += 1
                logger.error(
                    "failed_to_enqueue_manual_sync",
                    sync_task_id=task.id,
                    error=str(e),
                )

        logger.info(
            "manual_sync_completed",
            enqueued_count=enqueued_count,
            failed_count=failed_count,
            total_pending=len(pending_tasks),
        )

        return {
            "status": "success",
            "enqueued_count": enqueued_count,
            "failed_count": failed_count,
            "total_pending": len(pending_tasks),
        }

    # ==================== Status Tracking ====================

    async def get_sync_status(self) -> SyncStatusResponse:
        """
        Get overall sync status and statistics.

        Returns:
            SyncStatusResponse with sync statistics
        """
        logger.debug("get_sync_status")

        # Count total records
        total_records_result = await self.db.execute(
            select(func.count()).select_from(InspirationRecord)
        )
        total_records = total_records_result.scalar() or 0

        # Count synced records
        synced_result = await self.db.execute(
            select(func.count())
            .select_from(InspirationRecord)
            .where(InspirationRecord.sync_status == SyncStatus.SYNCED)
        )
        synced_count = synced_result.scalar() or 0

        # Count pending sync tasks
        pending_result = await self.db.execute(
            select(func.count())
            .select_from(SyncQueue)
            .where(SyncQueue.status == SyncQueueStatus.PENDING)
        )
        pending_count = pending_result.scalar() or 0

        # Count failed sync tasks
        failed_result = await self.db.execute(
            select(func.count())
            .select_from(SyncQueue)
            .where(SyncQueue.status == SyncQueueStatus.FAILED)
        )
        failed_count = failed_result.scalar() or 0

        # Get last successful sync time
        last_sync_result = await self.db.execute(
            select(SyncQueue.completed_at)
            .where(SyncQueue.status == SyncQueueStatus.COMPLETED)
            .order_by(SyncQueue.completed_at.desc())
            .limit(1)
        )
        last_sync_at = last_sync_result.scalar_one_or_none()

        # Get next scheduled retry time
        next_retry_result = await self.db.execute(
            select(SyncQueue.next_retry_at)
            .where(
                SyncQueue.status == SyncQueueStatus.PENDING,
                SyncQueue.next_retry_at.isnot(None),
            )
            .order_by(SyncQueue.next_retry_at.asc())
            .limit(1)
        )
        next_sync_at = next_retry_result.scalar_one_or_none()

        # Check if Notion sync is enabled
        # Priority: user preferences > environment variables
        from src.models.user_preferences import UserPreferences

        prefs_result = await self.db.execute(
            select(UserPreferences).where(UserPreferences.id == 1)
        )
        prefs = prefs_result.scalar_one_or_none()

        # Check user preferences first, fallback to environment variables
        if prefs and prefs.notion_token and prefs.notion_token.strip():
            # User has configured Notion in preferences
            notion_sync_enabled = (
                prefs.notion_database_id is not None and
                prefs.notion_database_id.strip() != ""
            )
        else:
            # Fallback to environment variables from settings
            notion_api_key = getattr(settings, 'NOTION_TOKEN', None) or getattr(settings, 'NOTION_API_KEY', None)
            notion_sync_enabled = (
                settings.NOTION_SYNC_ENABLED and
                notion_api_key is not None and
                notion_api_key.strip() != "" and
                settings.NOTION_DATABASE_ID is not None and
                settings.NOTION_DATABASE_ID.strip() != ""
            )

        return SyncStatusResponse(
            total_records=total_records,
            synced_count=synced_count,
            pending_count=pending_count,
            failed_count=failed_count,
            last_sync_at=last_sync_at,
            next_sync_at=next_sync_at,
            sync_enabled=notion_sync_enabled,
        )

    async def get_task_by_id(self, task_id: int) -> Optional[SyncQueue]:
        """
        Get sync task by ID.

        Args:
            task_id: SyncQueue task ID

        Returns:
            SyncQueue task or None if not found
        """
        result = await self.db.execute(
            select(SyncQueue).where(SyncQueue.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_tasks_by_record_id(
        self, record_id: int, limit: int = 10
    ) -> List[SyncQueue]:
        """
        Get sync tasks for a specific record.

        Args:
            record_id: InspirationRecord ID
            limit: Maximum number of tasks to return

        Returns:
            List of SyncQueue tasks
        """
        result = await self.db.execute(
            select(SyncQueue)
            .where(SyncQueue.record_id == record_id)
            .order_by(SyncQueue.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    # ==================== Cleanup ====================

    async def cleanup_old_tasks(
        self, days: int = 7, status_filter: Optional[SyncQueueStatus] = None
    ) -> int:
        """
        Clean up old sync tasks to prevent database bloat.

        Args:
            days: Delete tasks older than this many days
            status_filter: Only delete tasks with this status (default: COMPLETED)

        Returns:
            Number of tasks deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        if status_filter is None:
            status_filter = SyncQueueStatus.COMPLETED

        logger.info(
            "cleanup_old_tasks",
            days=days,
            status_filter=status_filter.name,
            cutoff_date=cutoff_date.isoformat(),
        )

        # Find tasks to delete
        result = await self.db.execute(
            select(SyncQueue).where(
                and_(
                    SyncQueue.status == status_filter,
                    SyncQueue.completed_at.isnot(None),
                    SyncQueue.completed_at < cutoff_date,
                )
            )
        )

        tasks_to_delete = result.scalars().all()
        delete_count = len(tasks_to_delete)

        # Delete tasks
        for task in tasks_to_delete:
            await self.db.delete(task)

        await self.db.commit()

        logger.info(
            "cleanup_completed",
            deleted_count=delete_count,
        )

        return delete_count


# ==================== Helper Functions ====================


def get_sync_service(db: AsyncSession) -> SyncQueueService:
    """
    Dependency injection for SyncQueueService.

    Args:
        db: Database session

    Returns:
        SyncQueueService instance
    """
    return SyncQueueService(db)
