"""
AI Processing API Endpoints

Handles LLM-based summary and abstract generation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.services.ai_processor import AIProcessor, LLMProvider
from src.models.user_preferences import UserPreferences
from src.database.connection import get_db
from src.core.exceptions import ExternalServiceException
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def get_ai_processor_from_prefs(db: AsyncSession) -> AIProcessor:
    """
    Get AI processor configured from user preferences

    Args:
        db: Database session

    Returns:
        Configured AIProcessor instance

    Raises:
        HTTPException: If preferences not found or invalid
    """
    # Fetch user preferences from database
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.id == 1)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured. Please configure LLM settings in preferences."
        )

    if not prefs.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key not configured. Please add your API key in preferences."
        )

    # Determine provider based on base_url
    provider = LLMProvider.CUSTOM
    if prefs.openai_base_url:
        if 'ollama' in prefs.openai_base_url.lower():
            provider = LLMProvider.OLLAMA
        elif 'openai.com' in prefs.openai_base_url.lower():
            provider = LLMProvider.OPENAI

    # Create AI processor with user preferences
    return AIProcessor(
        api_key=prefs.openai_api_key,
        provider=provider,
        base_url=prefs.openai_base_url,
        model=prefs.openai_model,
    )


class SummarizeRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=10000)
    max_length: int = Field(50, ge=20, le=200)
    language: str = Field("zh", pattern="^(zh|en)$")


class SummarizeResponse(BaseModel):
    title: str
    summary: str


class ProcessRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=10000)
    input_type: str
    max_summary_length: int = Field(50, ge=20, le=200)
    language: str = Field("zh", pattern="^(zh|en)$")


class ProcessResponse(BaseModel):
    title: str
    summary: str


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_content(
    request: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate the concise summary/title and short abstract using LLM.

    ``title`` is displayed as 总结 and ``summary`` as 摘要.
    """
    try:
        logger.info(f"Summarizing content: length={len(request.content)}")

        ai_processor = await get_ai_processor_from_prefs(db)
        result = await ai_processor.process_content(
            content=request.content,
            input_type="text",
            language=request.language,
        )

        return SummarizeResponse(
            title=result["title"],
            summary=result["summary"],
        )

    except HTTPException:
        raise
    except ExternalServiceException as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during summarization"
        )


@router.post("/process", response_model=ProcessResponse)
async def process_content(
    request: ProcessRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate the normalized AI fields in one call.

    Returns only the concise summary/title and short abstract.
    """
    try:
        logger.info(
            f"Processing content: type={request.input_type}, "
            f"length={len(request.content)}, language={request.language}"
        )

        ai_processor = await get_ai_processor_from_prefs(db)
        result = await ai_processor.process_content(
            content=request.content,
            input_type=request.input_type,
            language=request.language,
        )

        return ProcessResponse(
            title=result["title"],
            summary=result["summary"],
        )

    except HTTPException:
        raise
    except ExternalServiceException as e:
        logger.error(f"Content processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during content processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during content processing"
        )
