#!/usr/bin/env python3
"""Check LLM configuration"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import select
from src.database import get_db
from src.models.user_preferences import UserPreferences


async def check_llm_config():
    """Check LLM configuration from user preferences"""
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        # Get user preferences
        result = await db.execute(select(UserPreferences))
        prefs = result.scalar_one_or_none()

        if prefs:
            print("\n" + "=" * 60)
            print("LLM Configuration:")
            print("=" * 60)
            print(f"OpenAI API Key: {prefs.openai_api_key[:20] if prefs.openai_api_key else 'None'}...")
            print(f"OpenAI Base URL: {prefs.openai_base_url or 'None'}")
            print(f"OpenAI Model: {prefs.openai_model or 'None'}")
            print("=" * 60)
        else:
            print("\n❌ No user preferences found!")

    finally:
        await db_gen.aclose()


if __name__ == "__main__":
    asyncio.run(check_llm_config())
