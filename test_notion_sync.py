#!/usr/bin/env python3
"""
测试 Notion 同步配置的脚本

使用步骤：
1. 在此脚本中填入真实的 Notion 凭据
2. 运行脚本来配置后端
3. 在 Flutter 应用中点击同步按钮
"""

import requests
import json

# 后端 API 地址
API_BASE_URL = "http://localhost:8000/api/v1"

def update_notion_credentials(token: str, database_id: str):
    """更新 Notion 凭据到后端"""
    url = f"{API_BASE_URL}/preferences"

    data = {
        "notion_token": token,
        "notion_database_id": database_id,
    }

    print("📝 更新 Notion 凭据到后端...")
    response = requests.put(url, json=data)

    if response.status_code == 200:
        print("✅ Notion 凭据更新成功")
        result = response.json()
        print(f"   - Database ID: {result.get('notion_database_id')}")
        print(f"   - Updated at: {result.get('updated_at')}")
        return True
    else:
        print(f"❌ 更新失败: {response.status_code}")
        print(f"   错误: {response.text}")
        return False

def test_notion_connection(token: str, database_id: str):
    """测试 Notion 连接"""
    url = f"{API_BASE_URL}/preferences/test-notion"

    data = {
        "notion_token": token,
        "notion_database_id": database_id,
    }

    print("\n🔍 测试 Notion 连接...")
    response = requests.post(url, json=data)

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("✅ Notion 连接测试成功")
            print(f"   响应时间: {result.get('details', {}).get('response_time_ms')}ms")
            return True
        else:
            print(f"❌ Notion 连接失败: {result.get('message')}")
            return False
    else:
        print(f"❌ 测试请求失败: {response.status_code}")
        return False

def retry_failed_syncs():
    """重试所有失败的同步任务"""
    url = f"{API_BASE_URL}/sync/retry-failed"

    print("\n🔄 重试失败的同步任务...")
    response = requests.post(url)

    if response.status_code == 200:
        result = response.json()
        reset_count = result.get("reset_count", 0)
        print(f"✅ 已重置 {reset_count} 个失败的任务")
        return True
    else:
        print(f"❌ 重试失败: {response.status_code}")
        return False

def trigger_sync():
    """触发手动同步"""
    url = f"{API_BASE_URL}/sync/trigger"

    print("\n🚀 触发同步...")
    response = requests.post(url)

    if response.status_code == 200 or response.status_code == 202:
        result = response.json()
        status = result.get("status")

        if status == "success":
            enqueued = result.get("enqueued_count", 0)
            print(f"✅ 同步已触发，入队任务数: {enqueued}")
            return True
        elif status == "disabled":
            print(f"⚠️  同步被禁用: {result.get('message')}")
            return False
        else:
            print(f"ℹ️  {result.get('message')}")
            return True
    else:
        print(f"❌ 触发同步失败: {response.status_code}")
        return False

def check_sync_status():
    """检查同步状态"""
    url = f"{API_BASE_URL}/sync/status"

    print("\n📊 检查同步状态...")
    response = requests.get(url)

    if response.status_code == 200:
        result = response.json()
        print(f"   - 总记录数: {result.get('total_records')}")
        print(f"   - 已同步: {result.get('synced_count')}")
        print(f"   - 待同步: {result.get('pending_count')}")
        print(f"   - 失败: {result.get('failed_count')}")
        print(f"   - 同步启用: {result.get('sync_enabled')}")
        return result
    else:
        print(f"❌ 获取状态失败: {response.status_code}")
        return None


if __name__ == "__main__":
    print("=" * 70)
    print("Notion 同步配置测试脚本")
    print("=" * 70)

    # 请在这里填入您的真实 Notion 凭据
    # 获取方法：https://www.notion.so/my-integrations
    NOTION_TOKEN = "secret_your_actual_notion_token_here"
    NOTION_DATABASE_ID = "your_actual_database_id_here"

    if NOTION_TOKEN == "secret_your_actual_notion_token_here":
        print("\n⚠️  警告：请先在脚本中填入真实的 Notion 凭据！")
        print("\n使用方法：")
        print("1. 访问 https://www.notion.so/my-integrations 创建 Integration")
        print("2. 复制 Internal Integration Token")
        print("3. 在 Notion 数据库中添加 Integration 连接")
        print("4. 复制数据库 ID（从数据库 URL 中获取）")
        print("5. 在本脚本中填入这些凭据")
        exit(1)

    # 步骤 1: 测试 Notion 连接
    if not test_notion_connection(NOTION_TOKEN, NOTION_DATABASE_ID):
        print("\n❌ Notion 连接测试失败，请检查凭据是否正确")
        exit(1)

    # 步骤 2: 更新凭据到后端
    if not update_notion_credentials(NOTION_TOKEN, NOTION_DATABASE_ID):
        print("\n❌ 更新凭据失败")
        exit(1)

    # 步骤 3: 重试失败的同步任务
    retry_failed_syncs()

    # 步骤 4: 检查同步状态
    check_sync_status()

    # 步骤 5: 触发同步
    trigger_sync()

    print("\n" + "=" * 70)
    print("✅ 配置完成！现在可以在 Flutter 应用中查看同步状态")
    print("=" * 70)
