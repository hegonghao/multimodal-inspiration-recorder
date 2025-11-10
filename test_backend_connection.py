#!/usr/bin/env python3
"""Test if backend is accessible from different URLs"""
import requests
import socket

def test_backend_connection():
    """Test backend connectivity"""

    print("\n" + "=" * 60)
    print("Backend Connectivity Test")
    print("=" * 60)

    # Get current machine's IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    print(f"\n本机信息:")
    print(f"  主机名: {hostname}")
    print(f"  本地IP: {local_ip}")

    # Test URLs
    test_urls = [
        "http://localhost:8000/api/v1/health/liveness",
        "http://127.0.0.1:8000/api/v1/health/liveness",
        f"http://{local_ip}:8000/api/v1/health/liveness",
        "http://192.168.13.222:8000/api/v1/health/liveness",
    ]

    print(f"\n测试Backend连接:")
    for url in test_urls:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"  ✅ {url} - 可访问")
            else:
                print(f"  ❌ {url} - HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"  ❌ {url} - 连接失败")
        except requests.exceptions.Timeout:
            print(f"  ❌ {url} - 超时")
        except Exception as e:
            print(f"  ❌ {url} - 错误: {e}")

    print("\n" + "=" * 60)
    print("建议:")
    print("  1. 确认Backend容器正在运行: docker-compose ps")
    print("  2. 如果使用Android真机，请确保:")
    print(f"     - 手机和电脑在同一WiFi网络")
    print(f"     - App配置的Backend URL为: http://{local_ip}:8000")
    print("  3. 如果使用Android模拟器，Backend URL应为: http://10.0.2.2:8000")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    test_backend_connection()
