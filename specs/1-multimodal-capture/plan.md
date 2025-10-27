# Implementation Plan: 多模输入灵感记录器

**Branch**: `1-multimodal-capture` | **Date**: 2025-10-27 | **Spec**: /specs/1-multimodal-capture/spec.md
**Input**: Feature specification from `/specs/1-multimodal-capture/spec.md`

## Summary

基于用户对快速记录灵感的核心需求，构建支持语音、文字、图片三种输入方式的灵感记录器。前端采用Flutter实现跨平台移动应用，后端使用FastAPI提供轻量级API服务，通过自定义OpenAI兼容LLM实现智能分类和摘要功能。数据优先写入SQLite本地缓存，确保离线可用性，然后异步同步到Notion进行长期存储和管理。

## Technical Context

**Language/Version**: Flutter 3.16+, Python 3.11+, FastAPI 0.104+
**Primary Dependencies**: Flutter (mobile frontend), FastAPI (backend), SQLite (local storage), Notion API (sync), OpenAI-compatible API (AI processing)
**Storage**: SQLite for local cache, Notion for cloud storage
**Testing**: flutter_test for Flutter, pytest for FastAPI backend
**Target Platform**: iOS 15+, Android 8+, Cross-platform mobile app
**Project Type**: Mobile + API (Flutter frontend + FastAPI backend)
**Performance Goals**: UI response < 1s, voice transcription real-time, OCR processing < 5s, sync latency < 30s
**Constraints**: < 200MB local storage, offline-capable, battery-optimized voice recording
**Scale/Scope**: Single user per installation, max 1,000 records, 5-minute voice recording limit

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 必须通过的宪法门控检查：
- **多模态整合**: ✅ 三种输入方式(语音、文字、图片)在规格中明确要求完整支持
- **用户体验一致性**: ✅ 规格要求操作流程≤3步完成，5秒内开始记录
- **模块化架构**: ✅ 前后端分离设计，每个输入模式独立实现
- **测试覆盖率**: ✅ 核心功能要求90%测试覆盖率，需要在Phase 1中具体规划
- **性能标准**: ✅ 明确要求UI响应<1秒，简单操作<500ms
- **依赖隔离**: ✅ 外部依赖(LLM、OCR、Notion)通过接口层隔离
- **数据驱动**: ✅ 包含具体成功指标(90%用户独立完成，任务时间减少40%)

### 复杂度追踪（如有违反宪法的情况必须在此说明）：

## Project Structure

### Documentation (this feature)

```text
specs/1-multimodal-capture/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api.yaml         # OpenAPI specification for backend
│   └── models.json      # Data models and validation schemas
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── inspiration.py      # Inspiration record model
│   │   ├── sync_status.py     # Sync status tracking
│   │   └── user_config.py     # User preferences
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_processor.py     # LLM integration
│   │   ├── ocr_service.py      # Image text recognition
│   │   ├── speech_to_text.py   # Voice transcription
│   │   └── notion_sync.py      # Notion API integration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI application
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── records.py     # Inspiration record endpoints
│   │   │   └── sync.py        # Sync management endpoints
│   │   └── middleware/
│   │       ├── __init__.py
│   │       └── error_handler.py
│   └── database/
│       ├── __init__.py
│       ├── connection.py      # SQLite connection management
│       └── migrations/        # Database schema migrations
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── requirements.txt
└── Dockerfile

app/
├── lib/
│   ├── main.dart              # Flutter app entry point
│   ├── core/
│   │   ├── constants.dart     # App constants
│   │   ├── themes.dart        # UI themes
│   │   └── utils.dart         # Utility functions
│   ├── data/
│   │   ├── models/
│   │   │   ├── inspiration_record.dart
│   │   │   ├── sync_status.dart
│   │   │   └── user_preferences.dart
│   │   ├── repositories/
│   │   │   ├── local_repository.dart     # Local storage
│   │   │   └── remote_repository.dart   # API client
│   │   └── services/
│   │       ├── storage_service.dart     # Local data persistence
│   │       ├── api_service.dart         # Backend API client
│   │       ├── audio_service.dart       # Voice recording
│   │       ├── camera_service.dart      # Image capture
│   │       └── notification_service.dart
│   ├── presentation/
│   │   ├── pages/
│   │   │   ├── home_page.dart           # Main capture interface
│   │   │   ├── voice_input_page.dart    # Voice recording UI
│   │   │   ├── text_input_page.dart     # Text input UI
│   │   │   ├── image_input_page.dart    # Image upload UI
│   │   │   └── settings_page.dart      # Configuration
│   │   ├── widgets/
│   │   │   ├── voice_recorder.dart      # Voice recording widget
│   │   │   ├── text_editor.dart         # Text editing widget
│   │   │   ├── image_picker.dart        # Image selection widget
│   │   │   └── sync_indicator.dart      # Sync status widget
│   │   └── providers/
│   │       ├── inspiration_provider.dart  # State management
│   │       └── sync_provider.dart        # Sync state
│   └── tests/
│       ├── unit/
│       ├── widget/
│       └── integration/
├── assets/
│   ├── images/
│   └── sounds/
├── android/
├── ios/
├── pubspec.yaml
└── README.md
```

**Structure Decision**: 采用Flutter移动应用 + FastAPI后端的混合架构，确保跨平台兼容性和离线功能支持。前端负责用户交互和本地缓存，后端处理AI相关计算和外部API集成。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |