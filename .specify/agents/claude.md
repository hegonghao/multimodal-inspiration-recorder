# 多模输入灵感记录器 Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-27

## Active Technologies

### Frontend
- **Flutter**: 3.16+
- **Dart**: 3.2+
- **Drift ORM**: 2.16+ (SQLite数据库)
- **google_mlkit_text_recognition**: 0.13+ (OCR)
- **record**: 5.0+ (语音录制)
- **flutter_bloc**: 8.1+ (状态管理)

### Backend
- **Python**: 3.11+
- **FastAPI**: 0.104+
- **SQLAlchemy**: 2.0+ (异步ORM)
- **SQLite**: 本地数据存储
- **Redis**: 7.0+ (任务队列)
- **ARQ**: 0.25+ (异步任务队列)

### External Services
- **Notion API**: 云端同步
- **OpenAI-compatible LLM**: 分类和摘要
  - Development: Ollama (llama3.1本地)
  - Production: vLLM或OpenAI
- **Deepgram API**: 语音转写(可选)
- **Google ML Kit**: OCR文字识别

### Database
- **SQLite**: 本地离线存储(启用WAL模式)
- **SQLCipher**: 数据库加密(可选)

## Project Structure

```text
多模输入灵感记录器/
├── backend/                    # FastAPI后端
│   ├── src/
│   │   ├── models/            # SQLAlchemy数据模型
│   │   │   ├── inspiration.py
│   │   │   ├── sync_status.py
│   │   │   └── user_config.py
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── ai_processor.py    # LLM集成
│   │   │   ├── ocr_service.py     # OCR服务
│   │   │   ├── speech_to_text.py  # 语音转写
│   │   │   └── notion_sync.py     # Notion同步
│   │   ├── api/               # FastAPI路由
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │       ├── records.py
│   │   │       └── sync.py
│   │   └── database/          # 数据库配置
│   │       ├── connection.py
│   │       └── migrations/
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── requirements.txt
│   └── Dockerfile
│
├── app/                        # Flutter前端
│   ├── lib/
│   │   ├── main.dart
│   │   ├── core/
│   │   │   ├── constants.dart
│   │   │   ├── themes.dart
│   │   │   └── utils.dart
│   │   ├── data/
│   │   │   ├── models/
│   │   │   │   ├── inspiration_record.dart
│   │   │   │   ├── sync_status.dart
│   │   │   │   └── user_preferences.dart
│   │   │   ├── repositories/
│   │   │   │   ├── local_repository.dart
│   │   │   │   └── remote_repository.dart
│   │   │   └── services/
│   │   │       ├── storage_service.dart
│   │   │       ├── api_service.dart
│   │   │       ├── audio_service.dart
│   │   │       └── camera_service.dart
│   │   ├── presentation/
│   │   │   ├── pages/
│   │   │   │   ├── home_page.dart
│   │   │   │   ├── voice_input_page.dart
│   │   │   │   ├── text_input_page.dart
│   │   │   │   └── image_input_page.dart
│   │   │   ├── widgets/
│   │   │   └── providers/
│   │   └── tests/
│   ├── assets/
│   ├── android/
│   ├── ios/
│   └── pubspec.yaml
│
├── specs/                      # 规格文档
│   └── 1-multimodal-capture/
│       ├── spec.md
│       ├── plan.md
│       ├── research.md
│       ├── data-model.md
│       ├── quickstart.md
│       └── contracts/
│           └── api.yaml
│
├── .specify/                   # Specify框架
│   ├── templates/
│   ├── memory/
│   │   └── constitution.md
│   └── agents/
│       └── claude.md (this file)
│
├── docker-compose.yml
└── README.md
```

## Commands

### Backend Development

```bash
# 创建Python虚拟环境
cd backend
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动FastAPI服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 启动ARQ Worker(新终端)
arq app.worker.WorkerSettings

# 运行测试
pytest tests/ -v
pytest tests/ --cov=app --cov-report=html

# 代码格式化
black app/ tests/
isort app/ tests/
flake8 app/ tests/
```

### Flutter Development

```bash
# 安装依赖
cd app
flutter pub get

# 生成Drift代码
flutter pub run build_runner build --delete-conflicting-outputs

# 运行应用
flutter run

# 运行到特定设备
flutter run -d <device_id>

# 运行测试
flutter test
flutter test integration_test/

# 代码格式化
flutter format lib/

# 分析代码质量
flutter analyze
```

### Docker Commands

```bash
# 构建并启动所有服务
docker-compose up --build

# 后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f api
docker-compose logs -f worker

# 停止服务
docker-compose down

# 清理所有数据
docker-compose down -v
```

### Ollama Commands (本地LLM)

```bash
# 安装模型
ollama pull llama3.1

# 启动服务
ollama serve

# 测试API
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# 列出已安装模型
ollama list

# 删除模型
ollama rm llama3.1
```

### Redis Commands

```bash
# 启动Redis
redis-server

# 连接Redis CLI
redis-cli

# 监控Redis操作
redis-cli monitor

# 查看队列状态
redis-cli LLEN arq:queue

# 清空所有数据(慎用)
redis-cli FLUSHALL
```

## Code Style

### Python (Backend)

**遵循PEP 8标准**:

```python
# 文件头部导入顺序
import os
import sys
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import InspirationRecord
from app.services.ai_processor import AIProcessor

# 使用类型提示
async def create_record(
    data: InspirationRecordCreate,
    db: AsyncSession = Depends(get_db)
) -> InspirationRecord:
    """
    创建新的灵感记录

    Args:
        data: 记录创建数据
        db: 数据库会话

    Returns:
        创建的记录对象

    Raises:
        HTTPException: 验证失败或存储错误
    """
    record = InspirationRecord(**data.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record

# 错误处理
try:
    result = await process_ai(content)
except APIResponseError as e:
    logger.error(f"AI processing failed: {e}")
    raise HTTPException(status_code=503, detail="AI service unavailable")

# 异步上下文管理器
async with AsyncClient(auth=token) as client:
    response = await client.pages.create(...)
```

**命名规范**:
- 类名: `PascalCase`
- 函数名: `snake_case`
- 常量: `UPPER_SNAKE_CASE`
- 私有变量: `_leading_underscore`

### Dart/Flutter (Frontend)

**遵循Dart Style Guide**:

```dart
// 文件头部导入顺序
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:drift/drift.dart';

import '../../../core/constants.dart';
import '../../data/models/inspiration_record.dart';

// 使用类型注解
Future<InspirationRecord> createRecord({
  required String title,
  required String content,
  required InputType inputType,
}) async {
  final record = InspirationRecord(
    title: title,
    content: content,
    inputType: inputType,
  );

  await _db.insertRecord(record);
  return record;
}

// 错误处理
try {
  final result = await _api.processAI(content);
} on DioException catch (e) {
  logger.e('API call failed: ${e.message}');
  rethrow;
} catch (e) {
  logger.e('Unexpected error: $e');
  throw Exception('Failed to process content');
}

// Widget组件
class VoiceRecorderWidget extends StatefulWidget {
  const VoiceRecorderWidget({
    super.key,
    required this.onRecordingComplete,
  });

  final void Function(String audioPath) onRecordingComplete;

  @override
  State<VoiceRecorderWidget> createState() => _VoiceRecorderWidgetState();
}

// 使用const构造函数
const SizedBox(height: 16),
const Text('Hello'),
```

**命名规范**:
- 类名: `PascalCase`
- 变量/函数名: `camelCase`
- 常量: `lowerCamelCase`
- 私有成员: `_leadingUnderscore`
- 文件名: `snake_case.dart`

### SQL (Database)

```sql
-- 使用小写和下划线
CREATE TABLE inspiration_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引命名: idx_table_column
CREATE INDEX idx_inspiration_created_at
    ON inspiration_records(created_at DESC);

-- 外键命名: fk_table_ref_table
ALTER TABLE sync_queue
    ADD CONSTRAINT fk_sync_queue_record
    FOREIGN KEY (record_id) REFERENCES inspiration_records(id);
```

## Recent Changes

### Feature 1: Multimodal Capture (2025-10-27)

**Added**:
- 三种输入方式: 语音/文字/图片
- AI自动分类和摘要功能
- 本地SQLite数据库(Drift ORM for Flutter, SQLAlchemy for Backend)
- Notion异步同步(ARQ任务队列)
- OpenAI兼容LLM集成
- Google ML Kit OCR识别

**Technologies**:
- Frontend: Flutter + Drift + BLoC
- Backend: FastAPI + SQLAlchemy + ARQ
- Database: SQLite (WAL mode)
- External: Notion API, Ollama/OpenAI, ML Kit

**Key Files**:
- `specs/1-multimodal-capture/plan.md`: 实施计划
- `specs/1-multimodal-capture/data-model.md`: 数据模型
- `specs/1-multimodal-capture/contracts/api.yaml`: API规范
- `specs/1-multimodal-capture/quickstart.md`: 快速入门

<!-- MANUAL ADDITIONS START -->
<!--
此区域用于手动添加项目特定的开发指南
例如: 团队约定、特殊配置、部署流程等
-->

<!-- MANUAL ADDITIONS END -->