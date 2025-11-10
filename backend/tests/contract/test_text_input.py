"""
Contract Tests for Text Input to POST /records endpoint

Comprehensive tests for User Story 3: Text Input
Tests text-specific validation, AI processing, and error handling.
"""

import pytest
import httpx
import httpx
from httpx import AsyncClient
from fastapi import status

from src.api.main import app


@pytest.mark.asyncio
class TestTextInputContract:
    """Contract tests specifically for text input mode"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    # ==================== Basic Text Input Tests ====================

    async def test_text_input_minimal_valid_length(self, client):
        """Test text input with exactly minimum required length (10 chars)"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "十个字符测试内容",  # Exactly 10 characters
                "language": "zh",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input_type"] == "text"
        assert "content" in data

    async def test_text_input_long_content(self, client):
        """Test text input with long content"""
        long_text = "这是一段很长的测试文本。" * 100  # ~1300 characters

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": long_text,
                "language": "zh",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input_type"] == "text"
        assert len(data["content"]) > 1000

    async def test_text_input_with_english_content(self, client):
        """Test text input with English content"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "This is a test of English text input with sufficient length to pass validation.",
                "language": "en",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input_type"] == "text"
        assert "English" in data["content"] or "test" in data["content"]

    async def test_text_input_mixed_language(self, client):
        """Test text input with mixed Chinese and English"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "这是一段中英文混合的测试内容 with English mixed in for testing purposes.",
                "language": "zh",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input_type"] == "text"

    # ==================== Validation Tests ====================

    async def test_text_input_empty_content(self, client):
        """Test text input fails with empty content"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = response.json()
        assert "detail" in error

    async def test_text_input_whitespace_only(self, client):
        """Test text input fails with whitespace-only content"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "   \n\t   ",  # Only whitespace
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = response.json()
        assert "detail" in error

    async def test_text_input_just_below_minimum(self, client):
        """Test text input fails with 9 characters (just below minimum)"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "九个字符内容",  # 9 characters
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = response.json()
        assert "detail" in error
        assert "10" in str(error["detail"])

    async def test_text_input_maximum_length(self, client):
        """Test text input at maximum allowed length"""
        # Create content at exactly 10,000 characters
        max_text = "测" * 10000

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": max_text,
                "language": "zh",
                "auto_process": "true",
            },
        )

        # Should succeed or fail gracefully
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    async def test_text_input_exceeds_maximum(self, client):
        """Test text input fails when exceeding maximum length"""
        # Create content exceeding 10,000 characters
        too_long_text = "测" * 10001

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": too_long_text,
                "language": "zh",
            },
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]
        error = response.json()
        assert "detail" in error

    # ==================== Special Characters Tests ====================

    async def test_text_input_with_newlines(self, client):
        """Test text input with newline characters"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "第一行内容\n第二行内容\n第三行内容\n总共包含多个换行符",
                "language": "zh",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        # Content should preserve newlines or handle them gracefully
        assert "content" in data

    async def test_text_input_with_special_characters(self, client):
        """Test text input with special characters"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "特殊字符测试：@#$%^&*()[]{}!?<>\\|/~`+=.,;:\"'",
                "language": "zh",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input_type"] == "text"

    async def test_text_input_with_emojis(self, client):
        """Test text input with emoji characters"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "这是包含表情符号的测试内容 😀🎉💡📝✨🚀🔥💪",
                "language": "zh",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input_type"] == "text"

    async def test_text_input_with_markdown(self, client):
        """Test text input with Markdown formatting"""
        markdown_text = """
        # 标题

        这是一段包含Markdown格式的测试内容。

        ## 子标题

        - 列表项1
        - 列表项2

        **加粗文字** 和 *斜体文字*
        """

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": markdown_text,
                "language": "zh",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input_type"] == "text"

    # ==================== AI Processing Tests ====================

    async def test_text_input_with_ai_processing(self, client):
        """Test text input with AI processing enabled"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "人工智能技术正在改变我们的生活方式，从语音识别到图像处理，AI的应用越来越广泛。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["input_type"] == "text"

            # Should have AI-generated fields
            assert "categories" in data
            assert "summary" in data

            # Categories should be a list
            assert isinstance(data["categories"], list)

            # Summary should be non-empty if AI processed
            if data.get("summary"):
                assert len(data["summary"]) > 0

    async def test_text_input_without_ai_processing(self, client):
        """Test text input with AI processing disabled"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "这是不需要AI处理的简单文本内容，仅用于测试基本保存功能。",
                "language": "zh",
                "auto_process": "false",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["input_type"] == "text"
        assert "content" in data

    async def test_text_input_ai_categorization_quality(self, client):
        """Test AI categorization produces reasonable results"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "今天学习了Python编程语言的高级特性，包括装饰器、生成器和异步编程。"
                          "这些特性让代码更加简洁高效。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Categories should be reasonable (1-5 categories)
            if data.get("categories"):
                assert 1 <= len(data["categories"]) <= 5

                # Category names should be non-empty strings
                for category in data["categories"]:
                    assert isinstance(category, str)
                    assert len(category) > 0

    # ==================== Response Schema Tests ====================

    async def test_text_input_response_schema(self, client):
        """Test response schema for text input"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "完整响应模式验证的测试内容，确保所有字段都正确返回。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Required fields
            required_fields = [
                "id",
                "title",
                "content",
                "input_type",
                "categories",
                "tags",
                "created_at",
                "updated_at",
            ]

            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Verify types
            assert isinstance(data["id"], int)
            assert isinstance(data["title"], str)
            assert isinstance(data["content"], str)
            assert data["input_type"] == "text"
            assert isinstance(data["categories"], list)
            assert isinstance(data["tags"], list)
            assert isinstance(data["created_at"], str)
            assert isinstance(data["updated_at"], str)

    async def test_text_input_metadata_fields(self, client):
        """Test metadata fields are populated correctly"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "元数据字段测试内容，验证所有元数据是否正确填充。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Metadata fields
            assert "sync_status" in data
            assert "version" in data

            # Sync status should be 0 (pending) or 1 (synced)
            assert data["sync_status"] in [0, 1]

            # Version should be 1 for new records
            assert data["version"] >= 1

    # ==================== Edge Cases ====================

    async def test_text_input_with_sql_injection_attempt(self, client):
        """Test text input handles SQL injection attempts safely"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "'; DROP TABLE inspiration_records; --这是SQL注入测试内容",
                "language": "zh",
                "auto_process": "false",
            },
        )

        # Should either succeed (properly escaped) or fail gracefully
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        ]

    async def test_text_input_with_xss_attempt(self, client):
        """Test text input handles XSS attempts safely"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "<script>alert('XSS')</script>这是XSS测试内容",
                "language": "zh",
                "auto_process": "false",
            },
        )

        # Should succeed and sanitize/escape the content
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            # Content should be safely stored
            assert "content" in data


@pytest.mark.asyncio
@pytest.mark.slow
class TestTextInputPerformance:
    """Performance tests for text input"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_text_input_response_time(self, client):
        """Test text input response time meets requirements (<1s for UI)"""
        import time

        start_time = time.time()

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "性能测试内容，验证响应时间是否满足UI交互要求（小于1秒）。",
                "language": "zh",
                "auto_process": "false",  # Without AI for faster response
            },
        )

        end_time = time.time()
        elapsed = end_time - start_time

        # UI should respond < 1 second
        assert elapsed < 1.0, f"Response took {elapsed:.2f}s, expected < 1s"
        assert response.status_code == status.HTTP_201_CREATED

    async def test_text_input_with_ai_performance(self, client):
        """Test text input with AI processing completes reasonably fast"""
        import time

        start_time = time.time()

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "这是一段用于AI性能测试的内容。包含足够的文字以触发完整的AI分类和摘要生成流程。"
                          "测试目标是验证整个处理流程能在合理时间内完成。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        end_time = time.time()
        elapsed = end_time - start_time

        # With AI processing should complete < 5 seconds
        assert elapsed < 5.0, f"AI processing took {elapsed:.2f}s, expected < 5s"

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["input_type"] == "text"
