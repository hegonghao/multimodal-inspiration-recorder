#!/usr/bin/env python3
"""
Clear API configurations from user_preferences table

This script clears the OpenAI and Deepgram configurations that were incorrectly
set by the mobile app, allowing the backend to fall back to .env defaults.

Usage:
    python clear_app_api_configs.py
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select, update
from src.models.user_preferences import UserPreferences
from src.config import settings
import structlog

logger = structlog.get_logger(__name__)


async def clear_api_configs():
    """Clear API configurations from database"""

    print("=" * 60)
    print("Clearing API configurations from user_preferences")
    print("=" * 60)

    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL.replace('sqlite:///', 'sqlite+aiosqlite:///'),
        echo=False,
    )

    try:
        async with AsyncSession(engine) as session:
            # Fetch current preferences
            result = await session.execute(
                select(UserPreferences).where(UserPreferences.id == 1)
            )
            prefs = result.scalar_one_or_none()

            if not prefs:
                print("❌ No preferences found (id=1)")
                return

            print("\n📊 Current Configuration:")
            print(f"  OpenAI Base URL: {prefs.openai_base_url}")
            print(f"  OpenAI Model: {prefs.openai_model}")
            print(f"  OpenAI API Key: {'***' + prefs.openai_api_key[-10:] if prefs.openai_api_key else 'None'}")
            print(f"  Deepgram API Key: {'***' + prefs.deepgram_api_key[-10:] if prefs.deepgram_api_key else 'None'}")

            # Clear the configurations
            print("\n🧹 Clearing configurations...")
            await session.execute(
                update(UserPreferences)
                .where(UserPreferences.id == 1)
                .values(
                    openai_base_url="",
                    openai_api_key=None,
                    openai_model="",
                    deepgram_api_key="",
                )
            )
            await session.commit()

            print("✅ Configurations cleared successfully!")

            # Verify
            result = await session.execute(
                select(UserPreferences).where(UserPreferences.id == 1)
            )
            prefs = result.scalar_one_or_none()

            print("\n📊 Updated Configuration:")
            print(f"  OpenAI Base URL: '{prefs.openai_base_url}' (empty = will use .env)")
            print(f"  OpenAI Model: '{prefs.openai_model}' (empty = will use .env)")
            print(f"  OpenAI API Key: {prefs.openai_api_key or '(null = will use .env)'}")
            print(f"  Deepgram API Key: '{prefs.deepgram_api_key}' (empty = will use .env)")

            print("\n" + "=" * 60)
            print("✅ Backend will now use .env configurations:")
            print("=" * 60)
            print(f"  OPENAI_BASE_URL={settings.OPENAI_BASE_URL}")
            print(f"  OPENAI_MODEL={settings.OPENAI_MODEL}")
            print(f"  OPENAI_API_KEY={'***' + settings.OPENAI_API_KEY[-10:]}")
            print(f"  DEEPGRAM_API_KEY={'***' + settings.DEEPGRAM_API_KEY[-10:]}")
            print("=" * 60)

            print("\n💡 Next steps:")
            print("  1. Restart backend and worker containers:")
            print("     docker-compose restart backend worker")
            print("  2. Test by creating a voice record on mobile app")
            print("  3. Check logs for successful LLM API calls")

    except Exception as e:
        logger.error(f"Failed to clear configurations: {e}")
        raise

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clear_api_configs())
