#!/usr/bin/env python3
"""Initialize database with default preferences from .env"""
import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database path
DB_PATH = "data/inspirations.db"

# Get values from .env
deepgram_key = os.getenv("DEEPGRAM_API_KEY", "")
notion_token = os.getenv("NOTION_TOKEN", "")
notion_db_id = os.getenv("NOTION_DATABASE_ID", "")
openai_base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
openai_api_key = os.getenv("OPENAI_API_KEY", "")
openai_model = os.getenv("OPENAI_MODEL", "llama3.1")

print(f"Initializing database at: {DB_PATH}")
print(f"Deepgram API Key: {deepgram_key[:20]}..." if deepgram_key else "Deepgram API Key: (empty)")

# Connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check if preferences already exist
cursor.execute("SELECT COUNT(*) FROM user_preferences")
count = cursor.fetchone()[0]

if count > 0:
    print(f"Found {count} existing preference record(s). Updating...")
    cursor.execute("""
        UPDATE user_preferences
        SET deepgram_api_key = ?,
            notion_token = ?,
            notion_database_id = ?,
            openai_base_url = ?,
            openai_api_key = ?,
            openai_model = ?
        WHERE id = 1
    """, (deepgram_key, notion_token, notion_db_id, openai_base_url, openai_api_key, openai_model))
else:
    print("No preferences found. Inserting new record...")
    cursor.execute("""
        INSERT INTO user_preferences (
            id, notion_token, notion_database_id,
            openai_base_url, openai_api_key, openai_model,
            deepgram_api_key, encryption_enabled,
            sync_interval, sync_on_network,
            ui_language, theme_mode, max_voice_duration,
            auto_classify, auto_summarize
        ) VALUES (1, ?, ?, ?, ?, ?, ?, 0, 1800, 1, 'zh_CN', 'system', 300, 1, 1)
    """, (notion_token, notion_db_id, openai_base_url, openai_api_key, openai_model, deepgram_key))

conn.commit()
print("✅ Database initialized successfully!")

# Verify
cursor.execute("SELECT deepgram_api_key, openai_model FROM user_preferences WHERE id = 1")
result = cursor.fetchone()
if result:
    print(f"✅ Deepgram API Key: {result[0][:20]}..." if result[0] else "⚠️ Deepgram API Key: (empty)")
    print(f"✅ OpenAI Model: {result[1]}")

conn.close()
