#!/usr/bin/env python3
"""Check sync queue status"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select, func, and_
from src.database import get_db
from src.models.sync_queue import SyncQueue, SyncQueueStatus


async def check_sync_queue_status():
    """Check sync queue status breakdown"""
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        print("\n" + "=" * 60)
        print("Sync Queue Status")
        print("=" * 60)

        # Count by status
        for status in SyncQueueStatus:
            result = await db.execute(
                select(func.count(SyncQueue.id))
                .where(SyncQueue.status == status.value)
            )
            count = result.scalar()
            status_name = status.name
            print(f"{status_name:20s}: {count:4d}")

        # Get total count
        result = await db.execute(select(func.count(SyncQueue.id)))
        total = result.scalar()
        print(f"{'TOTAL':20s}: {total:4d}")

        print("\n" + "=" * 60)
        print("Pending Tasks Details (last 10)")
        print("=" * 60)

        # Get pending tasks
        result = await db.execute(
            select(SyncQueue)
            .where(SyncQueue.status == SyncQueueStatus.PENDING.value)
            .order_by(SyncQueue.id.desc())
            .limit(10)
        )
        pending_tasks = result.scalars().all()

        if pending_tasks:
            for task in pending_tasks:
                print(f"\nTask ID {task.id}:")
                print(f"  Record ID: {task.record_id}")
                print(f"  Operation: {task.operation}")
                print(f"  Priority: {task.priority}")
                print(f"  Retry Count: {task.retry_count}")
                print(f"  Created: {task.created_at}")
                if task.error_message:
                    print(f"  Last Error: {task.error_message[:100]}")
        else:
            print("\n✅ No pending tasks!")

        print("\n" + "=" * 60)
        print("Failed Tasks Details (last 10)")
        print("=" * 60)

        # Get failed tasks
        result = await db.execute(
            select(SyncQueue)
            .where(SyncQueue.status == SyncQueueStatus.FAILED.value)
            .order_by(SyncQueue.id.desc())
            .limit(10)
        )
        failed_tasks = result.scalars().all()

        if failed_tasks:
            for task in failed_tasks:
                print(f"\nTask ID {task.id}:")
                print(f"  Record ID: {task.record_id}")
                print(f"  Operation: {task.operation}")
                print(f"  Retry Count: {task.retry_count}")
                print(f"  Created: {task.created_at}")
                if task.error_message:
                    print(f"  Error: {task.error_message[:150]}")
        else:
            print("\n✅ No failed tasks!")

        print("\n" + "=" * 60)

    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    asyncio.run(check_sync_queue_status())
