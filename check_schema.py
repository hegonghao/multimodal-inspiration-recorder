import sqlite3

conn = sqlite3.connect('/app/data/production.db')
cursor = conn.cursor()

# Check schema
cursor.execute("PRAGMA table_info(user_preferences)")
print("Columns in user_preferences:")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

# Check data
cursor.execute("SELECT id, deepgram_api_key FROM user_preferences" if 'deepgram_api_key' in str(cursor.fetchall()) else "SELECT * FROM user_preferences")
print("\nData:")
print(cursor.fetchall())

conn.close()
