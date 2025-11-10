#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/production.db')

# Check tables
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables in production.db:')
for t in tables:
    print(f'  - {t[0]}')

# Check record 26
try:
    cursor = conn.execute("""
        SELECT id, title, category_tags, summary, ai_processing_status
        FROM inspiration_records
        WHERE id=26
    """)
    row = cursor.fetchone()
    if row:
        print(f'\nRecord 26 in production.db:')
        print(f'  ID: {row[0]}')
        print(f'  Title: {row[1][:60]}')
        print(f'  Category Tags: {row[2]}')
        print(f'  Summary: {row[3]}')
        print(f'  AI Status: {row[4]}')
    else:
        print('\nRecord 26 not found')
except Exception as e:
    print(f'Error: {e}')

conn.close()
