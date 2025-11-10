"""
Update user preferences with correct LLM API configuration
"""
import asyncio
from src.database import get_db
from src.models.user_preferences import UserPreferences
from sqlalchemy import select

async def update_prefs():
    """Update LLM config in user preferences"""
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        # Get existing preferences
        result = await db.execute(select(UserPreferences))
        prefs = result.scalar_one_or_none()

        if prefs:
            print(f"Found existing preferences (ID: {prefs.id})")
            print(f"  Current API Key: {prefs.openai_api_key[:20] if prefs.openai_api_key else 'None'}...")
            print(f"  Current Base URL: {prefs.openai_base_url}")
            print(f"  Current Model: {prefs.openai_model}")

            # Update with correct config
            prefs.openai_api_key = "sk-AUwTbAHEb85Lty150eDaC6335e464bCf99CaF5C0Fa00C98f"
            prefs.openai_base_url = "https://cnapi.kksj.org/v1"
            prefs.openai_model = "gpt-4o-mini"

            await db.commit()
            await db.refresh(prefs)

            print("\nUpdated preferences:")
            print(f"  New API Key: {prefs.openai_api_key[:20]}...")
            print(f"  New Base URL: {prefs.openai_base_url}")
            print(f"  New Model: {prefs.openai_model}")
        else:
            print("No user preferences found - creating new record")

            # Create new preferences
            new_prefs = UserPreferences(
                openai_api_key="sk-AUwTbAHEb85Lty150eDaC6335e464bCf99CaF5C0Fa00C98f",
                openai_base_url="https://cnapi.kksj.org/v1",
                openai_model="gpt-4o-mini",
            )

            db.add(new_prefs)
            await db.commit()
            await db.refresh(new_prefs)

            print(f"Created preferences (ID: {new_prefs.id})")
            print(f"  API Key: {new_prefs.openai_api_key[:20]}...")
            print(f"  Base URL: {new_prefs.openai_base_url}")
            print(f"  Model: {new_prefs.openai_model}")

    finally:
        await db_gen.aclose()

if __name__ == "__main__":
    asyncio.run(update_prefs())
