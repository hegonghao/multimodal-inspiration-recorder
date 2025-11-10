"""
AI Processing API Endpoints

Handles LLM-based classification and summarization
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any
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


class ClassifyRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=10000)
    language: str = Field("zh", pattern="^(zh|en)$")


class ClassifyResponse(BaseModel):
    categories: List[str]
    keywords: List[str]
    sentiment: str
    confidence: float


class SummarizeRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=10000)
    max_length: int = Field(50, ge=20, le=200)
    language: str = Field("zh", pattern="^(zh|en)$")


class SummarizeResponse(BaseModel):
    summary: str
    confidence: float


class ProcessRequest(BaseModel):
    content: str = Field(..., min_length=10, max_length=10000)
    input_type: str
    max_summary_length: int = Field(50, ge=20, le=200)
    language: str = Field("zh", pattern="^(zh|en)$")


class ProcessResponse(BaseModel):
    categories: List[str]
    summary: str
    sentiment: str
    keywords: List[str]
    confidence: float


@router.post("/classify", response_model=ClassifyResponse)
async def classify_content(
    request: ClassifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Classify content using LLM

    Returns categories, keywords, and sentiment analysis
    """
    try:
        logger.info(f"Classifying content: length={len(request.content)}")

        ai_processor = await get_ai_processor_from_prefs(db)
        result = await ai_processor.process_content(
            content=request.content,
            input_type="text",
            language=request.language,
        )

        return ClassifyResponse(
            categories=result["categories"],
            keywords=result["keywords"],
            sentiment=result["sentiment"],
            confidence=result["confidence"],
        )

    except HTTPException:
        raise
    except ExternalServiceException as e:
        logger.error(f"Classification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during classification"
        )


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_content(
    request: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate summary using LLM

    Returns a concise summary of the content
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
            summary=result["summary"],
            confidence=result["confidence"],
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
    Perform both classification and summarization in one call

    Returns complete AI analysis including categories, summary, sentiment, and keywords
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
            categories=result["categories"],
            summary=result["summary"],
            sentiment=result["sentiment"],
            keywords=result["keywords"],
            confidence=result["confidence"],
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
