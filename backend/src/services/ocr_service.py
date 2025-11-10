"""
OCR (Optical Character Recognition) Service

Provides text recognition from images and PDFs using PaddleOCR-VL API
with layout parsing and markdown output support.
"""

import asyncio
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path
import mimetypes

import httpx

from src.utils.logger import get_logger
from src.core.exceptions import ExternalServiceException

logger = get_logger(__name__)


class OCRService:
    """
    Service for extracting text from images and PDFs using PaddleOCR-VL API

    Features:
    - High accuracy text recognition for Chinese/English
    - Support for both images (PNG, JPG, WEBP) and PDF files
    - Layout parsing and analysis
    - Markdown-formatted output
    - Chart recognition (optional)
    - Document orientation and unwarping correction (optional)
    """

    def __init__(self, api_url: str, token: str):
        """
        Initialize OCR service

        Args:
            api_url: PaddleOCR-VL API endpoint URL
            token: API authentication token
        """
        if not api_url or not token:
            raise ValueError("PaddleOCR API URL and token are required")

        self.api_url = api_url.rstrip("/")
        self.token = token
        self.timeout = 60.0  # OCR can be slow for large documents

    async def extract_text_from_image(
        self,
        image_file_path: str,
        language_hints: Optional[List[str]] = None,
        use_chart_recognition: bool = False,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract text from image file

        Args:
            image_file_path: Path to image file (PNG, JPG, WEBP, etc.)
            language_hints: Unused, kept for API compatibility
            use_chart_recognition: Enable chart recognition
            use_orientation_classify: Enable document orientation correction
            use_unwarping: Enable document unwarping (dewarp)

        Returns:
            Dict containing OCR results:
            {
                "text": "extracted text content",
                "confidence": 0.95,
                "language": "zh",
                "word_count": 120,
                "blocks": [],
                "markdown": "# markdown formatted text"
            }

        Raises:
            ExternalServiceException: If OCR fails
        """
        try:
            logger.info(f"Starting OCR for: {image_file_path}")

            # Verify file exists
            image_path = Path(image_file_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image file not found: {image_file_path}")

            # Read and encode image
            with open(image_file_path, "rb") as f:
                file_bytes = f.read()

            # Determine file type
            mime_type, _ = mimetypes.guess_type(image_file_path)
            file_type = self._get_file_type(mime_type, image_path.suffix)

            # Call OCR API
            result = await self._call_ocr_api(
                file_bytes=file_bytes,
                file_type=file_type,
                use_chart_recognition=use_chart_recognition,
                use_orientation_classify=use_orientation_classify,
                use_unwarping=use_unwarping,
            )

            logger.info(
                f"OCR completed: {result['word_count']} words, "
                f"language: {result['language']}"
            )

            return result

        except FileNotFoundError as e:
            logger.error(f"Image file not found: {e}")
            raise

        except Exception as e:
            logger.error(f"OCR failed: {type(e).__name__}: {e}")
            raise ExternalServiceException(
                f"Failed to extract text from image: {str(e)}",
                error_code="OCR_FAILED"
            )

    async def extract_text_from_bytes(
        self,
        image_bytes: bytes,
        language_hints: Optional[List[str]] = None,
        file_type: int = 1,  # 1 = image, 0 = PDF
        use_chart_recognition: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract text from image bytes

        Args:
            image_bytes: Image or PDF file content as bytes
            language_hints: Unused, kept for API compatibility
            file_type: 0 for PDF, 1 for image
            use_chart_recognition: Enable chart recognition

        Returns:
            OCR result dict
        """
        try:
            logger.info(f"Starting OCR from bytes (type={file_type})")

            result = await self._call_ocr_api(
                file_bytes=image_bytes,
                file_type=file_type,
                use_chart_recognition=use_chart_recognition,
            )

            logger.info(f"OCR completed: {result['word_count']} words")
            return result

        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise ExternalServiceException(
                f"Failed to extract text from bytes: {str(e)}",
                error_code="OCR_FAILED"
            )

    async def _call_ocr_api(
        self,
        file_bytes: bytes,
        file_type: int,
        use_chart_recognition: bool = False,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
    ) -> Dict[str, Any]:
        """
        Call PaddleOCR-VL API

        Args:
            file_bytes: File content
            file_type: 0 for PDF, 1 for image
            use_chart_recognition: Enable chart recognition
            use_orientation_classify: Enable orientation correction
            use_unwarping: Enable document unwarping

        Returns:
            Processed OCR result
        """
        # Encode file to base64
        file_data = base64.b64encode(file_bytes).decode("ascii")

        # Prepare request
        headers = {
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json"
        }

        payload = {
            "file": file_data,
            "fileType": file_type,
            "useChartRecognition": use_chart_recognition,
            "useDocOrientationClassify": use_orientation_classify,
            "useDocUnwarping": use_unwarping,
        }

        # Make API request
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.api_url,
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            api_result = response.json()

        # Check for API errors
        if api_result.get("errorCode", 0) != 0:
            error_msg = api_result.get("errorMsg", "Unknown error")
            raise ExternalServiceException(
                f"PaddleOCR API error: {error_msg}",
                error_code="PADDLEOCR_API_ERROR"
            )

        # Extract results
        return self._parse_ocr_result(api_result)

    def _parse_ocr_result(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse PaddleOCR API result into standardized format

        Args:
            api_result: Raw API response

        Returns:
            Standardized OCR result
        """
        result = api_result.get("result", {})
        layout_results = result.get("layoutParsingResults", [])

        if not layout_results:
            logger.warning("No text detected in document")
            return {
                "text": "",
                "confidence": 0.0,
                "language": "unknown",
                "word_count": 0,
                "blocks": [],
                "markdown": "",
            }

        # Combine all pages (for multi-page PDFs)
        all_text = []
        all_markdown = []

        for page_result in layout_results:
            markdown_data = page_result.get("markdown", {})
            markdown_text = markdown_data.get("text", "")

            if markdown_text:
                all_text.append(markdown_text)
                all_markdown.append(markdown_text)

        # Combine results
        full_text = "\n\n".join(all_text)
        full_markdown = "\n\n".join(all_markdown)

        # Detect language
        detected_language = self._detect_language(full_text)

        # Calculate word count (approximate)
        word_count = len(full_text.split())

        # PaddleOCR doesn't provide confidence scores
        # Use a default high confidence since it's generally accurate
        confidence = 0.95 if full_text else 0.0

        return {
            "text": full_text,
            "confidence": confidence,
            "language": detected_language,
            "word_count": word_count,
            "blocks": [],  # PaddleOCR doesn't provide block-level details in this format
            "markdown": full_markdown,
            "page_count": len(layout_results),
        }

    def _get_file_type(self, mime_type: Optional[str], suffix: str) -> int:
        """
        Determine file type code for PaddleOCR API

        Args:
            mime_type: MIME type of file
            suffix: File extension

        Returns:
            0 for PDF, 1 for image
        """
        if mime_type == "application/pdf" or suffix.lower() == ".pdf":
            return 0
        return 1

    def _detect_language(self, text: str) -> str:
        """
        Detect primary language of text

        Args:
            text: Text to analyze

        Returns:
            Language code ('zh', 'en', 'ja', etc.)
        """
        if not text:
            return "unknown"

        # Simple heuristic based on character ranges
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        japanese_chars = sum(
            1 for c in text
            if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff'
        )
        korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
        total_chars = len(text)

        if total_chars == 0:
            return "unknown"

        # Chinese
        if chinese_chars / total_chars > 0.3:
            return "zh"
        # Japanese
        elif japanese_chars / total_chars > 0.3:
            return "ja"
        # Korean
        elif korean_chars / total_chars > 0.3:
            return "ko"
        # Default to English
        else:
            return "en"

    async def health_check(self) -> bool:
        """
        Check if PaddleOCR API is accessible

        Note: Uses a simple connectivity check. Small test images may return 500
        errors from the OCR service, but that still indicates the API is reachable.

        Returns:
            True if service is healthy (API is accessible), False otherwise
        """
        try:
            # Create a minimal test image (10x10 white PNG)
            test_image_bytes = bytearray([
                0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
                0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
                0x00, 0x00, 0x00, 0x0A, 0x00, 0x00, 0x00, 0x0A,  # 10x10 dimensions
                0x08, 0x02, 0x00, 0x00, 0x00, 0x02, 0x50, 0x58,
                0xEA, 0x00, 0x00, 0x00, 0x01, 0x73, 0x52, 0x47,
                0x42, 0x00, 0xAE, 0xCE, 0x1C, 0xE9, 0x00, 0x00,
                0x00, 0x17, 0x49, 0x44, 0x41, 0x54, 0x18, 0x57,  # IDAT chunk
                0x63, 0xF8, 0xFF, 0xFF, 0x3F, 0x03, 0x03, 0x00,
                0x00, 0x00, 0x00, 0x09, 0x00, 0x01, 0x2F, 0xD4,
                0xEF, 0x3F, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,
                0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82  # IEND chunk
            ])

            file_data = base64.b64encode(bytes(test_image_bytes)).decode("ascii")

            headers = {
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json"
            }

            payload = {
                "file": file_data,
                "fileType": 1,
            }

            # Make request - we only care if API is reachable
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )

                # Any response (even 500) means API is accessible
                # 401/403 would indicate auth issues
                # Connection errors would raise an exception
                if response.status_code in [401, 403]:
                    logger.error("PaddleOCR API authentication failed")
                    return False

                # 500 is acceptable for health check (API is reachable)
                logger.info(f"PaddleOCR API health check: status {response.status_code}")
                return True

        except httpx.ConnectError as e:
            logger.error(f"PaddleOCR API connection failed: {e}")
            return False
        except httpx.TimeoutException:
            logger.error("PaddleOCR API health check timed out")
            return False
        except Exception as e:
            logger.error(f"PaddleOCR API health check failed: {e}")
            return False


# Singleton instance
_ocr_service: Optional[OCRService] = None


def get_ocr_service(
    api_url: Optional[str] = None,
    token: Optional[str] = None
) -> OCRService:
    """
    Get or create OCR service instance

    Args:
        api_url: PaddleOCR API URL (required on first call if not in config)
        token: PaddleOCR API token (required on first call if not in config)

    Returns:
        OCRService instance
    """
    global _ocr_service

    if _ocr_service is None:
        # Try to get from config if not provided
        if api_url is None or token is None:
            from src.config import settings
            api_url = api_url or settings.PADDLEOCR_API_URL
            token = token or settings.PADDLEOCR_TOKEN

        if not api_url or not token:
            raise ValueError(
                "PaddleOCR API URL and token must be provided either as "
                "arguments or in configuration (PADDLEOCR_API_URL, PADDLEOCR_TOKEN)"
            )

        _ocr_service = OCRService(api_url=api_url, token=token)

    return _ocr_service
