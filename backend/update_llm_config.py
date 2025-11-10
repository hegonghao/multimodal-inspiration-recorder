"""
Update LLM configuration in user_preferences table
"""
import asyncio
import os
from sqlalchemy import text
from src.database.connection import get_async_session

async def update_llm_config():
    """Update LLM configuration from environment variables"""

    # Get configuration from environment
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    print(f"Updating LLM config:")
    print(f"  API Key: {api_key[:20]}..." if api_key else "  API Key: None")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")

    async for session in get_async_session():
        try:
            # Check if user_preferences exists
            result = await session.execute(
                text("SELECT COUNT(*) FROM user_preferences")
            )
            count = result.scalar()
            print(f"\nFound {count} user_preferences records")

            if count == 0:
                # Insert default preferences
                await session.execute(
                    text("""
                        INSERT INTO user_preferences
                        (openai_api_key, openai_base_url, openai_model, openai_max_tokens, openai_temperature)
                        VALUES (:api_key, :base_url, :model, 1000, 0.7)
                    """),
                    {
                        "api_key": api_key,
                        "base_url": base_url,
                        "model": model
                    }
                )
                print("✓ Inserted new user preferences")
            else:
                # Update existing preferences
                await session.execute(
                    text("""
                        UPDATE user_preferences
                        SET openai_api_key = :api_key,
                            openai_base_url = :base_url,
                            openai_model = :model,
                            openai_max_tokens = 1000,
                            openai_temperature = 0.7
                        WHERE id = 1
                    """),
                    {
                        "api_key": api_key,
                        "base_url": base_url,
                        "model": model
                    }
                )
                print("✓ Updated existing user preferences")

            await session.commit()

            # Verify update
            result = await session.execute(
                text("SELECT openai_api_key, openai_base_url, openai_model FROM user_preferences WHERE id = 1")
            )
            row = result.fetchone()
            if row:
                print(f"\nVerification:")
                print(f"  API Key: {row[0][:20]}..." if row[0] else "  API Key: None")
                print(f"  Base URL: {row[1]}")
                print(f"  Model: {row[2]}")

            print("\n✓ LLM configuration updated successfully!")

        except Exception as e:
            print(f"\n✗ Error: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(update_llm_config())
