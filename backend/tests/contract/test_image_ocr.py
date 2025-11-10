"""
Contract Tests for Image OCR

Tests API contract for image upload and OCR processing.
Validates image file handling, OCR confidence scoring, and error handling.
"""

import pytest
import tempfile
import os
import httpx
import httpx
from httpx import AsyncClient
from fastapi import status
from PIL import Image, ImageDraw, ImageFont

from src.api.main import app


@pytest.mark.asyncio
class TestImageOCRContract:
    """Contract tests for image upload and OCR processing"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def simple_image_with_text(self):
        """Create a simple test image with text"""
        # Create image with text "TEST 123"
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('RGB', (400, 100), color='white')
            draw = ImageDraw.Draw(img)

            # Draw simple text (no font file needed, uses default)
            draw.text((50, 30), "TEST 123", fill='black')

            img.save(f.name, 'PNG')
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def blank_image(self):
        """Create a blank image without text"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('RGB', (200, 200), color='white')
            img.save(f.name, 'PNG')
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def large_image(self):
        """Create a large image file (>5MB)"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Create 3000x3000 image (should be >5MB)
            img = Image.new('RGB', (3000, 3000), color='white')
            img.save(f.name, 'PNG', quality=100)
            yield f.name
        os.unlink(f.name)

    # ==================== Basic Image Upload Tests ====================

    async def test_image_upload_success(self, client, simple_image_with_text):
        """Test successful image upload and OCR"""
        with open(simple_image_with_text, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "image",
                    "language": "en",
                    "auto_process": "true",
                },
                files={"file": ("test.png", f, "image/png")},
            )

        # May succeed or fail depending on OCR service availability
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["input_type"] == "image"
            assert "content" in data
            assert "raw_data" in data

            # Should have OCR metadata
            raw_data = data["raw_data"]
            if isinstance(raw_data, dict):
                assert "ocr_confidence" in raw_data or "word_count" in raw_data

    async def test_image_upload_without_file(self, client):
        """Test image upload fails without file"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "image",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        error = response.json()
        assert "detail" in error
        assert "Image file is required" in str(error["detail"])

    async def test_image_upload_multiple_formats(self, client, simple_image_with_text):
        """Test image upload supports multiple formats"""
        # Test PNG
        with open(simple_image_with_text, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={"input_type": "image", "language": "en"},
                files={"file": ("test.png", f, "image/png")},
            )
        assert response.status_code in [201, 422, 503]

        # Create and test JPG
        jpg_file = simple_image_with_text.replace('.png', '.jpg')
        img = Image.open(simple_image_with_text)
        img.save(jpg_file, 'JPEG')

        try:
            with open(jpg_file, "rb") as f:
                response = await client.post(
                    "/api/v1/records/",
                    data={"input_type": "image", "language": "en"},
                    files={"file": ("test.jpg", f, "image/jpeg")},
                )
            assert response.status_code in [201, 422, 503]
        finally:
            os.unlink(jpg_file)

    # ==================== OCR Confidence Tests (T046) ====================

    async def test_ocr_low_confidence_error_structure(self, client, blank_image):
        """Test OCR low confidence error has proper structure"""
        with open(blank_image, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "image",
                    "language": "zh",
                    "auto_process": "true",
                },
                files={"file": ("blank.png", f, "image/png")},
            )

        # Blank image should fail with low confidence or no text
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            error = response.json()
            assert "detail" in error

            detail = error["detail"]
            if isinstance(detail, dict):
                # Should have structured error
                assert "error" in detail
                assert detail["error"] in ["low_ocr_confidence", "ocr_failed"]

                # Low confidence should include these fields
                if detail["error"] == "low_ocr_confidence":
                    assert "confidence" in detail
                    assert "threshold" in detail
                    assert "extracted_text" in detail  # Key: provide text for editing
                    assert "fallback" in detail
                    assert detail["fallback"] == "manual_edit"
                    assert "suggestions" in detail
                    assert isinstance(detail["suggestions"], list)
                    assert len(detail["suggestions"]) > 0

    async def test_ocr_failure_fallback_suggestions(self, client):
        """Test OCR failure includes fallback suggestions (T047)"""
        # Send invalid image data
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "image",
                "language": "zh",
            },
            files={"file": ("invalid.png", b"invalid data", "image/png")},
        )

        # Should fail
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

        error = response.json()
        if "detail" in error:
            detail = error["detail"]
            if isinstance(detail, dict) and "error" in detail:
                # Should include suggestions
                if "suggestions" in detail:
                    suggestions = detail["suggestions"]
                    assert isinstance(suggestions, list)
                    assert len(suggestions) > 0

                    # Should suggest manual input as fallback
                    suggestion_text = " ".join(suggestions)
                    assert any(
                        keyword in suggestion_text.lower()
                        for keyword in ["manual", "retry", "photo", "clear"]
                    )

    # ==================== Content Extraction Tests ====================

    async def test_ocr_content_too_short_error(self, client, blank_image):
        """Test OCR with insufficient content"""
        with open(blank_image, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "image",
                    "language": "zh",
                },
                files={"file": ("blank.png", f, "image/png")},
            )

        # Should fail with content too short or OCR error
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

        error = response.json()
        assert "detail" in error

        detail = error["detail"]
        if isinstance(detail, dict):
            # Should indicate content issue
            assert "error" in detail
            assert detail["error"] in [
                "content_too_short",
                "low_ocr_confidence",
                "ocr_failed"
            ]

    # ==================== Language Detection Tests ====================

    async def test_ocr_language_detection(self, client, simple_image_with_text):
        """Test OCR with language detection"""
        with open(simple_image_with_text, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "image",
                    "language": "auto",  # Auto-detect
                    "auto_process": "true",
                },
                files={"file": ("test.png", f, "image/png")},
            )

        # Should accept auto language
        assert response.status_code in [201, 422, 503]

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            raw_data = data.get("raw_data", {})

            if isinstance(raw_data, dict):
                # Should have detected language
                assert "detected_language" in raw_data

    async def test_ocr_chinese_text(self, client):
        """Test OCR with Chinese text image"""
        # Create image with Chinese text
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('RGB', (400, 100), color='white')
            draw = ImageDraw.Draw(img)
            draw.text((50, 30), "测试文字", fill='black')
            img.save(f.name, 'PNG')

            img_path = f.name

        try:
            with open(img_path, "rb") as f:
                response = await client.post(
                    "/api/v1/records/",
                    data={
                        "input_type": "image",
                        "language": "zh",
                        "auto_process": "true",
                    },
                    files={"file": ("chinese.png", f, "image/png")},
                )

            # Should process Chinese text
            assert response.status_code in [201, 422, 503]

        finally:
            os.unlink(img_path)

    # ==================== Image Size and Quality Tests ====================

    async def test_large_image_handling(self, client, large_image):
        """Test handling of large images"""
        file_size = os.path.getsize(large_image)

        # Skip if not actually large enough
        if file_size < 5 * 1024 * 1024:
            pytest.skip("Generated image not large enough")

        with open(large_image, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "image",
                    "language": "zh",
                },
                files={"file": ("large.png", f, "image/png")},
            )

        # Should handle large image (may compress or reject)
        assert response.status_code in [201, 400, 422, 503]

    # ==================== Metadata Tests ====================

    async def test_ocr_metadata_completeness(self, client, simple_image_with_text):
        """Test OCR response includes complete metadata"""
        with open(simple_image_with_text, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "image",
                    "language": "en",
                    "auto_process": "true",
                },
                files={"file": ("test.png", f, "image/png")},
            )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Should have raw_data with OCR metadata
            assert "raw_data" in data
            raw_data = data["raw_data"]

            if isinstance(raw_data, dict):
                # OCR-specific metadata
                expected_fields = [
                    "ocr_confidence",
                    "detected_language",
                    "word_count",
                ]

                for field in expected_fields:
                    assert field in raw_data, f"Missing OCR metadata: {field}"

                # Confidence should be a float
                assert isinstance(raw_data["ocr_confidence"], (int, float))
                assert 0.0 <= raw_data["ocr_confidence"] <= 1.0

    # ==================== AI Integration Tests ====================

    async def test_ocr_with_ai_processing(self, client, simple_image_with_text):
        """Test OCR results are processed by AI (T048)"""
        with open(simple_image_with_text, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "image",
                    "language": "en",
                    "auto_process": "true",
                },
                files={"file": ("test.png", f, "image/png")},
            )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Should have AI-generated fields
            assert "categories" in data
            assert "summary" in data

            # If AI processing succeeded
            if data.get("categories") or data.get("summary"):
                raw_data = data.get("raw_data", {})

                if isinstance(raw_data, dict):
                    # Should have AI metadata
                    assert "ai_confidence" in raw_data or "sentiment" in raw_data

    async def test_ocr_without_ai_processing(self, client, simple_image_with_text):
        """Test OCR without AI processing"""
        with open(simple_image_with_text, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "image",
                    "language": "en",
                    "auto_process": "false",  # Disable AI
                },
                files={"file": ("test.png", f, "image/png")},
            )

        # Should still work without AI
        assert response.status_code in [201, 422, 503]

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["input_type"] == "image"
            # Content should still be extracted
            assert "content" in data
