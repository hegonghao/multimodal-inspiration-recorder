#!/usr/bin/env python3
"""
Reprocess failed AI records

This script finds all records where AI processing failed (ai_processing_status=1)
and retries the AI processing.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select, and_
from src.database import get_db
from src.models.inspiration import InspirationRecord, serialize_category_tags
from src.services.ai_processor import get_ai_processor


async def reprocess_failed_records():
    """Find and reprocess failed AI records"""
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        print("\n" + "=" * 60)
        print("Reprocessing Failed AI Records...")
        print("=" * 60)

        # Get AI processor
        processor = get_ai_processor()
        print(f"[OK] AI Processor ready (model: {processor.model})")

        # Find failed records
        result = await db.execute(
            select(InspirationRecord)
            .where(
                and_(
                    InspirationRecord.ai_processing_status == 1,  # FAILED
                    InspirationRecord.content.isnot(None),
                )
            )
            .order_by(InspirationRecord.id.desc())
        )
        failed_records = result.scalars().all()

        if not failed_records:
            print("\n[OK] No failed records found!")
            return

        print(f"\nFound {len(failed_records)} failed record(s)")
        print("-" * 60)

        success_count = 0
        failed_count = 0

        for record in failed_records:
            print(f"\nProcessing Record ID {record.id}: {record.title[:50]}...")

            try:
                # Process content with AI
                result = await processor.process_content(
                    content=record.content,
                    input_type=record.input_type,
                    language="zh",  # Assume Chinese by default
                )

                # Generate new title
                title = await processor.generate_title(
                    record.content,
                    max_length=50,
                    language="zh"
                )

                # Update record
                record.title = title
                record.category_tags = serialize_category_tags(result["categories"])
                record.summary = result["summary"]
                record.ai_processing_status = 2  # COMPLETED
                record.ai_error_message = None

                await db.commit()

                print(f"  [OK] Success!")
                print(f"      Categories: {result['categories']}")
                print(f"      Summary: {result['summary'][:50]}...")
                success_count += 1

            except Exception as e:
                print(f"  [FAIL] Error: {e}")
                failed_count += 1
                await db.rollback()

        print("\n" + "=" * 60)
        print(f"Reprocessing Complete:")
        print(f"  Success: {success_count}")
        print(f"  Failed: {failed_count}")
        print("=" * 60)

    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    asyncio.run(reprocess_failed_records())
