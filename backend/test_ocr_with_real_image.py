"""
Test OCR with a real generated image
"""

import asyncio
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image, ImageDraw, ImageFont
from src.services.ocr_service import get_ocr_service
from src.config import settings


async def test_ocr_with_generated_image():
    """Test OCR with a generated test image"""

    print("=" * 60)
    print("PaddleOCR Service Test (Real Image)")
    print("=" * 60)

    # Check configuration
    print("\n1. Checking configuration...")
    if not settings.PADDLEOCR_API_URL or not settings.PADDLEOCR_TOKEN:
        print("❌ PaddleOCR not configured")
        return False

    print(f"✓ API URL: {settings.PADDLEOCR_API_URL}")
    print(f"✓ Token: {'*' * 20}{settings.PADDLEOCR_TOKEN[-8:]}")

    # Create a test image with text
    print("\n2. Creating test image with text...")
    try:
        # Create a white image with black text
        img = Image.new('RGB', (800, 200), color='white')
        draw = ImageDraw.Draw(img)

        # Try to use a system font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 40)  # Microsoft YaHei
            except:
                font = ImageFont.load_default()

        # Draw text
        text = "Hello World 你好世界"
        draw.text((50, 80), text, fill='black', font=font)

        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        print(f"✓ Created image: 800x200px")
        print(f"✓ Text content: {text}")

        # Also save to file for debugging
        test_img_path = Path(__file__).parent / "test_image.png"
        img.save(test_img_path)
        print(f"✓ Saved to: {test_img_path}")

    except Exception as e:
        print(f"❌ Failed to create image: {e}")
        return False

    # Initialize service
    print("\n3. Initializing OCR service...")
    try:
        ocr_service = get_ocr_service()
        print("✓ OCR service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False

    # Test OCR
    print("\n4. Running OCR on test image...")
    try:
        result = await ocr_service.extract_text_from_bytes(
            image_bytes=img_bytes.getvalue(),
            file_type=1
        )

        print(f"\n✓ OCR completed successfully!")
        print(f"\nResults:")
        print(f"  Text: {result.get('text', '')[:200]}")
        print(f"  Language: {result.get('language')}")
        print(f"  Word count: {result.get('word_count')}")
        print(f"  Confidence: {result.get('confidence'):.2f}")

        if result.get('markdown'):
            print(f"\n  Markdown preview:")
            print(f"  {result['markdown'][:200]}")

        return True

    except Exception as e:
        print(f"\n❌ OCR failed: {type(e).__name__}")
        print(f"   Message: {str(e)}")

        # Show more details for debugging
        import traceback
        print(f"\n   Traceback:")
        traceback.print_exc()

        return False


if __name__ == "__main__":
    success = asyncio.run(test_ocr_with_generated_image())

    print("\n" + "=" * 60)
    if success:
        print("✓ Test passed - OCR is working correctly!")
    else:
        print("❌ Test failed - see details above")
    print("=" * 60)

    sys.exit(0 if success else 1)
