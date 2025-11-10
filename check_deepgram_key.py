import asyncio
from sqlalchemy import select
from backend.src.database.connection import get_db
from backend.src.models.user_preferences import UserPreferences

async def check_key():
    async for db in get_db():
        result = await db.execute(select(UserPreferences).where(UserPreferences.id == 1))
        prefs = result.scalar_one_or_null()
        if prefs:
            print(f"Deepgram API Key: {prefs.deepgram_api_key}")
        else:
            print("No user preferences found")
        break

asyncio.run(check_key())
