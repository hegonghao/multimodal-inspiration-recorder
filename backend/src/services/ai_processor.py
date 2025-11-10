"""
AI Processor Service

Provides intelligent processing of inspiration records:
- Automatic categorization and tagging
- Content summarization
- Sentiment analysis
- Related content suggestions

Supports both Ollama (development) and OpenAI-compatible APIs (production).
"""

import asyncio
import json
from typing import Optional, Dict, Any, List
from enum import Enum

import httpx
from openai import AsyncOpenAI

from src.utils.logger import get_logger
from src.core.exceptions import ExternalServiceException

logger = get_logger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    OLLAMA = "ollama"
    CUSTOM = "custom"  # OpenAI-compatible API


class AIProcessor:
    """
    Service for AI-powered content analysis and enhancement

    Features:
    - Automatic categorization (3-5 tags per record)
    - Content summarization (1-2 sentences)
    - Sentiment analysis (positive/neutral/negative)
    - Multi-language support (Chinese/English)
    - Fast processing (<3 seconds for typical content)
    """

    def __init__(
        self,
        api_key: str,
        provider: LLMProvider = LLMProvider.OPENAI,
        base_url: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        timeout: float = 60.0,  # Increased for slow LLM APIs
    ):
        """
        Initialize AI processor

        Args:
            api_key: API key for LLM provider
            provider: LLM provider type
            base_url: Custom base URL for API (required for Ollama/custom)
            model: Model name to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.provider = provider
        self.model = model
        self.timeout = timeout

        # Initialize OpenAI client (works for all OpenAI-compatible APIs)
        client_kwargs = {
            "api_key": api_key,
            "timeout": timeout,
        }

        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = AsyncOpenAI(**client_kwargs)

        logger.info(
            f"AI Processor initialized: provider={provider}, model={model}"
        )

    async def process_content(
        self,
        content: str,
        input_type: str,
        language: str = "zh",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process content with AI to generate categories, summary, and sentiment

        Args:
            content: Text content to process
            input_type: Type of input ('voice', 'image', 'text')
            language: Content language ('zh', 'en')
            metadata: Optional metadata (e.g., confidence scores, duration)

        Returns:
            Dict containing AI processing results:
            {
                "categories": ["工作", "项目管理", "创意"],
                "summary": "关于新产品功能的创意想法",
                "sentiment": "positive",
                "confidence": 0.92,
                "keywords": ["产品", "功能", "用户体验"]
            }

        Raises:
            ExternalServiceException: If AI processing fails
        """
        try:
            logger.info(
                f"Processing content: type={input_type}, "
                f"length={len(content)}, language={language}"
            )

            # Validate content
            if not content or len(content.strip()) < 10:
                raise ValueError("Content too short for AI processing (minimum 10 characters)")

            # Build prompt based on language
            prompt = self._build_processing_prompt(content, input_type, language)

            # Call LLM API
            response = await self._call_llm(prompt, language)

            # Parse response
            result = self._parse_llm_response(response, language)

            logger.info(
                f"AI processing completed: categories={result['categories']}, "
                f"confidence={result['confidence']:.2f}"
            )

            return result

        except ValueError as e:
            logger.error(f"Invalid content: {e}")
            raise

        except Exception as e:
            logger.error(f"AI processing failed: {type(e).__name__}: {e}")
            raise ExternalServiceException(
                f"Failed to process content with AI: {str(e)}",
                error_code="AI_PROCESSING_FAILED"
            )

    async def generate_title(
        self,
        content: str,
        max_length: int = 50,
        language: str = "zh",
    ) -> str:
        """
        Generate a concise title from content

        Args:
            content: Text content
            max_length: Maximum title length
            language: Content language

        Returns:
            Generated title string
        """
        try:
            logger.info(f"Generating title for content (length={len(content)})")

            if language == "zh":
                prompt = f"""请为以下内容生成一个简洁的标题（不超过{max_length}字）：

内容：
{content[:500]}

要求：
- 标题要准确概括内容主题
- 简洁明了，不超过{max_length}字
- 只返回标题文本，不要其他内容
"""
            else:
                prompt = f"""Generate a concise title (max {max_length} characters) for the following content:

Content:
{content[:500]}

Requirements:
- Accurately summarize the main topic
- Concise and clear, max {max_length} characters
- Return only the title text, nothing else
"""

            response = await self._call_llm(prompt, language, temperature=0.7)
            title = response.strip().strip('"').strip("'")

            # Truncate if needed
            if len(title) > max_length:
                title = title[:max_length-3] + "..."

            logger.info(f"Generated title: {title}")
            return title

        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            # Fallback: use first N characters of content
            return content[:max_length-3].strip() + "..."

    async def _call_llm(
        self,
        prompt: str,
        language: str,
        temperature: float = 0.3,
        max_retries: int = 2,
    ) -> str:
        """
        Call LLM API with prompt, with retry logic for failures

        Args:
            prompt: Input prompt
            language: Response language
            temperature: Sampling temperature (0.0-1.0)
            max_retries: Maximum number of retries on failure

        Returns:
            LLM response text
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retrying LLM call (attempt {attempt + 1}/{max_retries + 1})")
                    # Increased backoff for 503 errors (service overload)
                    await asyncio.sleep(3 * attempt)  # 3s, 6s delays

                # Build system message based on language
                if language == "zh":
                    system_message = """你是一个智能内容分析助手，专门帮助用户整理和分类灵感记录。
你的任务是分析用户的输入内容，提供准确的分类标签、摘要和情感分析。
请始终使用简体中文回复，保持专业和准确。"""
                else:
                    system_message = """You are an intelligent content analysis assistant that helps users organize and categorize inspiration records.
Your task is to analyze user input and provide accurate categorization, summaries, and sentiment analysis.
Always respond in English with professionalism and accuracy."""

                # Call OpenAI-compatible API
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=500,
                )

                # Debug logging
                logger.info(f"LLM response received, model: {response.model}")
                logger.info(f"Response has {len(response.choices)} choice(s)")

                # Extract response text
                result = response.choices[0].message.content

                logger.info(f"Content extracted, length: {len(result) if result else 0}")
                logger.info(f"Content preview: {result[:100] if result else '(None)'}")
                logger.info(f"Content is None: {result is None}, empty: {result == ''}")

                if not result:
                    raise ExternalServiceException(
                        "Empty response from LLM",
                        error_code="EMPTY_LLM_RESPONSE"
                    )

                # Success! Return the result
                if attempt > 0:
                    logger.info(f"LLM call succeeded after {attempt + 1} attempts")
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"LLM API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}")

                # If this was the last attempt, raise the error
                if attempt >= max_retries:
                    logger.error(f"LLM API call failed after {max_retries + 1} attempts")
                    raise

        # Should never reach here, but just in case
        if last_error:
            raise last_error
        raise ExternalServiceException("LLM call failed with unknown error")

    def _build_processing_prompt(
        self,
        content: str,
        input_type: str,
        language: str,
    ) -> str:
        """
        Build prompt for content processing

        Args:
            content: Content to process
            input_type: Input type
            language: Content language

        Returns:
            Formatted prompt string
        """
        if language == "zh":
            prompt = f"""请分析以下灵感记录内容，并以JSON格式返回分析结果。

输入类型: {input_type}
内容:
{content}

请提供以下分析结果（必须严格按照JSON格式返回）：
1. categories: 3-5个最相关的分类标签（数组）
2. summary: 1-2句话的内容摘要（字符串）
3. sentiment: 情感倾向，只能是 "positive"、"neutral" 或 "negative" 之一（字符串）
4. keywords: 3-5个关键词（数组）

示例输出格式：
{{
  "categories": ["工作", "项目管理", "创意"],
  "summary": "关于新产品功能的创意想法，重点是提升用户体验",
  "sentiment": "positive",
  "keywords": ["产品", "功能", "用户体验", "创新", "设计"]
}}

请直接返回JSON，不要包含任何其他文本。"""

        else:
            prompt = f"""Analyze the following inspiration record and return the analysis in JSON format.

Input Type: {input_type}
Content:
{content}

Provide the following analysis (must return strict JSON format):
1. categories: 3-5 most relevant category tags (array)
2. summary: 1-2 sentence summary (string)
3. sentiment: Sentiment - must be "positive", "neutral", or "negative" (string)
4. keywords: 3-5 keywords (array)

Example output format:
{{
  "categories": ["work", "project management", "ideas"],
  "summary": "Creative ideas about new product features, focusing on user experience",
  "sentiment": "positive",
  "keywords": ["product", "features", "user experience", "innovation", "design"]
}}

Return only JSON, no other text."""

        return prompt

    def _parse_llm_response(
        self,
        response: str,
        language: str,
    ) -> Dict[str, Any]:
        """
        Parse LLM response into structured data

        Args:
            response: Raw LLM response
            language: Response language

        Returns:
            Parsed result dict
        """
        try:
            # Try to extract JSON from response
            response = response.strip()

            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            # Parse JSON
            data = json.loads(response)

            # Validate required fields
            required_fields = ["categories", "summary", "sentiment", "keywords"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Validate sentiment value
            valid_sentiments = {"positive", "neutral", "negative"}
            if data["sentiment"] not in valid_sentiments:
                logger.warning(f"Invalid sentiment: {data['sentiment']}, defaulting to neutral")
                data["sentiment"] = "neutral"

            # Ensure categories and keywords are lists
            if not isinstance(data["categories"], list):
                data["categories"] = [data["categories"]]
            if not isinstance(data["keywords"], list):
                data["keywords"] = [data["keywords"]]

            # Limit categories and keywords
            data["categories"] = data["categories"][:5]
            data["keywords"] = data["keywords"][:5]

            # Add confidence score (based on response quality)
            data["confidence"] = self._calculate_confidence(data)

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")

            # Fallback: return default structure
            return self._get_fallback_result(language)

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._get_fallback_result(language)

    def _calculate_confidence(self, data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on result quality

        Args:
            data: Parsed result data

        Returns:
            Confidence score (0.0-1.0)
        """
        confidence = 0.0

        # Categories quality (max 0.3)
        if data["categories"]:
            categories_score = min(len(data["categories"]) / 5.0, 1.0) * 0.3
            confidence += categories_score

        # Summary quality (max 0.3)
        summary = data["summary"]
        if summary and len(summary) > 10:
            summary_score = min(len(summary) / 100.0, 1.0) * 0.3
            confidence += summary_score

        # Keywords quality (max 0.2)
        if data["keywords"]:
            keywords_score = min(len(data["keywords"]) / 5.0, 1.0) * 0.2
            confidence += keywords_score

        # Sentiment presence (0.2)
        if data["sentiment"] in {"positive", "neutral", "negative"}:
            confidence += 0.2

        return min(confidence, 1.0)

    def _get_fallback_result(self, language: str) -> Dict[str, Any]:
        """
        Get fallback result when parsing fails

        Args:
            language: Result language

        Returns:
            Default result dict
        """
        if language == "zh":
            return {
                "categories": ["未分类"],
                "summary": "内容分析失败",
                "sentiment": "neutral",
                "keywords": [],
                "confidence": 0.0,
            }
        else:
            return {
                "categories": ["uncategorized"],
                "summary": "Content analysis failed",
                "sentiment": "neutral",
                "keywords": [],
                "confidence": 0.0,
            }

    async def health_check(self) -> bool:
        """
        Check if LLM API is accessible

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Simple test request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=10,
            )

            return response.choices[0].message.content is not None

        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False


# Singleton instance
_ai_processor: Optional[AIProcessor] = None


async def init_ai_processor_from_db():
    """
    Initialize AI processor with config from database (async)

    This should be called during application startup
    """
    global _ai_processor

    if _ai_processor is not None:
        return

    from src.config import settings
    from sqlalchemy import select
    from src.database.connection import engine, create_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.models.user_preferences import UserPreferences

    # Ensure engine is initialized
    if engine is None:
        create_engine()

    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(UserPreferences).limit(1))
            prefs = result.scalar_one_or_none()

            if prefs and prefs.openai_api_key:
                api_key = prefs.openai_api_key
                base_url = prefs.openai_base_url
                model = prefs.openai_model
                logger.info("Loaded LLM config from user preferences")
            else:
                api_key = settings.OPENAI_API_KEY
                base_url = settings.OPENAI_BASE_URL
                model = settings.OPENAI_MODEL
                logger.info("Using LLM config from .env")

            # Determine provider
            if base_url and 'ollama' in base_url.lower():
                provider = LLMProvider.OLLAMA
            elif base_url:
                provider = LLMProvider.CUSTOM
            else:
                provider = LLMProvider.OPENAI

            _ai_processor = AIProcessor(
                api_key=api_key,
                provider=provider,
                base_url=base_url,
                model=model,
            )

    except Exception as e:
        logger.warning(f"Failed to load user preferences: {e}, using .env defaults")
        _ai_processor = AIProcessor(
            api_key=settings.OPENAI_API_KEY,
            provider=LLMProvider.CUSTOM,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.OPENAI_MODEL,
        )


def get_ai_processor(
    api_key: Optional[str] = None,
    provider: Optional[LLMProvider] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> AIProcessor:
    """
    Get AI processor instance

    Note: Should call init_ai_processor_from_db() during startup first

    Args:
        api_key: LLM API key (for manual override)
        provider: LLM provider type
        base_url: Custom API base URL
        model: Model name

    Returns:
        AIProcessor instance
    """
    global _ai_processor

    if _ai_processor is None:
        # Fallback: create from settings if not initialized
        from src.config import settings
        logger.warning("AI processor not initialized from DB, using .env defaults")

        _ai_processor = AIProcessor(
            api_key=api_key or settings.OPENAI_API_KEY,
            provider=provider or LLMProvider.CUSTOM,
            base_url=base_url or settings.OPENAI_BASE_URL,
            model=model or settings.OPENAI_MODEL,
        )

    return _ai_processor
