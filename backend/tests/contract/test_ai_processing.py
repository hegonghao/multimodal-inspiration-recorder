"""Contract tests for concise AI summary generation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.ai_processor import AIProcessor, LLMProvider


@pytest.mark.asyncio
class TestAIProcessorContract:
    @pytest.fixture
    def sample_content_chinese(self):
        return (
            "今天开会讨论了新产品的功能设计，重点是提升用户体验。"
            "团队提出智能推荐系统和个性化界面，并计划下个月完成原型。"
        )

    @pytest.fixture
    def mock_ai_processor(self):
        with patch("src.services.ai_processor.AsyncOpenAI"):
            processor = AIProcessor(
                api_key="test-key",
                provider=LLMProvider.OPENAI,
                model="gpt-3.5-turbo",
            )
            response = MagicMock()
            response.model = "gpt-3.5-turbo"
            response.choices = [MagicMock()]
            response.choices[0].message.content = """
            {
                "title": "规划智能推荐产品原型",
                "summary": "团队讨论了个性化界面和智能推荐方案，计划下个月完成原型。"
            }
            """
            processor.client.chat.completions.create = AsyncMock(
                return_value=response
            )
            yield processor

    async def test_process_content_returns_only_normalized_fields(
        self, mock_ai_processor, sample_content_chinese
    ):
        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        assert set(result) == {"title", "summary"}
        assert result["title"] == "规划智能推荐产品原型"
        assert "下个月完成原型" in result["summary"]

    async def test_process_content_too_short(self, mock_ai_processor):
        with pytest.raises(ValueError, match="too short"):
            await mock_ai_processor.process_content(
                content="短",
                input_type="text",
                language="zh",
            )

    async def test_parse_markdown_json(
        self, mock_ai_processor, sample_content_chinese
    ):
        response = MagicMock()
        response.model = "gpt-3.5-turbo"
        response.choices = [MagicMock()]
        response.choices[0].message.content = """```json
        {"title": "产品原型计划", "summary": "下个月完成智能推荐原型。"}
        ```"""
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=response
        )

        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        assert result == {
            "title": "产品原型计划",
            "summary": "下个月完成智能推荐原型。",
        }

    async def test_malformed_json_falls_back_to_content(
        self, mock_ai_processor, sample_content_chinese
    ):
        response = MagicMock()
        response.model = "gpt-3.5-turbo"
        response.choices = [MagicMock()]
        response.choices[0].message.content = "not json"
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=response
        )

        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        assert set(result) == {"title", "summary"}
        assert result["title"]
        assert result["summary"]
        assert len(result["title"]) <= 40
        assert len(result["summary"]) <= 160

    async def test_generated_fields_are_truncated(
        self, mock_ai_processor, sample_content_chinese
    ):
        response = MagicMock()
        response.model = "gpt-3.5-turbo"
        response.choices = [MagicMock()]
        response.choices[0].message.content = (
            '{"title": "' + "总" * 80 + '", "summary": "' + "摘" * 240 + '"}'
        )
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=response
        )

        result = await mock_ai_processor.process_content(
            content=sample_content_chinese,
            input_type="text",
            language="zh",
        )

        assert len(result["title"]) <= 40
        assert len(result["summary"]) <= 160

    async def test_generate_title_remains_available(
        self, mock_ai_processor, sample_content_chinese
    ):
        response = MagicMock()
        response.model = "gpt-3.5-turbo"
        response.choices = [MagicMock()]
        response.choices[0].message.content = "产品功能设计讨论"
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=response
        )

        title = await mock_ai_processor.generate_title(
            sample_content_chinese,
            max_length=20,
            language="zh",
        )

        assert title == "产品功能设计讨论"

    async def test_health_check(self, mock_ai_processor):
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "OK"
        mock_ai_processor.client.chat.completions.create = AsyncMock(
            return_value=response
        )
        assert await mock_ai_processor.health_check() is True

    def test_custom_provider_configuration(self):
        processor = AIProcessor(
            api_key="test-key",
            provider=LLMProvider.CUSTOM,
            base_url="https://custom-api.example.com",
            model="custom-model",
        )
        assert processor.provider == LLMProvider.CUSTOM
        assert processor.model == "custom-model"
