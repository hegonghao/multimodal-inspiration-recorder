#!/usr/bin/env python3
"""Update database configuration from .env file"""
import sqlite3
import os
from pathlib import Path

# Load .env file
env_file = Path(__file__).parent / ".env"
env_vars = {}

if env_file.exists():
    with open(env_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

# Extract configuration
openai_api_key = env_vars.get('OPENAI_API_KEY', '')
openai_base_url = env_vars.get('OPENAI_BASE_URL', '')
openai_model = env_vars.get('OPENAI_MODEL', 'gpt-4o-mini')
deepgram_api_key = env_vars.get('DEEPGRAM_API_KEY', '')
notion_token = env_vars.get('NOTION_TOKEN', '')
notion_database_id = env_vars.get('NOTION_DATABASE_ID', '')

print("Configuration from .env:")
print(f"  OpenAI API Key: {openai_api_key[:20]}..." if openai_api_key else "  OpenAI API Key: (empty)")
print(f"  OpenAI Base URL: {openai_base_url}")
print(f"  OpenAI Model: {openai_model}")
print(f"  Deepgram API Key: {deepgram_api_key[:20]}..." if deepgram_api_key else "  Deepgram API Key: (empty)")
print(f"  Notion Token: {notion_token[:20]}..." if notion_token else "  Notion Token: (empty)")
print(f"  Notion DB ID: {notion_database_id}")

# Connect to database
DB_PATH = "data/inspirations.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Update user preferences
cursor.execute("""
    UPDATE user_preferences
    SET
        openai_api_key = ?,
        openai_base_url = ?,
        openai_model = ?,
        deepgram_api_key = ?,
        notion_token = ?,
        notion_database_id = ?
    WHERE id = 1
""", (
    openai_api_key if openai_api_key else None,
    openai_base_url,
    openai_model,
    deepgram_api_key,
    notion_token if notion_token else None,
    notion_database_id if notion_database_id else None,
))

conn.commit()

# Verify update
cursor.execute("""
    SELECT
        id,
        SUBSTR(openai_api_key, 1, 20) || '...' as openai_key,
        openai_base_url,
        openai_model,
        SUBSTR(deepgram_api_key, 1, 20) || '...' as deepgram_key,
        SUBSTR(notion_token, 1, 20) || '...' as notion_token,
        notion_database_id
    FROM user_preferences
    WHERE id = 1
""")

result = cursor.fetchone()
if result:
    print("\nConfiguration updated in database:")
    print(f"  ID: {result[0]}")
    print(f"  OpenAI Key: {result[1]}")
    print(f"  OpenAI Base URL: {result[2]}")
    print(f"  OpenAI Model: {result[3]}")
    print(f"  Deepgram Key: {result[4]}")
    print(f"  Notion Token: {result[5]}")
    print(f"  Notion DB ID: {result[6]}")
    print("\nUpdate successful!")
else:
    print("No configuration found! Run init_db.py first")

conn.close()
