---

description: "Task list for multimodal inspiration recorder feature implementation"
---

# Tasks: 多模输入灵感记录器

**Input**: Design documents from `/specs/1-multimodal-capture/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Unit and integration tests included based on research.md requirements (90% coverage goal)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/` at repository root
- **Frontend**: `app/lib/` at repository root
- **Tests**: `backend/tests/` and `app/test/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create Flutter + FastAPI project structure per implementation plan
- [X] T002 Initialize Flutter project with required dependencies (Drift, record, ML Kit, etc.)
- [X] T003 Initialize Python FastAPI project with required dependencies (OpenAI, Notion, ARQ, etc.)
- [X] T004 [P] Configure Flutter linting and formatting (analysis_options.yaml)
- [X] T005 [P] Configure Python linting and formatting (ruff, black, mypy)
- [X] T006 Create Docker configuration files (Dockerfile, docker-compose.yml)
- [X] T007 Create environment configuration files (.env.example, .env)
- [X] T008 Setup Git repository with .gitignore for Flutter/Python projects

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 Setup SQLite database schema and migrations framework (Alembic for backend, Drift for Flutter)
- [X] T010 [P] Implement database connection management in backend/src/database/connection.py
- [ ] T011 [P] Implement Drift database class in app/lib/data/database.dart
- [ ] T012 Create InspirationRecord entity in both backend and frontend
- [ ] T013 [P] Create SyncQueue entity for synchronization tasks
- [ ] T014 [P] Create UserPreferences entity for configuration
- [ ] T015 Setup API routing structure in backend/src/api/main.py
- [ ] T016 [P] Setup error handling middleware in backend/src/api/middleware/error_handler.py
- [ ] T017 Configure logging infrastructure (structlog for backend, flutter logs for frontend)
- [ ] T018 Setup environment configuration management (python-dotenv, flutter config)
- [ ] T019 [P] Create API client service in app/lib/data/services/api_service.dart
- [ ] T020 [P] Create local storage service in app/lib/data/services/storage_service.dart

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 快速语音记录灵感 (Priority: P1) 🎯 MVP

**Goal**: Enable users to quickly record voice inspirations with automatic transcription and AI categorization

**Independent Test**: User can record voice input, system automatically transcribes and generates分类标签 without manual intervention

### Tests for User Story 1 ⚠️

- [ ] T021 [P] [US1] Contract test for POST /records endpoint in backend/tests/contract/test_records_api.py
- [ ] T022 [P] [US1] Contract test for POST /ai/process endpoint in backend/tests/contract/test_ai_processing.py
- [ ] T023 [P] [US1] Integration test for voice recording workflow in backend/tests/integration/test_voice_workflow.py
- [ ] T024 [P] [US1] Widget test for voice recorder UI in app/test/widget/test_voice_recorder.dart

### Implementation for User Story 1

- [ ] T025 [P] [US1] Implement voice recording service using record package in app/lib/data/services/audio_service.dart
- [ ] T026 [P] [US1] Create Deepgram speech-to-text client in backend/src/services/speech_to_text.py
- [ ] T027 [P] [US1] Implement AI processor service in backend/src/services/ai_processor.py
- [ ] T028 [US1] Create POST /records endpoint in backend/src/api/routes/records.py (depends on T025, T026, T027)
- [ ] T029 [US1] Implement voice input page UI in app/lib/presentation/pages/voice_input_page.dart
- [ ] T030 [US1] Create voice recorder widget in app/lib/presentation/widgets/voice_recorder.dart
- [ ] T031 [US1] Implement inspiration provider for state management in app/lib/presentation/providers/inspiration_provider.dart
- [ ] T032 [US1] Add file upload handling for audio files in backend/src/api/routes/records.py
- [ ] T033 [US1] Add validation for voice recording duration (5-minute limit) with UI indicator
- [ ] T034 [US1] Add error handling for recording failures and transcription errors
- [ ] T035 [US1] Add real-time transcription display during recording
- [ ] T036 [US1] Implement automatic saving 3 seconds after speech stops

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - 图片内容快速识别 (Priority: P1)

**Goal**: Enable users to capture image content with OCR text recognition and AI categorization

**Independent Test**: User can upload image with text, system performs OCR and creates categorized inspiration record

### Tests for User Story 2 ⚠️

- [ ] T037 [P] [US2] Contract test for image upload to POST /records endpoint in backend/tests/contract/test_image_ocr.py
- [ ] T038 [P] [US2] Integration test for OCR workflow in backend/tests/integration/test_ocr_workflow.py
- [ ] T039 [P] [US2] Widget test for image picker UI in app/test/widget/test_image_picker.dart

### Implementation for User Story 2

- [ ] T040 [P] [US2] Implement image picker service in app/lib/data/services/camera_service.dart
- [ ] T041 [P] [US2] Create ML Kit OCR service in backend/src/services/ocr_service.py
- [ ] T042 [P] [US2] Implement image preprocessing for OCR accuracy optimization
- [ ] T043 [US2] Create image input page UI in app/lib/presentation/pages/image_input_page.dart
- [ ] T044 [US2] Create image picker widget in app/lib/presentation/widgets/image_picker.dart
- [ ] T045 [US2] Add image file upload handling to POST /records endpoint
- [ ] T046 [US2] Add OCR confidence scoring and validation
- [ ] T047 [US2] Add error handling for OCR failures with manual input fallback
- [ ] T048 [US2] Integrate OCR results with AI processing pipeline

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - 文字快速输入与智能分类 (Priority: P2)

**Goal**: Provide direct text input interface with automatic AI categorization

**Independent Test**: User can input text directly, system generates categories and summary automatically

### Tests for User Story 3 ⚠️

- [ ] T049 [P] [US3] Contract test for text input to POST /records endpoint in backend/tests/contract/test_text_input.py
- [ ] T050 [P] [US3] Integration test for text classification workflow in backend/tests/integration/test_text_workflow.py
- [ ] T051 [P] [US3] Widget test for text editor UI in app/test/widget/test_text_editor.dart

### Implementation for User Story 3

- [ ] T052 [P] [US3] Create text input page UI in app/lib/presentation/pages/text_input_page.dart
- [ ] T053 [P] [US3] Create text editor widget in app/lib/presentation/widgets/text_editor.dart
- [ ] T054 [US3] Add text validation (minimum 10 characters) with user prompts
- [ ] T055 [US3] Implement auto-save functionality for text input
- [ ] T056 [US3] Add character counter and validation feedback
- [ ] T057 [US3] Integrate text input with existing AI processing pipeline

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: User Story 4 - 本地数据管理与Notion同步 (Priority: P2)

**Goal**: Ensure all data is stored locally first with automatic Notion synchronization

**Independent Test**: User can use all features offline, data syncs automatically when network is available

### Tests for User Story 4 ⚠️

- [ ] T058 [P] [US4] Contract test for sync endpoints in backend/tests/contract/test_sync_api.py
- [ ] T059 [P] [US4] Integration test for offline-first workflow in backend/tests/integration/test_offline_sync.py
- [ ] T060 [P] [US4] Integration test for Notion sync in backend/tests/integration/test_notion_sync.py

### Implementation for User Story 4

- [ ] T061 [P] [US4] Implement ARQ task queue worker in backend/src/app/worker.py
- [ ] T062 [P] [US4] Create Notion API client service in backend/src/services/notion_sync.py
- [ ] T063 [P] [US4] Implement sync queue management service
- [ ] T064 [P] [US4] Create GET /sync/status endpoint in backend/src/api/routes/sync.py
- [ ] T065 [P] [US4] Create POST /sync/trigger endpoint in backend/src/api/routes/sync.py
- [ ] T066 [US4] Implement retry mechanism with exponential backoff
- [ ] T067 [US4] Create offline-first repository pattern in app/lib/data/repositories/local_repository.dart
- [ ] T068 [US4] Add network connectivity monitoring in app/lib/data/services/connectivity_service.dart
- [ ] T069 [US4] Implement sync status indicator widget in app/lib/presentation/widgets/sync_indicator.dart
- [ ] T070 [US4] Create settings page for Notion configuration in app/lib/presentation/pages/settings_page.dart
- [ ] T071 [US4] Add conflict resolution (Last-Write-Wins) with user notifications
- [ ] T072 [US4] Implement storage limit management (1000 records)
- [ ] T073 [US4] Add background sync for Android (WorkManager) and iOS (BackgroundFetch)

**Checkpoint**: User Story 4 completes the core functionality pipeline

---

## Phase 7: Cross-Cutting Infrastructure

**Purpose**: Shared services and components that support all user stories

**Dependencies**: Can start after Phase 2 (Foundational), works in parallel with user story implementation

- [ ] T074 [P] Implement notification service for sync status in app/lib/data/services/notification_service.dart
- [ ] T075 [P] Create main home page with input mode selection in app/lib/presentation/pages/home_page.dart
- [ ] T076 [P] Implement app navigation and routing structure
- [ ] T077 [P] Create app themes and styling in app/lib/core/themes.dart
- [ ] T078 [P] Add constants and configuration in app/lib/core/constants.dart
- [ ] T079 Implement utility functions in app/lib/core/utils.dart
- [ ] T080 [P] Create comprehensive error handling for API failures
- [ ] T081 [P] Add loading states and progress indicators
- [ ] T082 Implement user preferences management (GET/PUT /preferences endpoints)
- [ ] T083 [P] Add LLM connection testing (POST /preferences/test-llm)
- [ ] T084 [P] Add Notion connection testing (POST /preferences/test-notion)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Constitution Compliance (CRITICAL)

- [ ] T085 [P] Implement usage analytics service for Principle VII (Data-Driven Iteration) in backend/src/services/analytics_service.py
- [ ] T086 [P] Add performance monitoring dashboard for key metrics (task completion time, feature usage) in backend/src/api/routes/analytics.py
- [ ] T087 [P] Create user satisfaction feedback mechanism in app/lib/presentation/pages/feedback_page.dart
- [ ] T088 Implement performance testing for Principle II (5-second recording start validation) in backend/tests/performance/test_recording_start.py
- [ ] T089 [P] Add UI responsiveness benchmarking suite (<1s requirement validation) in app/test/performance/test_ui_responsiveness.dart
- [ ] T090 Create OCR performance validation tests (<5s processing requirement) in backend/tests/performance/test_ocr_performance.py

### Quality & Documentation

- [ ] T091 [P] Documentation updates in README.md and API docs
- [ ] T092 Code cleanup and refactoring across all modules
- [ ] T093 Performance optimization (database indexing, batch operations)
- [ ] T094 [P] Complete unit test suite to 90% coverage requirement
- [ ] T095 [P] Integration tests for complete user workflows
- [ ] T096 Security hardening (input validation, SQL injection prevention)
- [ ] T097 [P] Run quickstart.md validation and setup verification
- [ ] T098 Implement SQLCipher encryption for local data with performance optimization
- [ ] T099 Add monitoring and metrics (Prometheus) for production deployment
- [ ] T100 Optimize app startup time and memory usage
- [ ] T101 Add accessibility features (screen reader support)
- [ ] T102 Final deployment preparation and production configuration

### Optional Features (Post-MVP)

- [ ] T103 [P] Implement optional PIN protection for app security in app/lib/core/security/pin_protection.dart (deferred to post-MVP based on user feedback)
- [ ] T104 Add PIN setup and validation UI in app/lib/presentation/pages/pin_setup_page.dart (optional, post-MVP)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Cross-Cutting Infrastructure (Phase 7)**: Can start after Phase 2, work in parallel with user stories
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Voice recording - Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Image OCR - Can start after Foundational - Independent of US1
- **User Story 3 (P2)**: Text input - Can start after Foundational - Uses shared AI processing
- **User Story 4 (P2)**: Sync system - Can start after Foundational - Serves all other stories

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD approach)
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1 (Voice Recording)

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for POST /records endpoint in backend/tests/contract/test_records_api.py"
Task: "Contract test for POST /ai/process endpoint in backend/tests/contract/test_ai_processing.py"
Task: "Integration test for voice recording workflow in backend/tests/integration/test_voice_workflow.py"
Task: "Widget test for voice recorder UI in app/test/widget/test_voice_recorder.dart"

# Launch all services for User Story 1 together:
Task: "Implement voice recording service using record package in app/lib/data/services/audio_service.dart"
Task: "Create Deepgram speech-to-text client in backend/src/services/speech_to_text.py"
Task: "Implement AI processor service in backend/src/services/ai_processor.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Voice Recording)
4. Complete Phase 4: User Story 2 (Image OCR)
5. **STOP and VALIDATE**: Test core multimodal functionality independently
6. Deploy/demo MVP with voice + image capabilities

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (Voice) → Test independently → Deploy/Demo (Core MVP)
3. Add User Story 2 (Image) → Test independently → Deploy/Demo (Complete multimodal)
4. Add User Story 3 (Text) → Test independently → Deploy/Demo (Full input coverage)
5. Add User Story 4 (Sync) → Test independently → Deploy/Demo (Complete product)
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (Week 1-2)
2. Once Foundational is done:
   - Developer A: User Story 1 (Voice Recording)
   - Developer B: User Story 2 (Image OCR)
   - Developer C: User Story 4 (Sync Infrastructure)
3. Stories complete and integrate independently
4. Developer C adds User Story 3 (Text Input) after sync infrastructure is ready

---

## Risk Mitigation Based on Research Findings

- **Voice Recording**: Use record package with AAC-LC encoding (5min = 3.6MB)
- **OCR**: Implement Google ML Kit with image preprocessing for 95%+ accuracy
- **LLM Integration**: Support both Ollama (development) and OpenAI-compatible APIs (production)
- **Sync**: Implement ARQ with Redis for reliable Notion synchronization
- **Performance**: Database indexing and WAL mode for <1s response times
- **Storage**: Implement 1000 record limit with cleanup strategies

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Research.md indicates 10-week timeline for MVP completion
- Target 90% test coverage as specified in requirements
- Offline-first architecture is critical for user experience
- Performance targets: UI response <1s, OCR <5s, sync latency <30s, recording start <5s
- Constitution compliance: Tasks T085-T090 address mandatory data-driven iteration and performance validation requirements
- PIN protection (T103-T104) deferred to post-MVP phase pending user feedback data

## Task Summary

- **Total Tasks**: 104 tasks (including constitution compliance and optional features)
- **MVP Critical Path**: T001-T084 (84 tasks for core functionality)
- **Constitution Compliance**: T085-T090 (6 tasks for mandatory requirements)
- **Quality & Polish**: T091-T102 (12 tasks)
- **Optional Post-MVP**: T103-T104 (2 tasks for PIN protection)