"""
Contract Tests for AI Processing

Tests AI processor service contract including:
- Content categorization
- Summarization
- Title generation
- Sentiment analysis
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.ai_processor import (
    AIProcessor,
    LLMProvider,
)


@pytest.mark.asyncio
class TestAIProcessorContract:
    """Contract tests for AI processor service"""

    @pytest.fixture
    def sample_content_chinese(self):
        """Sample Chinese content for testing"""
        return """
        今天开会讨论了新产品的功能设计，重点是提升用户体验。
        团队提出了几个创新的想法，包括智能推荐系统和个性化界面。
        项目经理强调要在下个月完成原型开发。
        """

    @pytest.fixture
    def sample_content_english(self):
        """Sample English content for testing"""
        return """
        We had a meeting today to discuss the new product features.
        The focus was on improving user experience through innovative design.
        The team proposed several ideas including AI recommendations.
        """

    @pytest.fixture
    def mock_ai_processor(self):
        """Create AI processor with mocked LLM client"""
        with patch('src.services.ai_processor.AsyncOpenAI') as mock_client:
            # Create processor
            processor = AIProcessor(
                api_key="test-key",
                provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
            )

            # Setup mock response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '''
            {
                "categories": ["工作", "产品开发", "团队协作"],
                "summary": "讨论新产品功能设计，重点提升用户体验",
                "sentiment": "positive",
                "keywords": ["产品", "用户体验", "创新", "设计"]
            }
            '''

            processor.client.chat.completions.create = AsyncMock(
                return_value=mock_response
            )

            yield processor

    # ==================== Content Processing Tests ====================

    async def test_process_content_success(self, mock_ai_processor, sample_content_chinese):
        """Test successful content processing"""
        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        # Assert result structure
        assert "categories" in result
        assert "summary" in result
        assert "sentiment" in result
        assert "keywords" in result
        assert "confidence" in result

        # Assert data types
        assert isinstance(result["categories"], list)
        assert isinstance(result["summary"], str)
        assert isinstance(result["sentiment"], str)
        assert isinstance(result["keywords"], list)
        assert isinstance(result["confidence"], float)

        # Assert value constraints
        assert result["sentiment"] in ["positive", "neutral", "negative"]
        assert 0.0 <= result["confidence"] <= 1.0
        assert 1 <= len(result["categories"]) <= 5
        assert 1 <= len(result["keywords"]) <= 5

    async def test_process_content_too_short(self, mock_ai_processor):
        """Test processing fails with content too short"""
        with pytest.raises(ValueError) as exc_info:
            await mock_ai_processor.process_content(
                content="短",  # Only 1 character
                input_type="text",
                language="zh",
            )

        assert "too short" in str(exc_info.value).lower()

    async def test_process_content_different_input_types(self, mock_ai_processor, sample_content_chinese):
        """Test processing different input types"""
        input_types = ["voice", "image", "text"]

        for input_type in input_types:
            result = await mock_ai_processor.process_content(
                content=sample_content_chinese,
                input_type=input_type,
                language="zh",
            )

            assert result is not None
            assert "categories" in result
            assert "summary" in result

    async def test_process_content_different_languages(self, mock_ai_processor, sample_content_english):
        """Test processing different languages"""
        # English
        result = await mock_ai_processor.process_content(
            content=sample_content_english,
            input_type="text",
            language="en",
        )

        assert result is not None
        assert isinstance(result["categories"], list)

    # ==================== Title Generation Tests ====================

    async def test_generate_title_success(self, mock_ai_processor, sample_content_chinese):
        """Test successful title generation"""
        # Mock response for title generation
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="产品功能设计讨论"))]
            )
        )

        title = await mock_ai_processor.generate_title(
            content=sample_content_chinese,
            max_length=50,
            language="zh",
        )

        # Assert title properties
        assert isinstance(title, str)
        assert len(title) > 0
        assert len(title) <= 50

    async def test_generate_title_respects_max_length(self, mock_ai_processor):
        """Test title generation respects max length"""
        # Mock very long title
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="这是一个非常非常长的标题用于测试最大长度限制功能是否正常工作"
                ))]
            )
        )

        max_length = 20
        title = await mock_ai_processor.generate_title(
            content="测试内容" * 10,
            max_length=max_length,
            language="zh",
        )

        assert len(title) <= max_length

    async def test_generate_title_fallback(self, mock_ai_processor, sample_content_chinese):
        """Test title generation fallback when LLM fails"""
        # Mock LLM failure
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            side_effect=Exception("LLM error")
        )

        title = await mock_ai_processor.generate_title(
            content=sample_content_chinese,
            max_length=50,
            language="zh",
        )

        # Should return fallback title (first N characters)
        assert isinstance(title, str)
        assert len(title) > 0
        # Fallback should be substring of content (with whitespace trimmed)
        assert title in sample_content_chinese or sample_content_chinese.strip().startswith(title.rstrip("..."))

    # ==================== Response Parsing Tests ====================

    async def test_parse_malformed_json(self, mock_ai_processor, sample_content_chinese):
        """Test handling of malformed JSON from LLM"""
        # Mock malformed JSON response
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content="This is not valid JSON"
                ))]
            )
        )

        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        # Should return fallback result
        assert "categories" in result
        assert result["categories"] == ["未分类"] or result["categories"] == ["uncategorized"]
        assert result["confidence"] == 0.0

    async def test_parse_json_with_markdown(self, mock_ai_processor, sample_content_chinese):
        """Test parsing JSON wrapped in markdown code blocks"""
        # Mock JSON in markdown
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='''```json
                    {
                        "categories": ["工作"],
                        "summary": "测试摘要",
                        "sentiment": "positive",
                        "keywords": ["测试"]
                    }
                    ```'''
                ))]
            )
        )

        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        # Should parse successfully
        assert result["categories"] == ["工作"]
        assert result["sentiment"] == "positive"

    async def test_validate_sentiment_values(self, mock_ai_processor, sample_content_chinese):
        """Test sentiment validation"""
        # Mock invalid sentiment
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='''
                    {
                        "categories": ["工作"],
                        "summary": "测试",
                        "sentiment": "invalid_value",
                        "keywords": ["测试"]
                    }
                    '''
                ))]
            )
        )

        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        # Should default to neutral
        assert result["sentiment"] in ["positive", "neutral", "negative"]

    # ==================== Confidence Calculation Tests ====================

    async def test_confidence_calculation(self, mock_ai_processor, sample_content_chinese):
        """Test confidence score calculation"""
        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        confidence = result["confidence"]

        # Confidence should be between 0 and 1
        assert 0.0 <= confidence <= 1.0

        # Confidence should be higher with complete results
        if result["categories"] and result["summary"] and result["keywords"]:
            assert confidence > 0.5

    # ==================== Provider Configuration Tests ====================

    def test_processor_initialization_openai(self):
        """Test processor initialization with OpenAI"""
        processor = AIProcessor(
            api_key="test-key",
            provider=LLMProvider.OPENAI,
            model="gpt-3.5-turbo",
        )

        assert processor.api_key == "test-key"
        assert processor.provider == LLMProvider.OPENAI
        assert processor.model == "gpt-3.5-turbo"

    def test_processor_initialization_ollama(self):
        """Test processor initialization with Ollama"""
        processor = AIProcessor(
            api_key="test-key",
            provider=LLMProvider.OLLAMA,
            base_url="http://localhost:11434",
            model="llama2",
        )

        assert processor.provider == LLMProvider.OLLAMA
        assert processor.model == "llama2"

    def test_processor_initialization_custom(self):
        """Test processor initialization with custom provider"""
        processor = AIProcessor(
            api_key="test-key",
            provider=LLMProvider.CUSTOM,
            base_url="https://custom-api.example.com",
            model="custom-model",
        )

        assert processor.provider == LLMProvider.CUSTOM

    # ==================== Health Check Tests ====================

    async def test_health_check_success(self, mock_ai_processor):
        """Test health check succeeds"""
        # Mock successful health check
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content="OK"))]
            )
        )

        result = await mock_ai_processor.health_check()

        assert result is True

    async def test_health_check_failure(self, mock_ai_processor):
        """Test health check fails"""
        # Mock failed health check
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            side_effect=Exception("Connection error")
        )

        result = await mock_ai_processor.health_check()

        assert result is False

    # ==================== Edge Cases ====================

    async def test_empty_categories_list(self, mock_ai_processor, sample_content_chinese):
        """Test handling of empty categories"""
        # Mock empty categories
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='''
                    {
                        "categories": [],
                        "summary": "测试摘要",
                        "sentiment": "neutral",
                        "keywords": ["测试"]
                    }
                    '''
                ))]
            )
        )

        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        # Should handle empty categories
        assert isinstance(result["categories"], list)

    async def test_categories_limit(self, mock_ai_processor, sample_content_chinese):
        """Test categories are limited to 5"""
        # Mock too many categories
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='''
                    {
                        "categories": ["A", "B", "C", "D", "E", "F", "G"],
                        "summary": "测试",
                        "sentiment": "neutral",
                        "keywords": ["测试"]
                    }
                    '''
                ))]
            )
        )

        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        # Should limit to 5
        assert len(result["categories"]) <= 5

    async def test_keywords_limit(self, mock_ai_processor, sample_content_chinese):
        """Test keywords are limited to 5"""
        # Mock too many keywords
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(
                    content='''
                    {
                        "categories": ["工作"],
                        "summary": "测试",
                        "sentiment": "neutral",
                        "keywords": ["K1", "K2", "K3", "K4", "K5", "K6", "K7"]
                    }
                    '''
                ))]
            )
        )

        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        # Should limit to 5
        assert len(result["keywords"]) <= 5
