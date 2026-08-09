"""Detailed PaddleOCR v6 diagnostic using the production service client."""

import asyncio
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src.services.ocr_service import get_ocr_service


async def main() -> bool:
    """Run a non-destructive OCR request against the configured service."""
    if not settings.PADDLEOCR_API_URL or not settings.PADDLEOCR_TOKEN:
        print("PADDLEOCR_API_URL and PADDLEOCR_TOKEN are not configured")
        return False

    print(f"API URL: {settings.PADDLEOCR_API_URL}")
    print(f"Token suffix: ...{settings.PADDLEOCR_TOKEN[-8:]}")
    service = get_ocr_service()

    image_path = Path(__file__).parent / "test_image.png"
    if not image_path.exists():
        print(f"Test image not found: {image_path}")
        return False

    result = await service.extract_text_from_image(str(image_path))
    print(
        json.dumps(
            {
                "text": result["text"],
                "confidence": result["confidence"],
                "language": result["language"],
                "word_count": result["word_count"],
                "page_count": result["page_count"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return bool(result["text"])


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
