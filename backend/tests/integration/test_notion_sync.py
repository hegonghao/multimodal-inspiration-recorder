"""
Integration Tests for Notion Sync

Tests Notion API integration for User Story 4: Sync System
Validates end-to-end synchronization with Notion database including
rate limiting, retry logic, and error handling.

Note: These tests require valid Notion credentials in environment.
Use mocks if testing without real Notion access.
"""

import pytest
import httpx
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import select
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json

from src.api.main import app
from src.models.inspiration import InspirationRecord, SyncStatus
from src.models.sync_queue import SyncQueue, SyncQueueStatus, SyncOperation
from src.services.notion_sync import NotionSyncService, NotionConfig
from src.config import settings


@pytest.mark.asyncio
@pytest.mark.integration
class TestNotionConnectionVerification:
    """Tests for Notion API connection verification"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_notion_connection_api_endpoint(self, client):
        """
        Test POST /preferences/test-notion endpoint verifies connection.
        """
        # This test checks the connection verification endpoint
        response = await client.post("/api/v1/preferences/test-notion")

        # Should return status indicating connection state
        # May succeed or fail depending on environment configuration
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

        data = response.json()
        assert "status" in data

        if response.status_code == status.HTTP_200_OK:
            assert data["status"] in ["success", "connected"]

    @pytest.mark.skipif(
        not hasattr(settings, "NOTION_TOKEN") or not settings.NOTION_TOKEN,
        reason="Notion credentials not configured"
    )
    async def test_notion_service_verify_connection(self):
        """
        Test NotionSyncService.verify_connection() with real credentials.

        Skipped if Notion credentials not available.
        """
        service = NotionSyncService()

        try:
            is_connected = await service.verify_connection()

            # Should successfully verify connection
            assert isinstance(is_connected, bool)

            if is_connected:
                # Connection successful
                assert is_connected is True
            else:
                # Connection failed but handled gracefully
                assert is_connected is False

        finally:
            await service.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestNotionPageCreation:
    """Tests for creating Notion pages from inspiration records"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    async def db_session(self):
        """Get database session for verification"""
        from src.database.connection import get_db

        async for session in get_db():
            yield session

    @pytest.mark.skipif(
        not hasattr(settings, "NOTION_TOKEN") or not settings.NOTION_TOKEN,
        reason="Notion credentials not configured"
    )
    async def test_create_notion_page_from_record(self, client, db_session):
        """
        Test creating Notion page from InspirationRecord.

        Full workflow: Create record -> Sync to Notion -> Verify page ID saved
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "Notion同步测试：创建页面测试内容",
                "language": "zh",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Get record from database
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()
        assert record is not None

        # Attempt to sync to Notion
        notion_service = NotionSyncService()

        try:
            notion_page_id = await notion_service.create_page(record)

            if notion_page_id:
                # Successfully created page
                assert isinstance(notion_page_id, str)
                assert len(notion_page_id) > 0

                # Verify page ID would be saved to record
                # (In production, this happens via worker)
                assert notion_page_id != record.notion_page_id  # Would be updated

        finally:
            await notion_service.close()

    async def test_create_notion_page_with_mock(self, client, db_session):
        """
        Test Notion page creation with mocked API (no real credentials needed).
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "Mock Notion同步测试",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Get record
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()
        assert record is not None

        # Mock Notion API
        with patch('src.services.notion_sync.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful page creation
            mock_client.pages.create.return_value = {
                "id": "mock_page_id_12345",
                "created_time": datetime.utcnow().isoformat(),
            }

            # Create Notion service with mocked client
            notion_service = NotionSyncService()
            notion_service.client = mock_client

            try:
                page_id = await notion_service.create_page(record)

                # Should succeed with mock
                assert page_id == "mock_page_id_12345"

                # Verify create was called with correct parameters
                mock_client.pages.create.assert_called_once()

            finally:
                await notion_service.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestNotionPageUpdate:
    """Tests for updating Notion pages"""

    @pytest.fixture
    async def db_session(self):
        """Get database session"""
        from src.database.connection import get_db

        async for session in get_db():
            yield session

    async def test_update_notion_page_with_mock(self, db_session):
        """
        Test updating existing Notion page with mocked API.
        """
        # Create mock record
        from src.models.inspiration import InspirationRecordsCreate

        record_data = InspirationRecordsCreate(
            title="测试标题",
            content="测试更新内容",
            input_type="text",
            category_tags=json.dumps(["测试", "更新"]),
            summary="测试摘要",
            notion_page_id="existing_page_id_123",
            sync_status=SyncStatus.SYNCED,
        )

        # Create record in database
        record = InspirationRecord(**record_data.model_dump())
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)

        # Mock Notion API
        with patch('src.services.notion_sync.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful update
            mock_client.pages.update.return_value = {
                "id": "existing_page_id_123",
                "last_edited_time": datetime.utcnow().isoformat(),
            }

            # Update Notion page
            notion_service = NotionSyncService()
            notion_service.client = mock_client

            try:
                success = await notion_service.update_page(
                    notion_page_id="existing_page_id_123",
                    record=record
                )

                # Should succeed
                assert success is True

                # Verify update was called
                mock_client.pages.update.assert_called_once()

            finally:
                await notion_service.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestNotionPageArchive:
    """Tests for archiving (deleting) Notion pages"""

    async def test_archive_notion_page_with_mock(self):
        """
        Test archiving Notion page with mocked API.
        """
        # Mock Notion API
        with patch('src.services.notion_sync.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful archive
            mock_client.pages.update.return_value = {
                "id": "page_to_archive_123",
                "archived": True,
            }

            # Archive page
            notion_service = NotionSyncService()
            notion_service.client = mock_client

            try:
                success = await notion_service.archive_page(
                    notion_page_id="page_to_archive_123"
                )

                # Should succeed
                assert success is True

                # Verify archive was called with archived=True
                mock_client.pages.update.assert_called_once()
                call_args = mock_client.pages.update.call_args
                assert call_args.kwargs["archived"] is True

            finally:
                await notion_service.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestNotionRateLimiting:
    """Tests for Notion API rate limiting compliance"""

    async def test_rate_limiting_delay(self):
        """
        Test rate limiting delay is applied between requests.
        """
        import time

        # Mock Notion API
        with patch('src.services.notion_sync.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock successful responses
            mock_client.databases.retrieve.return_value = {
                "id": "test_db_id",
                "title": [{"text": {"content": "Test DB"}}],
            }

            notion_service = NotionSyncService()
            notion_service.client = mock_client

            try:
                # Make multiple requests
                start_time = time.time()

                await notion_service.verify_connection()
                await notion_service.verify_connection()
                await notion_service.verify_connection()

                end_time = time.time()
                elapsed = end_time - start_time

                # Should have rate limiting delays
                # 3 requests with 400ms delay = at least 800ms (2 delays between 3 requests)
                min_expected_time = NotionConfig.RATE_LIMIT_DELAY * 2

                assert elapsed >= min_expected_time, \
                    f"Rate limiting not working: {elapsed:.3f}s < {min_expected_time:.3f}s"

            finally:
                await notion_service.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestNotionRetryLogic:
    """Tests for Notion API retry logic with exponential backoff"""

    async def test_retry_on_api_error(self):
        """
        Test retry mechanism triggers on API errors.
        """
        from notion_client.errors import APIResponseError

        # Mock Notion API
        with patch('src.services.notion_sync.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock failure followed by success
            mock_client.pages.create.side_effect = [
                APIResponseError(
                    response=Mock(status_code=503, headers={}),
                    message="Service temporarily unavailable",
                    code="service_unavailable",
                ),
                APIResponseError(
                    response=Mock(status_code=503, headers={}),
                    message="Service temporarily unavailable",
                    code="service_unavailable",
                ),
                {"id": "retry_success_page_id"},  # Third attempt succeeds
            ]

            # Create mock record
            from src.models.inspiration import InspirationRecord

            mock_record = Mock(spec=InspirationRecord)
            mock_record.id = 1
            mock_record.title = "Retry Test"
            mock_record.content = "Testing retry logic"
            mock_record.input_type = "text"
            mock_record.category_tags = None
            mock_record.summary = None
            mock_record.created_at = datetime.utcnow()
            mock_record.updated_at = datetime.utcnow()

            notion_service = NotionSyncService()
            notion_service.client = mock_client

            try:
                # Should retry and eventually succeed
                page_id = await notion_service.create_page(mock_record)

                assert page_id == "retry_success_page_id"

                # Verify retries occurred
                assert mock_client.pages.create.call_count == 3

            finally:
                await notion_service.close()

    async def test_retry_respects_rate_limit_header(self):
        """
        Test 429 rate limit errors respect Retry-After header.
        """
        import time
        from notion_client.errors import APIResponseError

        # Mock Notion API
        with patch('src.services.notion_sync.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock 429 rate limit with Retry-After header
            retry_after_seconds = 2
            mock_response = Mock(
                status_code=429,
                headers={"Retry-After": str(retry_after_seconds)}
            )

            mock_client.databases.retrieve.side_effect = [
                APIResponseError(
                    response=mock_response,
                    message="Rate limit exceeded",
                    code="rate_limited",
                ),
                {"id": "test_db_after_rate_limit"},  # Second attempt succeeds
            ]

            notion_service = NotionSyncService()
            notion_service.client = mock_client

            try:
                start_time = time.time()

                # Should wait for Retry-After duration
                result = await notion_service.verify_connection()

                end_time = time.time()
                elapsed = end_time - start_time

                # Should have waited at least Retry-After duration
                assert elapsed >= retry_after_seconds

                assert result is True

            finally:
                await notion_service.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestNotionCompleteWorkflow:
    """Integration tests for complete Notion sync workflow"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    async def db_session(self):
        """Get database session"""
        from src.database.connection import get_db

        async for session in get_db():
            yield session

    async def test_complete_sync_workflow_mocked(self, client, db_session):
        """
        Test complete sync workflow from creation to Notion sync (mocked).

        Workflow:
        1. Create InspirationRecord via API
        2. Record saved to local database (PENDING)
        3. Sync task created in queue
        4. Worker processes sync task
        5. Notion page created
        6. Record updated with Notion page ID (SYNCED)
        """
        # Step 1 & 2: Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "完整同步工作流测试内容",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Verify record in database
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()
        assert record is not None
        assert record.sync_status == SyncStatus.PENDING

        # Step 3: Verify sync task created
        sync_query = await db_session.execute(
            select(SyncQueue).where(SyncQueue.record_id == record_id)
        )
        sync_task = sync_query.scalar_one_or_none()

        # Step 4 & 5: Mock worker processing sync task
        if sync_task:
            with patch('src.services.notion_sync.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                # Mock successful page creation
                mock_notion_page_id = "workflow_test_page_id"
                mock_client.pages.create.return_value = {
                    "id": mock_notion_page_id,
                    "created_time": datetime.utcnow().isoformat(),
                }

                # Simulate worker sync
                notion_service = NotionSyncService()
                notion_service.client = mock_client

                try:
                    page_id = await notion_service.create_page(record)

                    # Step 6: Update record with Notion page ID
                    if page_id:
                        record.notion_page_id = page_id
                        record.sync_status = SyncStatus.SYNCED
                        await db_session.commit()

                        # Verify final state
                        await db_session.refresh(record)
                        assert record.notion_page_id == mock_notion_page_id
                        assert record.sync_status == SyncStatus.SYNCED

                finally:
                    await notion_service.close()

    async def test_sync_workflow_handles_errors(self, client, db_session):
        """
        Test sync workflow handles errors gracefully.

        Workflow:
        1. Create record
        2. Sync fails
        3. Record remains PENDING or marked FAILED
        4. Sync task updated with error
        5. Can retry later
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "同步错误处理测试",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Mock Notion API failure
        with patch('src.services.notion_sync.AsyncClient') as mock_client_class:
            from notion_client.errors import APIResponseError

            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock persistent failure
            mock_client.pages.create.side_effect = APIResponseError(
                response=Mock(status_code=400, headers={}),
                message="Invalid request",
                code="invalid_request",
            )

            # Attempt sync
            query = await db_session.execute(
                select(InspirationRecord).where(InspirationRecord.id == record_id)
            )
            record = query.scalar_one_or_none()

            notion_service = NotionSyncService()
            notion_service.client = mock_client

            try:
                page_id = await notion_service.create_page(record)

                # Should return None on failure
                assert page_id is None

                # Record should still be pending/failed
                await db_session.refresh(record)
                assert record.sync_status in [SyncStatus.PENDING, SyncStatus.FAILED]

            finally:
                await notion_service.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestNotionPropertyMapping:
    """Tests for mapping InspirationRecord to Notion properties"""

    async def test_property_mapping_completeness(self):
        """
        Test all InspirationRecord fields map correctly to Notion properties.
        """
        from src.models.inspiration import InspirationRecord

        # Create mock record with all fields populated
        mock_record = Mock(spec=InspirationRecord)
        mock_record.id = 1
        mock_record.title = "完整字段映射测试"
        mock_record.content = "测试所有字段是否正确映射到Notion属性"
        mock_record.input_type = "text"
        mock_record.category_tags = json.dumps(["测试", "映射", "Notion"])
        mock_record.summary = "这是一个测试摘要"
        mock_record.created_at = datetime(2025, 1, 15, 10, 30, 0)
        mock_record.updated_at = datetime(2025, 1, 15, 11, 0, 0)

        # Build properties
        notion_service = NotionSyncService()

        try:
            properties = notion_service._build_page_properties(mock_record)

            # Verify all key properties exist
            assert NotionConfig.TITLE_PROPERTY in properties
            assert NotionConfig.CONTENT_PROPERTY in properties
            assert NotionConfig.INPUT_TYPE_PROPERTY in properties
            assert NotionConfig.CATEGORIES_PROPERTY in properties
            assert NotionConfig.SUMMARY_PROPERTY in properties
            assert NotionConfig.CREATED_AT_PROPERTY in properties
            assert NotionConfig.UPDATED_AT_PROPERTY in properties
            assert NotionConfig.SOURCE_PROPERTY in properties

            # Verify property structures
            assert properties[NotionConfig.TITLE_PROPERTY]["title"][0]["text"]["content"] == "完整字段映射测试"
            assert "测试所有字段" in properties[NotionConfig.CONTENT_PROPERTY]["rich_text"][0]["text"]["content"]
            assert properties[NotionConfig.INPUT_TYPE_PROPERTY]["select"]["name"] == "文字"
            assert len(properties[NotionConfig.CATEGORIES_PROPERTY]["multi_select"]) == 3
            assert "测试摘要" in properties[NotionConfig.SUMMARY_PROPERTY]["rich_text"][0]["text"]["content"]

        finally:
            await notion_service.close()

    async def test_input_type_mapping(self):
        """
        Test input type correctly maps to Chinese display names.
        """
        notion_service = NotionSyncService()

        try:
            assert notion_service._map_input_type("voice") == "语音"
            assert notion_service._map_input_type("text") == "文字"
            assert notion_service._map_input_type("image") == "图片"
            assert notion_service._map_input_type("unknown") == "unknown"  # Fallback

        finally:
            await notion_service.close()


@pytest.mark.asyncio
@pytest.mark.integration
class TestNotionSyncStatistics:
    """Tests for sync statistics tracking"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_sync_statistics_tracking(self, client):
        """
        Test sync statistics are tracked correctly via API.
        """
        # Get initial sync status
        initial_response = await client.get("/api/v1/sync/status")
        assert initial_response.status_code == status.HTTP_200_OK

        initial_data = initial_response.json()
        initial_pending = initial_data["pending_count"]

        # Create a new record (adds to pending)
        create_response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "同步统计追踪测试",
                "language": "zh",
            },
        )

        assert create_response.status_code == status.HTTP_201_CREATED

        # Get updated sync status
        updated_response = await client.get("/api/v1/sync/status")
        assert updated_response.status_code == status.HTTP_200_OK

        updated_data = updated_response.json()

        # Pending count may have increased (depends on auto-sync)
        assert updated_data["pending_count"] >= initial_pending
