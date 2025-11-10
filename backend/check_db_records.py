#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/inspirations.db')
cursor = conn.execute("""
    SELECT id, title, category_tags, ai_processing_status
    FROM inspiration_records
    WHERE id IN (22, 23, 24, 25, 26)
    ORDER BY id DESC
""")
rows = cursor.fetchall()

print("\nRecords 22-26 in inspirations.db:")
print("=" * 80)
for row in rows:
    print(f"ID {row[0]}:")
    print(f"  Title: {row[1][:60]}")
    print(f"  Has Tags: {'Yes' if row[2] else 'No'}")
    print(f"  AI Status: {row[3]}")
    print()

conn.close()
