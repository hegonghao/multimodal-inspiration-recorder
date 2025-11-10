"""
Batch Operations for Database Performance Optimization
批量操作工具，提升数据库性能
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import structlog

from src.models.inspiration import InspirationRecord, SyncStatus, AIProcessingStatus
from src.models.sync_queue import SyncQueue, SyncQueueStatus

logger = structlog.get_logger(__name__)


async def bulk_insert_records(
    db: AsyncSession,
    records_data: List[Dict[str, Any]],
    chunk_size: int = 100,
) -> List[InspirationRecord]:
    """
    批量插入灵感记录

    Args:
        db: 数据库会话
        records_data: 记录数据列表（字典格式）
        chunk_size: 每批次插入数量

    Returns:
        插入的记录列表

    Example:
        records_data = [
            {"title": "灵感1", "content": "内容1", "input_type": "text"},
            {"title": "灵感2", "content": "内容2", "input_type": "voice"},
        ]
        records = await bulk_insert_records(db, records_data)
    """
    if not records_data:
        return []

    logger.info("bulk_insert_records_started", count=len(records_data))

    inserted_records = []

    # 分批插入以避免内存压力
    for i in range(0, len(records_data), chunk_size):
        chunk = records_data[i : i + chunk_size]

        # 使用SQLAlchemy ORM批量添加
        records = [InspirationRecord(**data) for data in chunk]
        db.add_all(records)
        await db.flush()  # 获取自动生成的ID

        inserted_records.extend(records)

        logger.debug(
            "bulk_insert_chunk_completed",
            chunk_index=i // chunk_size + 1,
            chunk_size=len(chunk),
        )

    await db.commit()

    logger.info(
        "bulk_insert_records_completed",
        total_inserted=len(inserted_records),
    )

    return inserted_records


async def bulk_update_sync_status(
    db: AsyncSession,
    record_ids: List[int],
    new_status: SyncStatus,
    notion_page_id: Optional[str] = None,
) -> int:
    """
    批量更新同步状态

    Args:
        db: 数据库会话
        record_ids: 记录ID列表
        new_status: 新的同步状态
        notion_page_id: Notion页面ID（可选）

    Returns:
        更新的记录数量

    Example:
        count = await bulk_update_sync_status(
            db,
            record_ids=[1, 2, 3],
            new_status=SyncStatus.SYNCED,
            notion_page_id="abc123"
        )
    """
    if not record_ids:
        return 0

    logger.info(
        "bulk_update_sync_status_started",
        record_count=len(record_ids),
        new_status=new_status.name,
    )

    update_values = {"sync_status": new_status.value}
    if notion_page_id:
        update_values["notion_page_id"] = notion_page_id

    result = await db.execute(
        update(InspirationRecord)
        .where(InspirationRecord.id.in_(record_ids))
        .values(**update_values)
    )

    await db.commit()

    updated_count = result.rowcount
    logger.info(
        "bulk_update_sync_status_completed",
        updated_count=updated_count,
    )

    return updated_count


async def bulk_update_ai_status(
    db: AsyncSession,
    record_ids: List[int],
    new_status: AIProcessingStatus,
    error_message: Optional[str] = None,
) -> int:
    """
    批量更新AI处理状态

    Args:
        db: 数据库会话
        record_ids: 记录ID列表
        new_status: 新的AI处理状态
        error_message: 错误信息（可选）

    Returns:
        更新的记录数量
    """
    if not record_ids:
        return 0

    logger.info(
        "bulk_update_ai_status_started",
        record_count=len(record_ids),
        new_status=new_status.name,
    )

    update_values = {"ai_processing_status": new_status.value}
    if error_message:
        update_values["ai_error_message"] = error_message

    result = await db.execute(
        update(InspirationRecord)
        .where(InspirationRecord.id.in_(record_ids))
        .values(**update_values)
    )

    await db.commit()

    updated_count = result.rowcount
    logger.info(
        "bulk_update_ai_status_completed",
        updated_count=updated_count,
    )

    return updated_count


async def bulk_delete_records(
    db: AsyncSession,
    record_ids: List[int],
) -> int:
    """
    批量删除记录

    注意：由于外键级联删除，相关的SyncQueue记录也会被删除

    Args:
        db: 数据库会话
        record_ids: 记录ID列表

    Returns:
        删除的记录数量
    """
    if not record_ids:
        return 0

    logger.warning(
        "bulk_delete_records_started",
        record_count=len(record_ids),
    )

    # 首先获取要删除的记录信息（用于日志）
    result = await db.execute(
        select(InspirationRecord.id, InspirationRecord.title)
        .where(InspirationRecord.id.in_(record_ids))
    )
    records_to_delete = result.all()

    # 执行删除
    from sqlalchemy import delete

    result = await db.execute(
        delete(InspirationRecord).where(InspirationRecord.id.in_(record_ids))
    )

    await db.commit()

    deleted_count = result.rowcount
    logger.warning(
        "bulk_delete_records_completed",
        deleted_count=deleted_count,
        record_titles=[r.title[:30] for r in records_to_delete],
    )

    return deleted_count


async def bulk_create_sync_tasks(
    db: AsyncSession,
    record_ids: List[int],
    operation: str = "create",
    priority: int = 0,
) -> int:
    """
    批量创建同步任务

    Args:
        db: 数据库会话
        record_ids: 记录ID列表
        operation: 操作类型（create/update/delete）
        priority: 优先级（0=normal, 1=high, 2=urgent）

    Returns:
        创建的任务数量
    """
    if not record_ids:
        return 0

    logger.info(
        "bulk_create_sync_tasks_started",
        record_count=len(record_ids),
        operation=operation,
    )

    # 检查哪些记录尚未有待处理的同步任务
    existing_tasks = await db.execute(
        select(SyncQueue.record_id)
        .where(SyncQueue.record_id.in_(record_ids))
        .where(SyncQueue.status.in_([SyncQueueStatus.PENDING.value, SyncQueueStatus.PROCESSING.value]))
    )
    existing_record_ids = {row[0] for row in existing_tasks.all()}

    # 过滤掉已有任务的记录
    new_record_ids = [rid for rid in record_ids if rid not in existing_record_ids]

    if not new_record_ids:
        logger.info("bulk_create_sync_tasks_skipped_all_exist")
        return 0

    # 批量创建任务
    tasks = [
        SyncQueue(
            record_id=record_id,
            operation=operation,
            priority=priority,
            status=SyncQueueStatus.PENDING.value,
        )
        for record_id in new_record_ids
    ]

    db.add_all(tasks)
    await db.commit()

    created_count = len(tasks)
    logger.info(
        "bulk_create_sync_tasks_completed",
        created_count=created_count,
        skipped_count=len(record_ids) - created_count,
    )

    return created_count


async def bulk_retry_failed_tasks(
    db: AsyncSession,
    max_tasks: int = 50,
) -> int:
    """
    批量重试失败的同步任务

    Args:
        db: 数据库会话
        max_tasks: 最多重试任务数

    Returns:
        重置的任务数量
    """
    from datetime import datetime, UTC

    logger.info("bulk_retry_failed_tasks_started", max_tasks=max_tasks)

    # 查找可以重试的失败任务（retry_count < max_retries）
    now = datetime.now(UTC)

    result = await db.execute(
        select(SyncQueue.id)
        .where(SyncQueue.status == SyncQueueStatus.FAILED.value)
        .where(SyncQueue.retry_count < SyncQueue.max_retries)
        .where(
            (SyncQueue.next_retry_at.is_(None))
            | (SyncQueue.next_retry_at <= now)
        )
        .order_by(SyncQueue.priority.desc(), SyncQueue.created_at.asc())
        .limit(max_tasks)
    )

    task_ids = [row[0] for row in result.all()]

    if not task_ids:
        logger.info("bulk_retry_failed_tasks_no_tasks_found")
        return 0

    # 重置状态为PENDING
    result = await db.execute(
        update(SyncQueue)
        .where(SyncQueue.id.in_(task_ids))
        .values(
            status=SyncQueueStatus.PENDING.value,
            error_message=None,
        )
    )

    await db.commit()

    reset_count = result.rowcount
    logger.info("bulk_retry_failed_tasks_completed", reset_count=reset_count)

    return reset_count


async def get_records_statistics(
    db: AsyncSession,
) -> Dict[str, int]:
    """
    获取记录统计信息

    Args:
        db: 数据库会话

    Returns:
        统计信息字典

    Example:
        {
            "total_records": 1000,
            "voice_records": 300,
            "text_records": 500,
            "image_records": 200,
            "synced_records": 850,
            "pending_sync": 100,
            "failed_sync": 50,
            "pending_ai": 20,
            "completed_ai": 950,
        }
    """
    logger.debug("get_records_statistics_started")

    # 使用单个查询获取所有统计（避免多次往返）
    from sqlalchemy import case

    result = await db.execute(
        select(
            func.count().label("total_records"),
            func.sum(
                case((InspirationRecord.input_type == "voice", 1), else_=0)
            ).label("voice_records"),
            func.sum(
                case((InspirationRecord.input_type == "text", 1), else_=0)
            ).label("text_records"),
            func.sum(
                case((InspirationRecord.input_type == "image", 1), else_=0)
            ).label("image_records"),
            func.sum(
                case((InspirationRecord.sync_status == SyncStatus.SYNCED.value, 1), else_=0)
            ).label("synced_records"),
            func.sum(
                case((InspirationRecord.sync_status == SyncStatus.PENDING.value, 1), else_=0)
            ).label("pending_sync"),
            func.sum(
                case((InspirationRecord.sync_status == SyncStatus.FAILED.value, 1), else_=0)
            ).label("failed_sync"),
            func.sum(
                case((InspirationRecord.ai_processing_status == AIProcessingStatus.PENDING.value, 1), else_=0)
            ).label("pending_ai"),
            func.sum(
                case((InspirationRecord.ai_processing_status == AIProcessingStatus.COMPLETED.value, 1), else_=0)
            ).label("completed_ai"),
        )
    )

    row = result.one()

    stats = {
        "total_records": row.total_records or 0,
        "voice_records": row.voice_records or 0,
        "text_records": row.text_records or 0,
        "image_records": row.image_records or 0,
        "synced_records": row.synced_records or 0,
        "pending_sync": row.pending_sync or 0,
        "failed_sync": row.failed_sync or 0,
        "pending_ai": row.pending_ai or 0,
        "completed_ai": row.completed_ai or 0,
    }

    logger.debug("get_records_statistics_completed", stats=stats)

    return stats


async def cleanup_old_failed_tasks(
    db: AsyncSession,
    days_old: int = 30,
) -> int:
    """
    清理超过指定天数的失败任务

    Args:
        db: 数据库会话
        days_old: 清理多少天前的任务

    Returns:
        删除的任务数量
    """
    from datetime import datetime, timedelta, UTC

    cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

    logger.info(
        "cleanup_old_failed_tasks_started",
        days_old=days_old,
        cutoff_date=cutoff_date.isoformat(),
    )

    from sqlalchemy import delete

    result = await db.execute(
        delete(SyncQueue)
        .where(SyncQueue.status == SyncQueueStatus.FAILED.value)
        .where(SyncQueue.retry_count >= SyncQueue.max_retries)
        .where(SyncQueue.created_at < cutoff_date)
    )

    await db.commit()

    deleted_count = result.rowcount
    logger.info("cleanup_old_failed_tasks_completed", deleted_count=deleted_count)

    return deleted_count
