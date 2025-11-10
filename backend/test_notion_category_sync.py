#!/usr/bin/env python3
"""
Test script to verify Notion category tags sync functionality

This script:
1. Fetches a record with category_tags from the database
2. Tests the NotionSyncService to update the page with category tags
3. Verifies the sync worked correctly
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select
from src.database import get_db
from src.models.inspiration import InspirationRecord
from src.services.notion_sync import NotionSyncService
from src.config import settings


async def test_category_sync():
    """Test syncing category tags to Notion"""

    print("=" * 60)
    print("Testing Notion Category Tags Sync")
    print("=" * 60)

    # Get database session
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        # Find a record with category_tags and notion_page_id
        query = select(InspirationRecord).where(
            InspirationRecord.category_tags.isnot(None),
            InspirationRecord.category_tags != '',
            InspirationRecord.notion_page_id.isnot(None)
        ).limit(1)

        result = await db.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            print("❌ No records found with both category_tags and notion_page_id")
            return False

        print(f"\n✅ Found test record:")
        print(f"   ID: {record.id}")
        print(f"   Title: {record.title}")
        print(f"   Category Tags: {record.category_tags}")
        print(f"   Notion Page ID: {record.notion_page_id}")

        # Initialize Notion service
        print(f"\n📡 Initializing Notion sync service...")
        notion_service = NotionSyncService()

        # Test connection first
        print("   Testing Notion connection...")
        connection_ok = await notion_service.verify_connection()

        if not connection_ok:
            print("❌ Notion connection failed!")
            return False

        print("   ✅ Connection successful")

        # Try to update the page with category tags
        print(f"\n🔄 Updating Notion page with category tags...")
        success = await notion_service.update_page(
            notion_page_id=record.notion_page_id,
            record=record
        )

        if success:
            print("✅ Successfully updated Notion page with category tags!")
            print("\n📝 Next steps:")
            print("   1. Open your Notion database")
            print("   2. Find the page titled:", record.title)
            print("   3. Check if the '分类' field shows:", record.category_tags)
            print("\n⚠️  Note: If you see an error about missing properties,")
            print("   you need to add the '分类' (Multi-select) field to your database.")
            print("   See NOTION_DATABASE_SETUP.md for instructions.")
            return True
        else:
            print("❌ Failed to update Notion page")
            print("   Check backend logs for details")
            return False

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        try:
            await notion_service.close()
        except:
            pass
        await db_gen.aclose()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Notion Category Tags Sync Test")
    print("=" * 60)
    print(f"\nNotión Database ID: {settings.NOTION_DATABASE_ID}")
    print(f"Using Token: {settings.NOTION_TOKEN[:20] if settings.NOTION_TOKEN else 'NOT SET'}...\n")

    success = asyncio.run(test_category_sync())

    print("\n" + "=" * 60)
    if success:
        print("✅ Test PASSED")
    else:
        print("❌ Test FAILED")
    print("=" * 60 + "\n")

    sys.exit(0 if success else 1)
