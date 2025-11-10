#!/usr/bin/env python3
"""Test AI Processor connectivity"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.ai_processor import get_ai_processor


async def test_ai_processor():
    """Test AI processor connectivity"""
    print("\n" + "=" * 60)
    print("Testing AI Processor Connectivity...")
    print("=" * 60)

    try:
        # Get AI processor instance
        processor = get_ai_processor()
        print(f"[OK] AI Processor initialized")
        print(f"  Provider: {processor.provider}")
        print(f"  Model: {processor.model}")
        print(f"  Base URL: {processor.client.base_url if hasattr(processor.client, 'base_url') else 'N/A'}")

        # Test health check
        print("\n Testing connectivity...")
        is_healthy = await processor.health_check()

        if is_healthy:
            print("[OK] Health check passed - AI service is accessible")
        else:
            print("[FAIL] Health check failed - AI service is not accessible")
            return

        # Test content processing with a simple example
        print("\nTesting content processing...")
        test_content = "今天学习了如何使用 Python 进行数据分析，感觉很有收获。"

        result = await processor.process_content(
            content=test_content,
            input_type="text",
            language="zh"
        )

        print("[OK] Content processing succeeded!")
        print(f"  Categories: {result['categories']}")
        print(f"  Summary: {result['summary']}")
        print(f"  Sentiment: {result['sentiment']}")
        print(f"  Confidence: {result['confidence']:.2f}")

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_ai_processor())
