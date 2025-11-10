"""
Update Deepgram API Key in backend database

Usage:
    python update_deepgram_key.py YOUR_API_KEY_HERE
"""

import sys
import sqlite3

if len(sys.argv) != 2:
    print("Usage: python update_deepgram_key.py YOUR_API_KEY_HERE")
    print("\nExample: python update_deepgram_key.py 44e90ac460009a2a7cd9adfee1a65de28aba654b")
    sys.exit(1)

api_key = sys.argv[1].strip()

if not api_key or len(api_key) < 20:
    print("Error: API key seems too short. Please check your key.")
    sys.exit(1)

# Database path inside Docker container
db_path = '/app/data/production.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Update the Deepgram API key
    cursor.execute(
        "UPDATE user_preferences SET deepgram_api_key = ? WHERE id = 1",
        (api_key,)
    )

    # Verify update
    cursor.execute("SELECT deepgram_api_key FROM user_preferences WHERE id = 1")
    result = cursor.fetchone()

    conn.commit()
    conn.close()

    if result:
        print(f"✓ Deepgram API key updated successfully!")
        print(f"  New key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else api_key}")
    else:
        print("✗ Failed to verify update")
        sys.exit(1)

except Exception as e:
    print(f"✗ Error updating API key: {e}")
    sys.exit(1)
