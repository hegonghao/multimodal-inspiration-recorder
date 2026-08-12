"""
AI Processor Service

Provides intelligent processing of inspiration records:
- Concise summary/title generation
- Short abstract generation

Supports both Ollama (development) and OpenAI-compatible APIs (production).
"""

import asyncio
import json
from typing import Optional, Dict, Any
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
    - Concise summary/title generation
    - Short abstract generation
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
        Process content with AI to generate a concise summary/title and abstract.

        Args:
            content: Text content to process
            input_type: Type of input ('voice', 'image', 'text')
            language: Content language ('zh', 'en')
            metadata: Optional metadata (e.g., confidence scores, duration)

        Returns:
            Dict containing ``title`` (displayed as 总结) and ``summary``
            (displayed as 摘要).

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
            result = self._parse_llm_response(response, language, content)

            logger.info("AI summary and abstract generated")

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
                    system_message = """你是一个灵感记录整理助手。
只提炼用户内容的核心总结和简短摘要，不添加原文没有的信息。
请始终使用简体中文回复。"""
                else:
                    system_message = """You organize inspiration records.
Return only a concise summary/title and a short abstract without inventing facts.
Always respond in English."""

                # Call OpenAI-compatible API
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=300,
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
            prompt = f"""请精简整理以下灵感记录，并严格返回JSON。

输入类型: {input_type}
内容:
{content}

字段要求：
1. title: 一句话概括核心内容，作为“总结”，不超过40字
2. summary: 补充关键事实的短摘要，不超过160字；不要重复标题，不要添加原文没有的信息

示例输出格式：
{{
  "title": "规划下月完成智能推荐原型",
  "summary": "团队讨论了提升用户体验的产品方案，拟加入智能推荐和个性化界面。"
}}

请直接返回JSON，不要包含任何其他文本。"""

        else:
            prompt = f"""Condense the following inspiration record and return strict JSON.

Input Type: {input_type}
Content:
{content}

Fields:
1. title: one concise sentence capturing the core point, max 60 characters
2. summary: a short abstract with key facts, max 240 characters; do not repeat the title or invent facts

Example output format:
{{
  "title": "Plan the smart recommendation prototype",
  "summary": "The team discussed personalized interfaces and aims to finish the prototype next month."
}}

Return only JSON, no other text."""

        return prompt

    def _parse_llm_response(
        self,
        response: str,
        language: str,
        content: str,
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

            # Validate and normalize the two public AI fields.
            required_fields = ["title", "summary"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            if not isinstance(data["title"], str) or not isinstance(data["summary"], str):
                raise ValueError("title and summary must be strings")

            title_limit = 40 if language == "zh" else 60
            summary_limit = 160 if language == "zh" else 240
            data["title"] = self._truncate_text(data["title"], title_limit)
            data["summary"] = self._truncate_text(data["summary"], summary_limit)
            if not data["title"] or not data["summary"]:
                raise ValueError("title and summary must not be empty")

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")

            # Fallback: return default structure
            return self._get_fallback_result(content, language)

        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._get_fallback_result(content, language)

    @staticmethod
    def _truncate_text(value: str, max_length: int) -> str:
        value = value.strip().strip('"').strip("'")
        if len(value) <= max_length:
            return value
        return value[: max_length - 3].rstrip() + "..."

    def _get_fallback_result(self, content: str, language: str) -> Dict[str, Any]:
        """
        Get fallback result when parsing fails

        Args:
            language: Result language

        Returns:
            Default result dict
        """
        title_limit = 40 if language == "zh" else 60
        summary_limit = 160 if language == "zh" else 240
        compact_content = " ".join(content.split())
        return {
            "title": self._truncate_text(compact_content, title_limit),
            "summary": self._truncate_text(compact_content, summary_limit),
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
