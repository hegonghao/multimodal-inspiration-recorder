#!/usr/bin/env python3
"""Quick check for database configuration"""
import sqlite3

DB_PATH = "data/inspirations.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT
        id,
        SUBSTR(deepgram_api_key, 1, 20) || '...' as deepgram_key,
        openai_model,
        SUBSTR(notion_token, 1, 10) || '...' as notion_token,
        sync_interval
    FROM user_preferences
    WHERE id = 1
""")

result = cursor.fetchone()
if result:
    print("✅ Configuration found in database:")
    print(f"   ID: {result[0]}")
    print(f"   Deepgram Key: {result[1]}")
    print(f"   OpenAI Model: {result[2]}")
    print(f"   Notion Token: {result[3]}")
    print(f"   Sync Interval: {result[4]} seconds")
else:
    print("❌ No configuration found! Run init_db.py first")

conn.close()
