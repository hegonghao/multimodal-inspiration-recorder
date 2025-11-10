#!/usr/bin/env python3
import requests
import json

# Test AI processing endpoint
url = "http://localhost:8000/api/v1/ai/process"

data = {
    "content": "今天学习了FastAPI的异步编程和数据库连接池管理，感觉收获很大。需要在项目中应用这些最佳实践。",
    "input_type": "text",
    "max_summary_length": 50
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
