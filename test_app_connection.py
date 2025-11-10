#!/usr/bin/env python3
"""Test if App can connect to Backend by simulating an App request"""
import requests
import sys

def test_app_connection():
    """Test connection from App perspective"""

    print("\n" + "=" * 60)
    print("App-to-Backend Connection Test")
    print("=" * 60)

    # Test the exact endpoint and method that App uses
    backend_url = "http://192.168.13.222:8000"
    endpoint = "/api/v1/records/upload"

    print(f"\nBackend URL: {backend_url}")
    print(f"Endpoint: POST {endpoint}")

    # Test 1: Health check
    print("\n[1] Testing health check...")
    try:
        response = requests.get(f"{backend_url}/api/v1/health/liveness", timeout=5)
        if response.status_code == 200:
            print(f"   SUCCESS: Health check passed - {response.json()}")
        else:
            print(f"   FAIL: Health check failed - HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   FAIL: Health check failed - {e}")
        return False

    # Test 2: POST /upload with text record (simulating App behavior)
    print("\n[2] Testing text record creation (simulating App behavior)...")
    try:
        # Simulate the exact FormData that App sends
        data = {
            'input_type': 'text',
            'content': 'Test from connection script',
            'language': 'zh',
            'auto_process': True,
        }

        print(f"   Sending data: {data}")
        response = requests.post(
            f"{backend_url}{endpoint}",
            data=data,  # FormData format
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            print(f"   SUCCESS: Record created!")
            print(f"      Record ID: {result.get('id')}")
            print(f"      Title: {result.get('title')}")
            return True
        else:
            print(f"   FAIL: Creation failed - HTTP {response.status_code}")
            print(f"      Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print(f"   FAIL: Request timeout")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"   FAIL: Connection error - {e}")
        return False
    except Exception as e:
        print(f"   FAIL: Unknown error - {e}")
        return False

    finally:
        print("\n" + "=" * 60)
        print("Notes:")
        print("  - If health check passes but POST fails: Backend routing issue")
        print("  - If both tests fail: Check if Backend is running")
        print("  - App should use the same URL and endpoint")
        print("=" * 60 + "\n")

if __name__ == "__main__":
    success = test_app_connection()
    sys.exit(0 if success else 1)
