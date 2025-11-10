#!/usr/bin/env python3
"""Check latest records in database"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select, desc, text
from src.database import get_db
from src.models.inspiration import InspirationRecord
from src.models.sync_queue import SyncQueue


async def check_latest_records():
    """Check latest records and sync tasks"""
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        print("\n" + "=" * 60)
        print("Latest 5 Records:")
        print("=" * 60)

        # Get latest records
        result = await db.execute(
            select(InspirationRecord)
            .order_by(desc(InspirationRecord.id))
            .limit(5)
        )
        records = result.scalars().all()

        if records:
            for record in records:
                print(f"\nID {record.id}: {record.title[:50]}")
                print(f"  Created: {record.created_at}")
                print(f"  Input Type: {record.input_type}")
                print(f"  Category Tags: {record.category_tags[:100] if record.category_tags else 'None'}")
                print(f"  Summary: {record.summary[:100] if record.summary else 'None'}")
                print(f"  AI Processing Status: {record.ai_processing_status}")
                print(f"  AI Error: {record.ai_error_message[:50] if record.ai_error_message else 'None'}")
                print(f"  Notion Page ID: {record.notion_page_id or 'None'}")
        else:
            print("\n❌ No records found!")

        print("\n" + "=" * 60)
        print("Latest 5 Sync Tasks:")
        print("=" * 60)

        # Get latest sync tasks
        result = await db.execute(
            select(SyncQueue)
            .order_by(desc(SyncQueue.id))
            .limit(5)
        )
        tasks = result.scalars().all()

        if tasks:
            for task in tasks:
                print(f"\nSync Task ID {task.id}:")
                print(f"  Record ID: {task.record_id}")
                print(f"  Operation: {task.operation}")
                print(f"  Status: {task.status}")
                print(f"  Created: {task.created_at}")
                print(f"  Retries: {task.retry_count}")
        else:
            print("\n❌ No sync tasks found!")

        print("\n" + "=" * 60)

    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    asyncio.run(check_latest_records())
