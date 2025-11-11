#!/usr/bin/env python3
"""
Restore Deepgram API key to user_preferences table

This script restores the Deepgram API key that was accidentally cleared
during the LLM configuration cleanup.

Usage:
    python restore_deepgram_key.py
"""

import sqlite3
import sys

# Deepgram API key from backend/.env
DEEPGRAM_API_KEY = "823ee18611e5be6ce4a31f8a162ffd4f9a27845b"

try:
    conn = sqlite3.connect('/app/data/inspirations.db')
    cursor = conn.cursor()

    print('=' * 60)
    print('Restoring Deepgram API key to user_preferences')
    print('=' * 60)
    print('')

    # Check current configuration
    cursor.execute('SELECT openai_base_url, openai_model, deepgram_api_key FROM user_preferences WHERE id = 1')
    result = cursor.fetchone()

    if not result:
        print('❌ Error: No user preferences found (id=1)')
        sys.exit(1)

    print('📊 Current Configuration:')
    print(f'  openai_base_url: "{result[0]}"')
    print(f'  openai_model: "{result[1]}"')
    print(f'  deepgram_api_key: "{result[2][:20] if result[2] else ""}{"..." if result[2] else "(empty)"}"')
    print('')

    # Update Deepgram API key
    print('🔧 Restoring Deepgram API key...')
    cursor.execute('''
        UPDATE user_preferences
        SET deepgram_api_key = ?
        WHERE id = 1
    ''', (DEEPGRAM_API_KEY,))
    conn.commit()

    print('✅ Deepgram API key restored successfully!')
    print('')

    # Verify
    cursor.execute('SELECT openai_base_url, openai_model, deepgram_api_key FROM user_preferences WHERE id = 1')
    result = cursor.fetchone()

    print('📊 Updated Configuration:')
    print(f'  openai_base_url: "{result[0]}" (empty = uses .env)')
    print(f'  openai_model: "{result[1]}" (empty = uses .env)')
    print(f'  deepgram_api_key: "{result[2][:20]}..." (has value)')
    print('')

    print('=' * 60)
    print('✅ Configuration Summary:')
    print('=' * 60)
    print('  LLM API (OpenAI):')
    print('    - Source: backend/.env (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL)')
    print('    - Status: ✅ Database configs empty, .env will be used')
    print('')
    print('  Speech-to-Text (Deepgram):')
    print('    - Source: database (user_preferences.deepgram_api_key)')
    print('    - Status: ✅ API key restored')
    print('=' * 60)
    print('')
    print('💡 Next steps:')
    print('  1. Restart backend: docker-compose restart backend worker')
    print('  2. Test voice recording on mobile app')
    print('  3. Check logs: docker-compose logs -f backend')
    print('')

    conn.close()

except sqlite3.Error as e:
    print(f'❌ Database error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Unexpected error: {e}')
    sys.exit(1)
