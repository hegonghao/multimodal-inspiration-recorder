"""
Detailed OCR API diagnostics
"""

import asyncio
import sys
import base64
from pathlib import Path

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")

sys.path.insert(0, str(Path(__file__).parent))

import httpx
from src.config import settings


async def test_api_direct():
    """Test PaddleOCR API directly with detailed error info"""

    print("=" * 60)
    print("PaddleOCR API Detailed Diagnostics")
    print("=" * 60)

    # Check configuration
    api_url = settings.PADDLEOCR_API_URL
    token = settings.PADDLEOCR_TOKEN

    if not api_url or not token:
        print("\n❌ API credentials not configured")
        return False

    print(f"\nAPI URL: {api_url}")
    print(f"Token: {'*' * 20}{token[-8:]}")

    # Create a simple test image (white 100x100 PNG with text area)
    # Using a minimal but valid PNG
    print("\n1. Creating test image...")

    # Create a simple 10x10 white PNG
    test_image = bytearray([
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

    file_data = base64.b64encode(bytes(test_image)).decode("ascii")
    print(f"   Image size: {len(test_image)} bytes")
    print(f"   Base64 size: {len(file_data)} chars")

    # Prepare request
    print("\n2. Preparing API request...")
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "file": file_data,
        "fileType": 1,  # Image
        "useChartRecognition": False,
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
    }

    print(f"   Payload size: {len(str(payload))} chars")

    # Make request
    print("\n3. Calling API...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"   Sending POST to: {api_url}")

            response = await client.post(
                api_url,
                json=payload,
                headers=headers
            )

            print(f"   Status code: {response.status_code}")
            print(f"   Response headers: {dict(response.headers)}")

            # Try to parse response
            try:
                result = response.json()
                print(f"\n4. Response body:")
                import json
                print(json.dumps(result, indent=2, ensure_ascii=False))

                # Check for errors
                error_code = result.get("errorCode", 0)
                if error_code != 0:
                    error_msg = result.get("errorMsg", "Unknown error")
                    print(f"\n❌ API returned error:")
                    print(f"   Code: {error_code}")
                    print(f"   Message: {error_msg}")
                    return False
                else:
                    print("\n✓ API call successful!")

                    # Check results
                    api_result = result.get("result", {})
                    layout_results = api_result.get("layoutParsingResults", [])
                    print(f"   Pages processed: {len(layout_results)}")

                    if layout_results:
                        first_page = layout_results[0]
                        markdown = first_page.get("markdown", {})
                        text = markdown.get("text", "")
                        print(f"   Extracted text length: {len(text)} chars")
                        if text:
                            print(f"   Text preview: {text[:100]}...")

                    return True

            except Exception as e:
                print(f"\n❌ Failed to parse JSON response:")
                print(f"   Error: {e}")
                print(f"   Raw response: {response.text[:500]}")
                return False

    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP error occurred:")
        print(f"   Status: {e.response.status_code}")
        print(f"   Response: {e.response.text[:500]}")
        return False

    except httpx.TimeoutException:
        print(f"\n❌ Request timed out (>60s)")
        return False

    except Exception as e:
        print(f"\n❌ Unexpected error:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_api_direct())

    print("\n" + "=" * 60)
    if success:
        print("✓ Diagnostics completed - API is working!")
    else:
        print("❌ Diagnostics found issues - see details above")
    print("=" * 60)

    sys.exit(0 if success else 1)
