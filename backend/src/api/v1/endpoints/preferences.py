"""
User Preferences API Endpoints

Manages user configuration and integration settings
"""

import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import structlog

from src.database.connection import get_db
from src.models.user_preferences import (
    UserPreferences,
    UserPreferencesUpdate,
    UserPreferencesResponse,
    NotionConnectionTest,
    LLMConnectionTest,
    ConnectionTestResponse,
)
from src.services.notion_sync import NotionSyncService
from src.services.ai_processor import AIProcessor, LLMProvider

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("", response_model=UserPreferencesResponse)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
):
    """
    Get user preferences

    Returns current user configuration including:
    - Notion database ID (token excluded for security)
    - LLM API settings
    - Sync configuration
    - UI preferences

    **Note**: Sensitive fields (tokens/keys) are never returned
    """
    try:
        logger.info("get_preferences_requested")

        # Fetch preferences (single-user mode: id=1)
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.id == 1)
        )
        prefs = result.scalar_one_or_none()

        if not prefs:
            # Create default preferences if not exists
            prefs = UserPreferences(id=1)
            db.add(prefs)
            await db.commit()
            await db.refresh(prefs)
            logger.info("default_preferences_created")

        logger.info("preferences_retrieved", openai_model=prefs.openai_model)
        return UserPreferencesResponse.model_validate(prefs)

    except Exception as e:
        logger.error("get_preferences_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve preferences: {str(e)}",
        )


@router.put("", response_model=UserPreferencesResponse)
async def update_preferences(
    preferences: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update user preferences

    Allows partial updates - only provided fields will be modified.

    **Security**: Tokens and API keys are write-only and never returned
    """
    try:
        logger.info("update_preferences_requested")

        # Fetch existing preferences
        result = await db.execute(
            select(UserPreferences).where(UserPreferences.id == 1)
        )
        prefs = result.scalar_one_or_none()

        if not prefs:
            # Create if not exists
            prefs = UserPreferences(id=1)
            db.add(prefs)

        # Update only provided fields
        update_data = preferences.model_dump(exclude_unset=True)

        if not update_data:
            logger.warning("no_fields_to_update")
            return UserPreferencesResponse.model_validate(prefs)

        # Apply updates
        for field, value in update_data.items():
            if hasattr(prefs, field):
                setattr(prefs, field, value)

        await db.commit()
        await db.refresh(prefs)

        logger.info(
            "preferences_updated",
            updated_fields=list(update_data.keys()),
        )

        return UserPreferencesResponse.model_validate(prefs)

    except Exception as e:
        logger.error("update_preferences_failed", error=str(e), exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}",
        )


@router.post("/test-notion", response_model=ConnectionTestResponse)
async def test_notion_connection(
    test: NotionConnectionTest,
):
    """
    Test Notion API connection

    Validates:
    - Token format and validity
    - Database ID format
    - API accessibility
    - Database permissions

    **Example Request:**
    ```json
    {
      "notion_token": "secret_abc123...",
      "notion_database_id": "a1b2c3d4e5f67890"
    }
    ```

    **Example Success Response:**
    ```json
    {
      "success": true,
      "message": "Notion连接成功",
      "details": {
        "database_title": "灵感记录",
        "response_time_ms": 350
      }
    }
    ```
    """
    logger.info("test_notion_connection_requested")

    start_time = time.time()

    try:
        # Initialize Notion service
        notion_service = NotionSyncService(
            notion_token=test.notion_token,
            database_id=test.notion_database_id,
        )

        # Test connection
        success = await notion_service.verify_connection()

        response_time_ms = int((time.time() - start_time) * 1000)

        await notion_service.close()

        if success:
            logger.info("notion_connection_test_passed", response_time_ms=response_time_ms)
            return ConnectionTestResponse(
                success=True,
                message="Notion连接成功,数据库访问正常",
                details={
                    "response_time_ms": response_time_ms,
                    "database_id": test.notion_database_id,
                },
            )
        else:
            logger.warning("notion_connection_test_failed")
            return ConnectionTestResponse(
                success=False,
                message="Notion连接失败,请检查Token和Database ID是否正确",
                details={"response_time_ms": response_time_ms},
            )

    except ValueError as e:
        # Configuration error
        logger.warning("notion_connection_config_error", error=str(e))
        return ConnectionTestResponse(
            success=False,
            message=f"配置错误: {str(e)}",
            details={"error_type": "configuration_error"},
        )

    except Exception as e:
        # Unexpected error
        logger.error("notion_connection_test_exception", error=str(e), exc_info=True)
        return ConnectionTestResponse(
            success=False,
            message=f"连接测试失败: {str(e)}",
            details={"error_type": type(e).__name__},
        )


@router.post("/test-llm", response_model=ConnectionTestResponse)
async def test_llm_connection(
    test: LLMConnectionTest,
):
    """
    Test LLM API connection

    Validates:
    - API endpoint accessibility
    - API key validity (if required)
    - Model availability
    - Response generation

    **Example Request:**
    ```json
    {
      "openai_base_url": "http://localhost:11434/v1",
      "openai_model": "llama3.1",
      "openai_api_key": null
    }
    ```

    **Example Success Response:**
    ```json
    {
      "success": true,
      "message": "LLM连接成功",
      "details": {
        "model": "llama3.1",
        "response_time_ms": 1250,
        "test_output": "你好!"
      }
    }
    ```
    """
    logger.info("test_llm_connection_requested", model=test.openai_model)

    start_time = time.time()

    try:
        # Initialize AI processor
        processor = AIProcessor(
            api_key=test.openai_api_key or "not-needed-for-ollama",
            provider=LLMProvider.CUSTOM,
            base_url=test.openai_base_url,
            model=test.openai_model,
        )

        # Test with simple prompt
        success = await processor.health_check()

        response_time_ms = int((time.time() - start_time) * 1000)

        if success:
            logger.info("llm_connection_test_passed", response_time_ms=response_time_ms)
            return ConnectionTestResponse(
                success=True,
                message="LLM连接成功,模型响应正常",
                details={
                    "model": test.openai_model,
                    "base_url": test.openai_base_url,
                    "response_time_ms": response_time_ms,
                },
            )
        else:
            logger.warning("llm_connection_test_failed")
            return ConnectionTestResponse(
                success=False,
                message="LLM连接失败,请检查API地址和模型名称是否正确",
                details={
                    "response_time_ms": response_time_ms,
                    "base_url": test.openai_base_url,
                },
            )

    except Exception as e:
        # Connection or API error
        logger.error("llm_connection_test_exception", error=str(e), exc_info=True)

        error_message = str(e)
        if "Connection" in error_message or "connection" in error_message.lower():
            message = f"无法连接到LLM服务: {test.openai_base_url}"
        elif "API" in error_message or "api" in error_message.lower():
            message = "API调用失败,请检查API Key和模型名称"
        else:
            message = f"LLM测试失败: {error_message}"

        return ConnectionTestResponse(
            success=False,
            message=message,
            details={
                "error_type": type(e).__name__,
                "base_url": test.openai_base_url,
                "model": test.openai_model,
            },
        )
