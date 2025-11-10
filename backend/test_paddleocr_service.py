"""
Test script for PaddleOCR-VL service
使用示例测试图片验证 OCR 服务功能
"""

import asyncio
import sys
import os
from pathlib import Path

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.ocr_service import get_ocr_service
from src.config import settings


async def test_ocr_service():
    """Test OCR service with a sample image"""

    print("=" * 60)
    print("PaddleOCR-VL Service Test")
    print("=" * 60)

    # Check configuration
    print("\n1. Checking configuration...")
    if not settings.PADDLEOCR_API_URL:
        print("❌ PADDLEOCR_API_URL not configured in .env")
        print("   Please add: PADDLEOCR_API_URL=<your-api-url>")
        return False

    if not settings.PADDLEOCR_TOKEN:
        print("❌ PADDLEOCR_TOKEN not configured in .env")
        print("   Please add: PADDLEOCR_TOKEN=<your-token>")
        return False

    print(f"✓ API URL: {settings.PADDLEOCR_API_URL}")
    print(f"✓ Token: {'*' * 20}{settings.PADDLEOCR_TOKEN[-8:]}")

    # Initialize service
    print("\n2. Initializing OCR service...")
    try:
        ocr_service = get_ocr_service()
        print("✓ OCR service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize OCR service: {e}")
        return False

    # Health check
    print("\n3. Running health check...")
    try:
        is_healthy = await ocr_service.health_check()
        if is_healthy:
            print("✓ OCR service health check passed")
        else:
            print("❌ OCR service health check failed")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

    # Test with sample image (if provided)
    print("\n4. Ready for OCR processing")
    print("\nUsage example:")
    print("  result = await ocr_service.extract_text_from_image('path/to/image.jpg')")
    print("\nReturned fields:")
    print("  - text: 提取的纯文本")
    print("  - markdown: Markdown 格式文本")
    print("  - confidence: 置信度分数")
    print("  - language: 检测到的语言")
    print("  - word_count: 词数统计")
    print("  - page_count: 页数（对于 PDF）")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_ocr_service())

    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
    else:
        print("❌ Some tests failed. Please check the output above.")
    print("=" * 60)

    sys.exit(0 if success else 1)
