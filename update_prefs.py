#!/usr/bin/env python3
import requests
import json

# 更新用户首选项以添加 API key
url = "http://localhost:8000/api/v1/preferences"

data = {
    "openai_api_key": "sk-your-actual-api-key-here",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model": "gpt-4o-mini"
}

try:
    response = requests.put(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")