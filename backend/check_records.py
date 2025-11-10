#!/usr/bin/env python3
"""Check all records in database"""
import sqlite3

DB_PATH = "data/inspirations.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT
        id,
        title,
        category_tags,
        summary,
        ai_processing_status,
        ai_error_message
    FROM inspiration_records
    ORDER BY id DESC
    LIMIT 10
""")

print("=" * 80)
print("Recent Records:")
print("=" * 80)

for row in cursor.fetchall():
    record_id, title, tags, summary, status, error = row
    print(f"\n[ID {record_id}] {title}")
    print(f"  分类: {tags}")
    print(f"  摘要: {summary}")
    print(f"  AI状态: {status} (0=pending, 1=failed, 2=success)")
    if error:
        print(f"  错误: {error}")

conn.close()
