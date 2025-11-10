#!/usr/bin/env python3
"""Verify Notion page properties for latest record"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select, desc
from src.database import get_db
from src.models.inspiration import InspirationRecord
from src.services.notion_sync import NotionSyncService


async def verify_latest_notion_page():
    """Verify latest record's Notion page"""
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        print("\n" + "=" * 60)
        print("Verifying Latest Notion Page")
        print("=" * 60)

        # Get latest record
        result = await db.execute(
            select(InspirationRecord)
            .where(InspirationRecord.notion_page_id.isnot(None))
            .order_by(desc(InspirationRecord.id))
            .limit(1)
        )
        record = result.scalar_one_or_none()

        if not record:
            print("\n❌ No records with notion_page_id found!")
            return False

        print(f"\n✅ Found latest synced record:")
        print(f"   ID: {record.id}")
        print(f"   Title: {record.title}")
        print(f"   Category Tags: {record.category_tags}")
        print(f"   Notion Page ID: {record.notion_page_id}")

        # Initialize Notion service
        print(f"\n📡 Fetching Notion page properties...")
        notion_service = NotionSyncService()

        # Retrieve page from Notion
        async def get_page():
            return await notion_service.client.pages.retrieve(
                page_id=record.notion_page_id
            )

        try:
            page = await notion_service._retry_with_backoff(
                operation_name=f"get_page_{record.notion_page_id}",
                operation_func=get_page,
            )

            print("\n✅ Successfully retrieved Notion page!")
            print("\n📊 Page Properties:")

            properties = page.get("properties", {})

            # Check if "分类" field exists and has values
            categories_prop = properties.get("分类")
            if categories_prop:
                print("\n✅ '分类' field exists!")
                multi_select = categories_prop.get("multi_select", [])
                if multi_select:
                    print(f"   Categories ({len(multi_select)} tags):")
                    for tag in multi_select:
                        print(f"     - {tag['name']}")
                else:
                    print("   ⚠️  '分类' field is EMPTY (no tags)")
            else:
                print("\n❌ '分类' field NOT FOUND in Notion database!")
                print("   Available properties:")
                for prop_name in properties.keys():
                    print(f"     - {prop_name}")

            # Check other key properties
            print("\n📋 Other Properties:")
            for prop_name in ["名称1", "内容", "输入方式", "摘要", "来源"]:
                if prop_name in properties:
                    print(f"   ✅ {prop_name}: exists")
                else:
                    print(f"   ❌ {prop_name}: missing")

            await notion_service.close()
            return True

        except Exception as e:
            print(f"\n❌ Failed to retrieve Notion page: {e}")
            import traceback
            traceback.print_exc()
            await notion_service.close()
            return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    success = asyncio.run(verify_latest_notion_page())
    print("\n" + "=" * 60)
    if success:
        print("✅ Verification completed")
    else:
        print("❌ Verification failed")
    print("=" * 60 + "\n")
    sys.exit(0 if success else 1)
