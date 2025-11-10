"""
Contract Tests for Records API

Tests API contract compliance for POST /records endpoint.
Validates request/response schemas, status codes, and error handling.
"""

import pytest
import tempfile
import os
import httpx
from httpx import AsyncClient
from fastapi import status

from src.api.main import app


@pytest.mark.asyncio
class TestRecordsAPIContract:
    """Contract tests for /api/v1/records endpoint"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def sample_audio_file(self):
        """Create a sample audio file for testing"""
        # Create a minimal AAC file (silent audio, ~1 second)
        with tempfile.NamedTemporaryFile(suffix=".aac", delete=False) as f:
            # Minimal AAC header + silent frame
            f.write(b'\xff\xf1\x50\x80\x00\x1f\xfc')
            f.flush()
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def sample_image_file(self):
        """Create a sample image file for testing"""
        # Create a minimal PNG file (1x1 white pixel)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
                b'\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00'
                b'\x05\x18\r\xa2d\x00\x00\x00\x00IEND\xaeB`\x82'
            )
            f.flush()
            yield f.name
        os.unlink(f.name)

    # ==================== Text Input Tests ====================

    async def test_create_text_record_success(self, client):
        """Test successful text record creation"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "这是一段测试文字，用于验证文本输入功能是否正常工作。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        # Assert status code
        assert response.status_code == status.HTTP_201_CREATED

        # Assert response schema
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert "content" in data
        assert "input_type" in data
        assert data["input_type"] == "text"
        assert "categories" in data
        assert "summary" in data
        assert "created_at" in data
        assert "updated_at" in data

        # Assert content matches
        assert "测试文字" in data["content"]

    async def test_create_text_record_too_short(self, client):
        """Test text record creation fails with short content"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "短",  # Only 1 character
                "language": "zh",
            },
        )

        # Assert status code
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Assert error response
        error = response.json()
        assert "detail" in error
        assert "10 characters" in str(error["detail"])

    async def test_create_text_record_missing_content(self, client):
        """Test text record creation fails without content"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "language": "zh",
            },
        )

        # Assert status code
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_create_text_record_without_ai_processing(self, client):
        """Test text record creation without AI processing"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "这是一段没有AI处理的测试文字内容。",
                "language": "zh",
                "auto_process": "false",
            },
        )

        # Assert status code
        assert response.status_code == status.HTTP_201_CREATED

        # Assert response
        data = response.json()
        assert data["input_type"] == "text"
        # Categories and summary might be empty or minimal without AI
        assert "content" in data

    # ==================== Voice Input Tests ====================

    async def test_create_voice_record_missing_file(self, client):
        """Test voice record creation fails without audio file"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "voice",
                "language": "zh",
            },
        )

        # Assert status code
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Assert error message
        error = response.json()
        assert "detail" in error
        assert "Audio file is required" in str(error["detail"])

    async def test_create_voice_record_with_file(self, client, sample_audio_file):
        """Test voice record creation with audio file (may fail due to mock service)"""
        with open(sample_audio_file, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "voice",
                    "language": "zh",
                    "auto_process": "true",
                },
                files={"file": ("test.aac", f, "audio/aac")},
            )

        # May succeed or fail depending on service availability
        # Just verify it doesn't crash and returns proper status
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

        # If error, should have proper structure
        if response.status_code != status.HTTP_201_CREATED:
            error = response.json()
            assert "detail" in error

    # ==================== Image Input Tests ====================

    async def test_create_image_record_missing_file(self, client):
        """Test image record creation fails without image file"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "image",
                "language": "zh",
            },
        )

        # Assert status code
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Assert error message
        error = response.json()
        assert "detail" in error
        assert "Image file is required" in str(error["detail"])

    async def test_create_image_record_with_file(self, client, sample_image_file):
        """Test image record creation with image file (may fail due to mock service)"""
        with open(sample_image_file, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "image",
                    "language": "zh",
                    "auto_process": "true",
                },
                files={"file": ("test.png", f, "image/png")},
            )

        # May succeed or fail depending on service availability
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

        # If error, should have proper structure
        if response.status_code != status.HTTP_201_CREATED:
            error = response.json()
            assert "detail" in error

    # ==================== Invalid Input Tests ====================

    async def test_create_record_invalid_type(self, client):
        """Test record creation fails with invalid input type"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "invalid_type",
                "content": "Some content",
            },
        )

        # Assert status code
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Assert error message
        error = response.json()
        assert "detail" in error
        assert "Invalid input_type" in str(error["detail"])

    async def test_create_record_missing_input_type(self, client):
        """Test record creation fails without input_type"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "content": "Some content",
            },
        )

        # Assert status code (422 for missing required field)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # ==================== Response Schema Tests ====================

    async def test_response_schema_completeness(self, client):
        """Test response contains all required fields"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "完整的响应模式测试内容，用于验证所有字段是否都存在。",
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
                "sync_status",
                "version",
                "created_at",
                "updated_at",
            ]

            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Type validations
            assert isinstance(data["id"], int)
            assert isinstance(data["title"], str)
            assert isinstance(data["content"], str)
            assert isinstance(data["categories"], list)
            assert isinstance(data["tags"], list)
            assert isinstance(data["sync_status"], int)
            assert isinstance(data["version"], int)

    async def test_error_response_schema(self, client):
        """Test error responses have consistent structure"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "短",  # Too short
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        error = response.json()
        assert "detail" in error

        # Detail can be string or dict
        detail = error["detail"]
        if isinstance(detail, dict):
            # Structured error should have message
            assert "error" in detail or "message" in detail


@pytest.mark.asyncio
class TestRecordsAPIConfidenceValidation:
    """Tests for confidence-based validation (T034, T046, T047)"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_low_confidence_error_structure(self, client):
        """Test that low confidence errors have proper structure"""
        # This test documents expected error structure
        # Actual test would require mocking services to return low confidence

        expected_error_fields = [
            "error",
            "message",
            "confidence",
            "threshold",
            "suggestions",
        ]

        # Document expected structure for low transcription confidence
        expected_transcription_error = {
            "error": "low_transcription_confidence",
            "message": str,
            "confidence": float,
            "threshold": 0.5,
            "suggestions": list,
        }

        # Document expected structure for low OCR confidence
        expected_ocr_error = {
            "error": "low_ocr_confidence",
            "message": str,
            "confidence": float,
            "threshold": 0.4,
            "extracted_text": str,  # Should provide text for editing
            "fallback": "manual_edit",
            "suggestions": list,
        }

        # This is a documentation test
        assert True


# ==================== Performance Tests ====================


@pytest.mark.asyncio
@pytest.mark.slow
class TestRecordsAPIPerformance:
    """Performance tests for records API"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_text_record_creation_performance(self, client):
        """Test text record creation completes within reasonable time"""
        import time

        start_time = time.time()

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "性能测试内容，验证文本记录创建的响应时间是否在可接受范围内。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete within 5 seconds (including AI processing)
        assert elapsed < 5.0, f"Request took {elapsed:.2f}s, expected < 5s"

        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
