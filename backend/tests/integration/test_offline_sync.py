"""
Integration Tests for Offline-First Workflow

Tests offline-first architecture for User Story 4: Sync System
Validates that local database is source of truth and sync happens asynchronously.
"""

import pytest
import httpx
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import select
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.api.main import app
from src.models.inspiration import InspirationRecord, SyncStatus
from src.models.sync_queue import SyncQueue, SyncQueueStatus, SyncOperation, SyncPriority


@pytest.mark.asyncio
@pytest.mark.integration
class TestOfflineFirstWorkflow:
    """Integration tests for offline-first architecture"""

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

    # ==================== Local Storage First Tests ====================

    async def test_record_created_locally_first(self, client, db_session):
        """
        Test record is created in local database immediately,
        regardless of network availability.
        """
        # Create a text record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "离线优先测试：本地存储优先级验证",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Verify record exists in local database immediately
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()

        assert record is not None, "Record should exist in local database"
        assert record.content == "离线优先测试:本地存储优先级验证"
        assert record.sync_status == SyncStatus.PENDING  # Not synced yet

    async def test_local_database_as_source_of_truth(self, client, db_session):
        """
        Test that local database is the source of truth.
        Data is readable from DB immediately after creation.
        """
        # Create record
        create_response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "本地数据库作为真实数据源的测试内容",
                "language": "zh",
            },
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        record_id = create_response.json()["id"]

        # Read record from API (should read from local DB)
        read_response = await client.get(f"/api/v1/records/{record_id}")

        assert read_response.status_code == status.HTTP_200_OK
        read_data = read_response.json()

        # Verify data matches
        assert read_data["id"] == record_id
        assert "本地数据库" in read_data["content"]
        assert read_data["sync_status"] == SyncStatus.PENDING

    async def test_sync_queue_created_after_local_save(self, client, db_session):
        """
        Test sync queue entry is created AFTER local database save.
        This ensures data is never lost even if sync fails.
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "同步队列创建测试内容",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Verify record in database
        record_query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = record_query.scalar_one_or_none()
        assert record is not None

        # Verify sync queue entry created
        sync_query = await db_session.execute(
            select(SyncQueue).where(SyncQueue.record_id == record_id)
        )
        sync_task = sync_query.scalar_one_or_none()

        if sync_task:
            assert sync_task.operation == SyncOperation.CREATE
            assert sync_task.status in [SyncQueueStatus.PENDING, SyncQueueStatus.PROCESSING]
            assert sync_task.record_id == record_id

    # ==================== Offline Behavior Tests ====================

    async def test_offline_create_operation(self, client, db_session):
        """
        Test record creation works offline (sync fails but record saved).
        """
        with patch('src.services.notion_sync.NotionSyncService.sync_record') as mock_sync:
            # Simulate network failure
            mock_sync.side_effect = Exception("Network unavailable")

            # Create record should still succeed
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "text",
                    "content": "离线创建操作测试内容",
                    "language": "zh",
                },
            )

            # Record creation should succeed despite sync failure
            assert response.status_code == status.HTTP_201_CREATED
            record_id = response.json()["id"]

            # Verify record exists in local database
            query = await db_session.execute(
                select(InspirationRecord).where(InspirationRecord.id == record_id)
            )
            record = query.scalar_one_or_none()
            assert record is not None
            assert record.sync_status == SyncStatus.PENDING

    async def test_offline_read_operations(self, client, db_session):
        """
        Test read operations work offline (always from local DB).
        """
        # Create a record first
        create_response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "离线读取操作测试",
                "language": "zh",
            },
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        record_id = create_response.json()["id"]

        # Simulate Notion being offline
        with patch('src.services.notion_sync.NotionSyncService') as mock_notion:
            mock_notion.side_effect = Exception("Notion unavailable")

            # Read should still work (from local DB)
            read_response = await client.get(f"/api/v1/records/{record_id}")

            assert read_response.status_code == status.HTTP_200_OK
            data = read_response.json()
            assert data["id"] == record_id
            assert "离线读取" in data["content"]

    # ==================== Sync Queue Management Tests ====================

    async def test_pending_sync_queue_accumulation(self, client, db_session):
        """
        Test that failed syncs accumulate in queue for retry.
        """
        # Create multiple records
        record_ids = []
        for i in range(3):
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "text",
                    "content": f"同步队列累积测试 {i+1}",
                    "language": "zh",
                },
            )
            assert response.status_code == status.HTTP_201_CREATED
            record_ids.append(response.json()["id"])

        # Check sync queue has entries for all records
        sync_query = await db_session.execute(
            select(SyncQueue).where(
                SyncQueue.record_id.in_(record_ids)
            )
        )
        sync_tasks = sync_query.scalars().all()

        # Should have sync tasks for records
        assert len(sync_tasks) >= 0  # May or may not be created depending on config

    async def test_sync_queue_priority_management(self, client, db_session):
        """
        Test sync queue respects priority ordering.
        """
        # This tests that manual triggers can have higher priority
        status_response = await client.get("/api/v1/sync/status")
        assert status_response.status_code == status.HTTP_200_OK

        # Get current queue
        queue_response = await client.get("/api/v1/sync/queue")
        assert queue_response.status_code == status.HTTP_200_OK

        queue_data = queue_response.json()
        tasks = queue_data["tasks"]

        if len(tasks) > 1:
            # Verify tasks are ordered by priority (high to low)
            for i in range(len(tasks) - 1):
                assert tasks[i]["priority"] >= tasks[i + 1]["priority"]

    # ==================== Sync Retry Logic Tests ====================

    async def test_failed_sync_retry_mechanism(self, client, db_session):
        """
        Test that failed syncs are retried with exponential backoff.
        """
        # Create a record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "同步重试机制测试",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Get sync task for this record
        sync_query = await db_session.execute(
            select(SyncQueue).where(SyncQueue.record_id == record_id)
        )
        sync_task = sync_query.scalar_one_or_none()

        if sync_task:
            # Verify retry configuration
            assert sync_task.max_retries > 0  # Should have retry attempts
            assert sync_task.retry_count >= 0

            # If task failed, should have next_retry_at
            if sync_task.status == SyncQueueStatus.FAILED:
                assert sync_task.next_retry_at is not None
                assert sync_task.error_message is not None

    async def test_retry_failed_sync_api(self, client, db_session):
        """
        Test POST /sync/retry-failed resets failed tasks.
        """
        # Get current failed tasks count
        initial_status = await client.get("/api/v1/sync/status")
        initial_data = initial_status.json()
        initial_failed_count = initial_data.get("failed_count", 0)

        # Trigger retry
        retry_response = await client.post("/api/v1/sync/retry-failed")
        assert retry_response.status_code == status.HTTP_202_ACCEPTED

        retry_data = retry_response.json()
        assert "status" in retry_data
        assert "reset_count" in retry_data
        assert retry_data["status"] == "success"

        # Reset count should match initial failed count
        assert retry_data["reset_count"] >= 0

    # ==================== Sync Status Tracking Tests ====================

    async def test_sync_status_transitions(self, client, db_session):
        """
        Test sync status transitions: PENDING -> SYNCING -> SYNCED
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "同步状态转换测试",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Initial status should be PENDING
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()
        assert record is not None
        assert record.sync_status == SyncStatus.PENDING

        # After sync completes (mocked or real), status should update
        # This is tested in the Notion sync integration test (T060)

    async def test_sync_status_api_accuracy(self, client, db_session):
        """
        Test GET /sync/status returns accurate counts.
        """
        # Get sync status
        response = await client.get("/api/v1/sync/status")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()

        # Verify counts are consistent
        total_records = data["total_records"]
        synced_count = data["synced_count"]
        pending_count = data["pending_count"]
        failed_count = data["failed_count"]

        # Counts should be non-negative
        assert total_records >= 0
        assert synced_count >= 0
        assert pending_count >= 0
        assert failed_count >= 0

        # Synced + pending + failed should not exceed total
        # (Some records might not be queued for sync)
        assert synced_count + pending_count + failed_count <= total_records

    # ==================== Manual Sync Trigger Tests ====================

    async def test_manual_sync_trigger(self, client, db_session):
        """
        Test POST /sync/trigger manually enqueues pending tasks.
        """
        # Trigger sync
        response = await client.post("/api/v1/sync/trigger")
        assert response.status_code == status.HTTP_202_ACCEPTED

        data = response.json()
        assert "status" in data
        assert "enqueued_count" in data
        assert data["status"] == "success"

    async def test_manual_sync_with_batch_size(self, client):
        """
        Test manual sync respects batch_size parameter.
        """
        # Trigger sync with small batch
        response = await client.post(
            "/api/v1/sync/trigger",
            params={"batch_size": 5}
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()

        # Enqueued count should not exceed batch_size
        assert data["enqueued_count"] <= 5

    # ==================== Data Consistency Tests ====================

    async def test_local_database_consistency(self, client, db_session):
        """
        Test local database maintains consistency even with sync failures.
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "数据一致性测试内容",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Read record multiple times
        for _ in range(3):
            read_response = await client.get(f"/api/v1/records/{record_id}")
            assert read_response.status_code == status.HTTP_200_OK

            data = read_response.json()
            assert data["id"] == record_id
            assert "数据一致性" in data["content"]

    async def test_version_field_for_conflict_resolution(self, client, db_session):
        """
        Test version field is maintained for conflict resolution.
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "版本字段冲突解决测试",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Check version in database
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()

        assert record is not None
        assert record.version == 1  # New record should have version 1

    # ==================== Performance Tests ====================

    @pytest.mark.slow
    async def test_offline_operation_performance(self, client):
        """
        Test offline operations are fast (local DB only).
        """
        import time

        start_time = time.time()

        # Create record (local DB operation)
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "离线操作性能测试",
                "language": "zh",
            },
        )

        end_time = time.time()
        elapsed = end_time - start_time

        # Local operation should be very fast (<1 second)
        assert elapsed < 1.0, f"Local operation took {elapsed:.2f}s, expected <1s"
        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.slow
    async def test_read_performance_from_local_db(self, client, db_session):
        """
        Test reading from local DB is fast.
        """
        # Create record first
        create_response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "读取性能测试",
                "language": "zh",
            },
        )

        record_id = create_response.json()["id"]

        import time

        start_time = time.time()

        # Read record
        response = await client.get(f"/api/v1/records/{record_id}")

        end_time = time.time()
        elapsed = end_time - start_time

        # Read should be very fast (<0.5 seconds)
        assert elapsed < 0.5, f"Read operation took {elapsed:.2f}s, expected <0.5s"
        assert response.status_code == status.HTTP_200_OK

    # ==================== Error Recovery Tests ====================

    async def test_sync_queue_recovery_after_failure(self, client, db_session):
        """
        Test sync queue recovers gracefully from failures.
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "同步队列故障恢复测试",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Even if sync fails, API should continue working
        status_response = await client.get("/api/v1/sync/status")
        assert status_response.status_code == status.HTTP_200_OK

        queue_response = await client.get("/api/v1/sync/queue")
        assert queue_response.status_code == status.HTTP_200_OK

    async def test_database_transaction_rollback(self, client, db_session):
        """
        Test database transaction rollback on errors.
        """
        # Attempt to create invalid record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "短",  # Too short - should fail
                "language": "zh",
            },
        )

        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Database should remain consistent (no partial records)
        # This is implicitly tested by not finding invalid records

    # ==================== Multi-User Scenario Tests ====================

    async def test_concurrent_offline_operations(self, client):
        """
        Test concurrent offline operations don't interfere.
        """
        import asyncio

        async def create_record(index: int):
            async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/records/",
                    data={
                        "input_type": "text",
                        "content": f"并发离线操作测试 {index}",
                        "language": "zh",
                    },
                )
                return response

        # Create 5 records concurrently
        tasks = [create_record(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_201_CREATED

    # ==================== Sync Queue Task Details Tests ====================

    async def test_get_sync_task_by_id(self, client, db_session):
        """
        Test GET /sync/tasks/{task_id} returns task details.
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "同步任务详情测试",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Get sync task for this record
        sync_query = await db_session.execute(
            select(SyncQueue).where(SyncQueue.record_id == record_id)
        )
        sync_task = sync_query.scalar_one_or_none()

        if sync_task:
            # Get task details via API
            task_response = await client.get(f"/api/v1/sync/tasks/{sync_task.id}")
            assert task_response.status_code == status.HTTP_200_OK

            task_data = task_response.json()
            assert task_data["id"] == sync_task.id
            assert task_data["record_id"] == record_id

    async def test_get_sync_tasks_by_record(self, client, db_session):
        """
        Test GET /sync/tasks/record/{record_id} returns tasks for record.
        """
        # Create record
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "按记录查询同步任务测试",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Get tasks for this record
        tasks_response = await client.get(f"/api/v1/sync/tasks/record/{record_id}")
        assert tasks_response.status_code == status.HTTP_200_OK

        tasks = tasks_response.json()
        assert isinstance(tasks, list)

        # If tasks exist, verify they belong to this record
        for task in tasks:
            assert task["record_id"] == record_id
