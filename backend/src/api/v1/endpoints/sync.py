"""
Sync API Endpoints

Manages synchronization with Notion API
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from typing import List, Optional, Dict, Any

import structlog

from src.database.connection import get_db
from src.models.sync_queue import (
    SyncStatusResponse,
    SyncTaskResponse,
    SyncQueueListResponse,
    SyncQueue,
    SyncQueueStatus,
    SyncOperation,
    SyncPriority,
)
from src.services.sync_service import SyncQueueService

logger = structlog.get_logger(__name__)

router = APIRouter()


# ==================== Dependency Injection ====================


def get_sync_service(db: AsyncSession = Depends(get_db)) -> SyncQueueService:
    """Get sync service instance"""
    return SyncQueueService(db)


# ==================== Endpoints ====================


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    sync_service: SyncQueueService = Depends(get_sync_service),
):
    """
    Get current synchronization status.

    Returns overall sync statistics including:
    - Total number of records
    - Count of synced, pending, and failed records
    - Last and next sync timestamps
    - Sync enabled status

    **Example Response:**
    ```json
    {
      "total_records": 100,
      "synced_count": 85,
      "pending_count": 10,
      "failed_count": 5,
      "last_sync_at": "2025-10-27T10:00:00Z",
      "next_sync_at": "2025-10-27T10:15:00Z",
      "sync_enabled": true
    }
    ```
    """
    try:
        logger.info("get_sync_status_requested")
        status_response = await sync_service.get_sync_status()

        logger.info(
            "sync_status_retrieved",
            total_records=status_response.total_records,
            synced_count=status_response.synced_count,
            pending_count=status_response.pending_count,
            failed_count=status_response.failed_count,
        )

        return status_response

    except Exception as e:
        logger.error(
            "get_sync_status_failed",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sync status: {str(e)}",
        )
    finally:
        await sync_service.close()


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    batch_size: Optional[int] = Query(
        None,
        ge=1,
        le=100,
        description="Number of tasks to sync (max 100)",
    ),
    record_ids: Optional[List[int]] = None,
    sync_service: SyncQueueService = Depends(get_sync_service),
) -> Dict[str, Any]:
    """
    Manually trigger synchronization for all or specific records.

    Enqueues pending sync tasks for immediate processing.

    **Parameters:**
    - `batch_size`: Optional number of tasks to sync (default: from settings)
    - `record_ids`: Optional list of specific record IDs to sync

    **Example Response:**
    ```json
    {
      "status": "success",
      "enqueued_count": 10,
      "failed_count": 0,
      "total_pending": 10
    }
    ```

    **Note:** Returns 202 Accepted - sync happens asynchronously in background.
    """
    try:
        logger.info(
            "trigger_sync_requested",
            batch_size=batch_size,
            record_ids=record_ids,
        )

        # If specific record IDs provided, enqueue those
        if record_ids:
            enqueued = []
            failed = []

            for record_id in record_ids:
                try:
                    # Enqueue create/update operation for this record
                    task = await sync_service.enqueue_sync_task(
                        record_id=record_id,
                        operation=SyncOperation.UPDATE,  # Use UPDATE for manual triggers
                        priority=SyncPriority.HIGH,
                        immediate=True,
                    )
                    if task:
                        enqueued.append(task.id)
                except ValueError as ve:
                    logger.warning(
                        "record_not_found",
                        record_id=record_id,
                        error=str(ve),
                    )
                    failed.append(record_id)
                except Exception as e:
                    logger.error(
                        "enqueue_task_failed",
                        record_id=record_id,
                        error=str(e),
                    )
                    failed.append(record_id)

            result = {
                "status": "success",
                "enqueued_count": len(enqueued),
                "failed_count": len(failed),
                "enqueued_task_ids": enqueued,
                "failed_record_ids": failed,
            }

        else:
            # Trigger batch sync for all pending tasks
            result = await sync_service.trigger_manual_sync(batch_size=batch_size)

        logger.info(
            "trigger_sync_completed",
            enqueued_count=result.get("enqueued_count", 0),
            failed_count=result.get("failed_count", 0),
        )

        return result

    except Exception as e:
        logger.error(
            "trigger_sync_failed",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger sync: {str(e)}",
        )
    finally:
        await sync_service.close()


@router.get("/queue", response_model=SyncQueueListResponse)
async def get_sync_queue(
    status_filter: Optional[int] = Query(
        None,
        ge=0,
        le=3,
        description="Filter by status: 0=PENDING, 1=PROCESSING, 2=COMPLETED, 3=FAILED",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of tasks to return",
    ),
    db: AsyncSession = Depends(get_db),
) -> SyncQueueListResponse:
    """
    Get sync queue details.

    Returns list of sync tasks with optional status filtering.

    **Parameters:**
    - `status_filter`: Filter by task status (0-3)
    - `limit`: Maximum number of tasks to return (max 200)

    **Example Response:**
    ```json
    {
      "tasks": [
        {
          "id": 1,
          "record_id": 1,
          "operation": "create",
          "status": 0,
          "retry_count": 0,
          "max_retries": 5,
          "priority": 1,
          "created_at": "2025-10-27T10:30:05Z"
        }
      ],
      "total_count": 10
    }
    ```
    """
    try:
        logger.info(
            "get_sync_queue_requested",
            status_filter=status_filter,
            limit=limit,
        )

        # Build query
        query = select(SyncQueue)

        if status_filter is not None:
            query = query.where(SyncQueue.status == status_filter)

        query = query.order_by(
            SyncQueue.priority.desc(),
            SyncQueue.created_at.asc(),
        ).limit(limit)

        # Execute query
        result = await db.execute(query)
        tasks = result.scalars().all()

        # Get total count
        count_query = select(SyncQueue)
        if status_filter is not None:
            count_query = count_query.where(SyncQueue.status == status_filter)

        count_result = await db.execute(count_query)
        total_count = len(count_result.scalars().all())

        # Convert to response models
        task_responses = [
            SyncTaskResponse.model_validate(task) for task in tasks
        ]

        logger.info(
            "sync_queue_retrieved",
            returned_count=len(task_responses),
            total_count=total_count,
        )

        return SyncQueueListResponse(
            tasks=task_responses,
            total_count=total_count,
        )

    except Exception as e:
        logger.error(
            "get_sync_queue_failed",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sync queue: {str(e)}",
        )


@router.post("/retry-failed", status_code=status.HTTP_202_ACCEPTED)
async def retry_failed_sync(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retry all failed sync tasks.

    Resets failed tasks to pending status and schedules them for retry.

    **Example Response:**
    ```json
    {
      "status": "success",
      "reset_count": 5,
      "message": "5 failed tasks reset for retry"
    }
    ```

    **Note:** Returns 202 Accepted - retry happens asynchronously.
    """
    try:
        logger.info("retry_failed_sync_requested")

        # Find all failed tasks
        result = await db.execute(
            select(SyncQueue).where(SyncQueue.status == SyncQueueStatus.FAILED)
        )
        failed_tasks = result.scalars().all()

        if not failed_tasks:
            logger.info("no_failed_tasks_to_retry")
            return {
                "status": "success",
                "reset_count": 0,
                "message": "No failed tasks to retry",
            }

        # Reset failed tasks to pending
        reset_count = 0
        for task in failed_tasks:
            # Reset retry count to allow new attempts
            await db.execute(
                update(SyncQueue)
                .where(SyncQueue.id == task.id)
                .values(
                    status=SyncQueueStatus.PENDING,
                    retry_count=0,
                    next_retry_at=None,
                    error_message=None,
                )
            )
            reset_count += 1

        await db.commit()

        logger.info(
            "failed_tasks_reset",
            reset_count=reset_count,
        )

        return {
            "status": "success",
            "reset_count": reset_count,
            "message": f"{reset_count} failed tasks reset for retry",
        }

    except Exception as e:
        logger.error(
            "retry_failed_sync_failed",
            error=str(e),
            exc_info=True,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry failed tasks: {str(e)}",
        )


@router.get("/tasks/{task_id}", response_model=SyncTaskResponse)
async def get_sync_task(
    task_id: int,
    sync_service: SyncQueueService = Depends(get_sync_service),
) -> SyncTaskResponse:
    """
    Get details of a specific sync task.

    **Parameters:**
    - `task_id`: Sync task ID

    **Example Response:**
    ```json
    {
      "id": 1,
      "record_id": 1,
      "operation": "create",
      "status": 2,
      "retry_count": 0,
      "max_retries": 5,
      "completed_at": "2025-10-27T10:31:15Z",
      "priority": 1
    }
    ```
    """
    try:
        logger.info(
            "get_sync_task_requested",
            task_id=task_id,
        )

        task = await sync_service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sync task {task_id} not found",
            )

        return SyncTaskResponse.model_validate(task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_sync_task_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sync task: {str(e)}",
        )
    finally:
        await sync_service.close()


@router.get("/tasks/record/{record_id}", response_model=List[SyncTaskResponse])
async def get_sync_tasks_by_record(
    record_id: int,
    limit: int = Query(10, ge=1, le=50),
    sync_service: SyncQueueService = Depends(get_sync_service),
) -> List[SyncTaskResponse]:
    """
    Get sync tasks for a specific inspiration record.

    **Parameters:**
    - `record_id`: InspirationRecord ID
    - `limit`: Maximum number of tasks to return (max 50)

    **Example Response:**
    ```json
    [
      {
        "id": 1,
        "record_id": 1,
        "operation": "create",
        "status": 2,
        "retry_count": 0,
        "max_retries": 5
      }
    ]
    ```
    """
    try:
        logger.info(
            "get_sync_tasks_by_record_requested",
            record_id=record_id,
            limit=limit,
        )

        tasks = await sync_service.get_tasks_by_record_id(
            record_id=record_id,
            limit=limit,
        )

        return [SyncTaskResponse.model_validate(task) for task in tasks]

    except Exception as e:
        logger.error(
            "get_sync_tasks_by_record_failed",
            record_id=record_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sync tasks for record: {str(e)}",
        )
    finally:
        await sync_service.close()
