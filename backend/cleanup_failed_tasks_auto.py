#!/usr/bin/env python3
"""Clean up failed sync tasks automatically"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select, delete
from src.database import get_db
from src.models.sync_queue import SyncQueue, SyncQueueStatus


async def cleanup_failed_tasks():
    """Delete failed sync tasks that reached max retries"""
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        print("\n" + "=" * 60)
        print("Cleanup Failed Sync Tasks")
        print("=" * 60)

        # Count failed tasks
        result = await db.execute(
            select(SyncQueue)
            .where(SyncQueue.status == SyncQueueStatus.FAILED.value)
        )
        failed_tasks = result.scalars().all()

        if not failed_tasks:
            print("\n✅ No failed tasks to clean up!")
            return

        print(f"\n找到 {len(failed_tasks)} 个失败任务:")
        for task in failed_tasks:
            print(f"  - Task ID {task.id}: Record {task.record_id} ({task.operation}), Retries: {task.retry_count}")

        print("\n🗑️  开始删除失败任务...")

        # Delete failed tasks
        result = await db.execute(
            delete(SyncQueue)
            .where(SyncQueue.status == SyncQueueStatus.FAILED.value)
        )
        deleted_count = result.rowcount
        await db.commit()

        print(f"\n✅ 已成功删除 {deleted_count} 个失败任务")

        # Verify cleanup
        result = await db.execute(
            select(SyncQueue)
            .where(SyncQueue.status == SyncQueueStatus.FAILED.value)
        )
        remaining = result.scalars().all()

        if not remaining:
            print("✅ 验证：所有失败任务已清理完成")
        else:
            print(f"⚠️  警告：仍有 {len(remaining)} 个失败任务")

        print("\n" + "=" * 60)

    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    asyncio.run(cleanup_failed_tasks())
