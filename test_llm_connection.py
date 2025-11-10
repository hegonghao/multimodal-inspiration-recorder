#!/usr/bin/env python3
"""
Test LLM API Connection
测试 LLM API 连接性

Usage:
    python test_llm_connection.py
"""

import os
import sys
import asyncio
import httpx
from openai import AsyncOpenAI


async def test_basic_connectivity():
    """Test basic network connectivity to API endpoint"""
    print("=" * 60)
    print("1. Testing Basic Network Connectivity")
    print("=" * 60)

    api_base = os.getenv("OPENAI_BASE_URL", "https://cnapi.kksj.org/v1")
    print(f"Target: {api_base}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_base.replace("/v1", ""))
            print(f"✅ Network reachable - Status: {response.status_code}")
            return True
    except httpx.ConnectTimeout:
        print(f"❌ Connection timeout - Cannot reach {api_base}")
        return False
    except httpx.ConnectError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_openai_client():
    """Test OpenAI client with actual API call"""
    print("\n" + "=" * 60)
    print("2. Testing OpenAI Client API Call")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY", "")
    api_base = os.getenv("OPENAI_BASE_URL", "https://cnapi.kksj.org/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return False

    print(f"API Base: {api_base}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:20]}...{api_key[-10:]}")

    try:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=30.0,
        )

        print("\nSending test request...")
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Say 'Hello'"}
            ],
            max_tokens=10,
            temperature=0.7,
        )

        print(f"✅ API call successful!")
        print(f"Response: {response.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"❌ API call failed: {type(e).__name__}: {e}")
        return False


async def test_alternative_endpoint():
    """Test alternative API endpoints"""
    print("\n" + "=" * 60)
    print("3. Testing Alternative API Endpoints")
    print("=" * 60)

    alternatives = [
        ("OpenAI Official", "https://api.openai.com/v1"),
        ("OpenRouter", "https://openrouter.ai/api/v1"),
        ("DeepSeek", "https://api.deepseek.com/v1"),
    ]

    for name, endpoint in alternatives:
        print(f"\nTesting {name}: {endpoint}")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(endpoint.replace("/v1", ""))
                print(f"  ✅ Reachable - Status: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Unreachable: {e}")


async def test_dns_resolution():
    """Test DNS resolution"""
    print("\n" + "=" * 60)
    print("4. Testing DNS Resolution")
    print("=" * 60)

    api_base = os.getenv("OPENAI_BASE_URL", "https://cnapi.kksj.org/v1")
    hostname = api_base.split("//")[1].split("/")[0]

    print(f"Resolving: {hostname}")

    try:
        import socket
        ip_addresses = socket.gethostbyname_ex(hostname)[2]
        print(f"✅ DNS resolved: {', '.join(ip_addresses)}")
        return True
    except socket.gaierror:
        print(f"❌ DNS resolution failed for {hostname}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "🔍 LLM API Connection Diagnostic Tool" + "\n")

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    results = {}

    # Run tests
    results["dns"] = await test_dns_resolution()
    results["connectivity"] = await test_basic_connectivity()
    results["openai_client"] = await test_openai_client()
    await test_alternative_endpoint()

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")

    # Recommendations
    print("\n" + "=" * 60)
    print("💡 Recommendations")
    print("=" * 60)

    if not results["dns"]:
        print("• DNS resolution failed - Check /etc/resolv.conf or network settings")

    if not results["connectivity"]:
        print("• Network unreachable - Check firewall, proxy settings, or try VPN")

    if not results["openai_client"]:
        print("• API call failed - Try:")
        print("  1. Verify API key is valid")
        print("  2. Check if endpoint requires payment")
        print("  3. Try alternative endpoint (OpenRouter, DeepSeek)")
        print("  4. Set up HTTP proxy if needed:")
        print("     export HTTP_PROXY=http://proxy:port")
        print("     export HTTPS_PROXY=http://proxy:port")

    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
