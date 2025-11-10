#!/usr/bin/env python3
"""Clean up failed sync tasks"""
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

        # Ask for confirmation
        print("\n⚠️  这些任务会被永久删除。")
        print("   它们都是因为Notion页面已删除而失败的旧记录更新任务。")
        print("   删除后不会影响新记录的同步。\n")

        response = input("确认删除这些失败任务? (yes/no): ")

        if response.lower() != 'yes':
            print("\n❌ 操作已取消")
            return

        # Delete failed tasks
        await db.execute(
            delete(SyncQueue)
            .where(SyncQueue.status == SyncQueueStatus.FAILED.value)
        )
        await db.commit()

        print(f"\n✅ 已删除 {len(failed_tasks)} 个失败任务")
        print("\n" + "=" * 60)

    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    asyncio.run(cleanup_failed_tasks())
