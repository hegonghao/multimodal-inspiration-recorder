#!/usr/bin/env python3
"""
Re-sync records with category_tags to Notion

This script creates UPDATE sync tasks for records that have category_tags
but were synced before the category_tags feature was added.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select, and_
from src.database import get_db
from src.models.inspiration import InspirationRecord
from src.models.sync_queue import SyncOperation, SyncPriority
from src.services.sync_service import SyncQueueService


async def resync_records_with_category_tags():
    """Create UPDATE sync tasks for records with category_tags"""

    print("=" * 60)
    print("Re-sync Records with Category Tags to Notion")
    print("=" * 60)

    # Get database session
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        # Find records with category_tags and notion_page_id
        query = select(InspirationRecord).where(
            and_(
                InspirationRecord.category_tags.isnot(None),
                InspirationRecord.category_tags != '',
                InspirationRecord.notion_page_id.isnot(None)
            )
        )

        result = await db.execute(query)
        records = result.scalars().all()

        if not records:
            print("\n❌ No records found with category_tags and notion_page_id")
            return False

        print(f"\n✅ Found {len(records)} records with category_tags to re-sync")

        # Initialize sync service
        sync_service = SyncQueueService(db)

        # Create UPDATE sync tasks for each record
        created_count = 0
        skipped_count = 0
        failed_count = 0

        print("\n📝 Creating UPDATE sync tasks...")

        for record in records:
            try:
                print(f"\n  Record ID {record.id}: {record.title[:50]}")
                print(f"    Category Tags: {record.category_tags[:60]}...")
                print(f"    Notion Page ID: {record.notion_page_id}")

                # Create UPDATE sync task with immediate=True
                sync_task = await sync_service.enqueue_sync_task(
                    record_id=record.id,
                    operation=SyncOperation.UPDATE,
                    priority=SyncPriority.HIGH,
                    immediate=True  # Enqueue immediately to ARQ
                )

                if sync_task:
                    created_count += 1
                    print(f"    ✅ Created sync task ID: {sync_task.id}")
                else:
                    skipped_count += 1
                    print(f"    ⏭️  Skipped (task already exists)")

            except Exception as e:
                failed_count += 1
                print(f"    ❌ Failed: {e}")

        # Commit all changes
        await db.commit()

        print("\n" + "=" * 60)
        print("Summary:")
        print(f"  ✅ Created: {created_count} sync tasks")
        print(f"  ⏭️  Skipped: {skipped_count} (already pending)")
        print(f"  ❌ Failed: {failed_count}")
        print(f"  📊 Total: {len(records)} records")
        print("=" * 60)

        if created_count > 0:
            print("\n⏳ Sync tasks have been enqueued.")
            print("   The worker will process them shortly.")
            print("   Check worker logs: docker-compose logs -f worker")
            print("\n📌 Important: Make sure you have added the following fields to your Notion database:")
            print("   - 分类 (Multi-select)")
            print("   - 标签 (Multi-select)")
            print("\n   See NOTION_DATABASE_SETUP.md for detailed instructions.")

        await sync_service.close()
        return created_count > 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Re-sync Category Tags to Notion")
    print("=" * 60 + "\n")

    success = asyncio.run(resync_records_with_category_tags())

    print("\n" + "=" * 60)
    if success:
        print("✅ Re-sync initiated successfully")
    else:
        print("❌ Re-sync failed or no records to sync")
    print("=" * 60 + "\n")

    sys.exit(0 if success else 1)
