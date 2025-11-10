#!/usr/bin/env python3
"""Check App's local database for unsyncedrecords"""
import sqlite3
import os
from pathlib import Path

# Find app database (typical Flutter location on Windows)
possible_paths = [
    Path.home() / "AppData" / "Local" / "inspiration_recorder" / "app.db",
    Path.home() / "AppData" / "Roaming" / "inspiration_recorder" / "app.db",
    Path("D:/") / "multifuncinspirationrecord" / "app" / "*.db",
]

print("\n" + "=" * 60)
print("Searching for App Database")
print("=" * 60)

# Try to find the database
for path in possible_paths:
    if path.exists():
        print(f"\n✅ Found database: {path}")

        try:
            conn = sqlite3.connect(str(path))
            cursor = conn.cursor()

            # Get record count
            cursor.execute("SELECT COUNT(*) FROM inspiration_records")
            total_count = cursor.fetchone()[0]

            # Get records without notion_page_id (unsynced to Notion)
            cursor.execute("SELECT COUNT(*) FROM inspiration_records WHERE notion_page_id IS NULL")
            unsynced_count = cursor.fetchone()[0]

            # Get latest records
            cursor.execute("""
                SELECT id, title, created_at, notion_page_id
                FROM inspiration_records
                ORDER BY id DESC
                LIMIT 5
            """)
            latest_records = cursor.fetchall()

            print(f"\n📊 Statistics:")
            print(f"  Total records: {total_count}")
            print(f"  Unsynced to Notion: {unsynced_count}")

            print(f"\n📝 Latest 5 records:")
            for record in latest_records:
                synced = "✅" if record[3] else "❌"
                print(f"  {synced} ID {record[0]}: {record[1][:50]}")
                print(f"     Created: {record[2]}")

            conn.close()
            break
        except Exception as e:
            print(f"❌ Error reading database: {e}")
    else:
        print(f"⏭️  Not found: {path}")

print("\n" + "=" * 60)
print("Note: App database location may vary")
print("=" * 60 + "\n")
