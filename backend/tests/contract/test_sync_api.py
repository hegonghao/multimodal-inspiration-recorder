"""
Contract Tests for Sync API

Tests API contract compliance for sync endpoints.
Validates request/response schemas, status codes, and error handling.

Endpoints tested:
- GET /api/v1/sync/status
- POST /api/v1/sync/trigger
- GET /api/v1/sync/queue
- POST /api/v1/sync/retry-failed
- GET /api/v1/sync/tasks/{task_id}
- GET /api/v1/sync/tasks/record/{record_id}
"""

import pytest
import httpx
from httpx import AsyncClient
from fastapi import status

from src.api.main import app


@pytest.mark.asyncio
class TestSyncStatusAPI:
    """Contract tests for GET /api/v1/sync/status endpoint"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_get_sync_status_success(self, client):
        """Test successful sync status retrieval"""
        response = await client.get("/api/v1/sync/status")

        # Assert status code
        assert response.status_code == status.HTTP_200_OK

        # Assert response schema
        data = response.json()
        assert "total_records" in data
        assert "synced_count" in data
        assert "pending_count" in data
        assert "failed_count" in data
        assert "last_sync_at" in data or data.get("last_sync_at") is None
        assert "next_sync_at" in data or data.get("next_sync_at") is None
        assert "sync_enabled" in data

        # Assert types
        assert isinstance(data["total_records"], int)
        assert isinstance(data["synced_count"], int)
        assert isinstance(data["pending_count"], int)
        assert isinstance(data["failed_count"], int)
        assert isinstance(data["sync_enabled"], bool)

        # Assert counts are non-negative
        assert data["total_records"] >= 0
        assert data["synced_count"] >= 0
        assert data["pending_count"] >= 0
        assert data["failed_count"] >= 0

    async def test_get_sync_status_response_structure(self, client):
        """Test sync status response has complete structure"""
        response = await client.get("/api/v1/sync/status")

        if response.status_code == status.HTTP_200_OK:
            data = response.json()

            # Required fields
            required_fields = [
                "total_records",
                "synced_count",
                "pending_count",
                "failed_count",
                "last_sync_at",
                "next_sync_at",
                "sync_enabled",
            ]

            for field in required_fields:
                assert field in data, f"Missing required field: {field}"


@pytest.mark.asyncio
class TestSyncTriggerAPI:
    """Contract tests for POST /api/v1/sync/trigger endpoint"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_trigger_sync_success(self, client):
        """Test manual sync trigger succeeds"""
        response = await client.post("/api/v1/sync/trigger")

        # Assert status code (202 Accepted for async processing)
        assert response.status_code == status.HTTP_202_ACCEPTED

        # Assert response schema
        data = response.json()
        assert "status" in data
        assert "enqueued_count" in data
        # Accept both 'success' (when Notion configured) and 'disabled' (when not configured)
        assert data["status"] in ["success", "disabled"]

        # Assert types
        assert isinstance(data["enqueued_count"], int)

    async def test_trigger_sync_with_batch_size(self, client):
        """Test sync trigger with custom batch size"""
        response = await client.post(
            "/api/v1/sync/trigger",
            params={"batch_size": 10}
        )

        # Should accept batch_size parameter
        assert response.status_code == status.HTTP_202_ACCEPTED

        data = response.json()
        assert "enqueued_count" in data

    async def test_trigger_sync_invalid_batch_size(self, client):
        """Test sync trigger fails with invalid batch size"""
        # Test batch_size = 0 (below minimum)
        response = await client.post(
            "/api/v1/sync/trigger",
            params={"batch_size": 0}
        )

        # Should reject invalid batch_size
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_trigger_sync_batch_size_too_large(self, client):
        """Test sync trigger fails with batch size over limit"""
        # Test batch_size > 100 (above maximum)
        response = await client.post(
            "/api/v1/sync/trigger",
            params={"batch_size": 101}
        )

        # Should reject batch_size over limit
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_trigger_sync_response_structure(self, client):
        """Test trigger sync response has complete structure"""
        response = await client.post("/api/v1/sync/trigger")

        if response.status_code == status.HTTP_202_ACCEPTED:
            data = response.json()

            # Required fields
            required_fields = [
                "status",
                "enqueued_count",
            ]

            for field in required_fields:
                assert field in data, f"Missing required field: {field}"


@pytest.mark.asyncio
class TestSyncQueueAPI:
    """Contract tests for GET /api/v1/sync/queue endpoint"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_get_sync_queue_success(self, client):
        """Test successful sync queue retrieval"""
        response = await client.get("/api/v1/sync/queue")

        # Assert status code
        assert response.status_code == status.HTTP_200_OK

        # Assert response schema
        data = response.json()
        assert "tasks" in data
        assert "total_count" in data

        # Assert types
        assert isinstance(data["tasks"], list)
        assert isinstance(data["total_count"], int)
        assert data["total_count"] >= 0

    async def test_get_sync_queue_with_status_filter(self, client):
        """Test sync queue with status filter"""
        # Test each valid status value
        for status_value in [0, 1, 2, 3]:
            response = await client.get(
                "/api/v1/sync/queue",
                params={"status_filter": status_value}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "tasks" in data
            assert "total_count" in data

    async def test_get_sync_queue_with_limit(self, client):
        """Test sync queue with custom limit"""
        response = await client.get(
            "/api/v1/sync/queue",
            params={"limit": 10}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # If there are tasks, should not exceed limit
        if len(data["tasks"]) > 0:
            assert len(data["tasks"]) <= 10

    async def test_get_sync_queue_invalid_status(self, client):
        """Test sync queue fails with invalid status filter"""
        # Test status out of range (valid: 0-3)
        response = await client.get(
            "/api/v1/sync/queue",
            params={"status_filter": 5}
        )

        # Should reject invalid status
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_sync_queue_invalid_limit(self, client):
        """Test sync queue fails with invalid limit"""
        # Test limit = 0 (below minimum)
        response = await client.get(
            "/api/v1/sync/queue",
            params={"limit": 0}
        )

        # Should reject invalid limit
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_sync_queue_limit_too_large(self, client):
        """Test sync queue fails with limit over maximum"""
        # Test limit > 200 (above maximum)
        response = await client.get(
            "/api/v1/sync/queue",
            params={"limit": 201}
        )

        # Should reject limit over maximum
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_sync_queue_task_structure(self, client):
        """Test sync queue tasks have proper structure"""
        response = await client.get("/api/v1/sync/queue")

        if response.status_code == status.HTTP_200_OK:
            data = response.json()

            # If tasks exist, validate structure
            if len(data["tasks"]) > 0:
                task = data["tasks"][0]

                # Required task fields
                required_fields = [
                    "id",
                    "record_id",
                    "operation",
                    "status",
                    "retry_count",
                    "max_retries",
                    "priority",
                    "created_at",
                ]

                for field in required_fields:
                    assert field in task, f"Missing required field in task: {field}"

                # Type validations
                assert isinstance(task["id"], int)
                assert isinstance(task["record_id"], int)
                assert isinstance(task["operation"], str)
                assert isinstance(task["status"], int)
                assert isinstance(task["retry_count"], int)
                assert isinstance(task["max_retries"], int)
                assert isinstance(task["priority"], int)
                assert isinstance(task["created_at"], str)


@pytest.mark.asyncio
class TestSyncRetryFailedAPI:
    """Contract tests for POST /api/v1/sync/retry-failed endpoint"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_retry_failed_sync_success(self, client):
        """Test retry failed sync succeeds"""
        response = await client.post("/api/v1/sync/retry-failed")

        # Assert status code (202 Accepted for async processing)
        assert response.status_code == status.HTTP_202_ACCEPTED

        # Assert response schema
        data = response.json()
        assert "status" in data
        assert "reset_count" in data
        assert "message" in data
        assert data["status"] == "success"

        # Assert types
        assert isinstance(data["reset_count"], int)
        assert isinstance(data["message"], str)
        assert data["reset_count"] >= 0

    async def test_retry_failed_sync_response_structure(self, client):
        """Test retry failed sync response has complete structure"""
        response = await client.post("/api/v1/sync/retry-failed")

        if response.status_code == status.HTTP_202_ACCEPTED:
            data = response.json()

            # Required fields
            required_fields = [
                "status",
                "reset_count",
                "message",
            ]

            for field in required_fields:
                assert field in data, f"Missing required field: {field}"


@pytest.mark.asyncio
class TestSyncTaskDetailsAPI:
    """Contract tests for GET /api/v1/sync/tasks/{task_id} endpoint"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_get_sync_task_not_found(self, client):
        """Test get sync task returns 404 for non-existent task"""
        response = await client.get("/api/v1/sync/tasks/99999")

        # Should return 404 for non-existent task
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Assert error response structure (custom format: {error, message, timestamp})
        error = response.json()
        assert "error" in error or "message" in error or "detail" in error

    async def test_get_sync_task_invalid_id(self, client):
        """Test get sync task fails with invalid task ID"""
        response = await client.get("/api/v1/sync/tasks/invalid")

        # Should reject invalid task ID
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestSyncTasksByRecordAPI:
    """Contract tests for GET /api/v1/sync/tasks/record/{record_id} endpoint"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_get_sync_tasks_by_record_success(self, client):
        """Test get sync tasks by record ID returns list"""
        # Use record_id=1 (may or may not exist)
        response = await client.get("/api/v1/sync/tasks/record/1")

        # Should succeed (even if empty list)
        assert response.status_code == status.HTTP_200_OK

        # Assert response is list
        data = response.json()
        assert isinstance(data, list)

    async def test_get_sync_tasks_by_record_with_limit(self, client):
        """Test get sync tasks by record with custom limit"""
        response = await client.get(
            "/api/v1/sync/tasks/record/1",
            params={"limit": 5}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should not exceed limit
        assert len(data) <= 5

    async def test_get_sync_tasks_by_record_invalid_limit(self, client):
        """Test get sync tasks by record fails with invalid limit"""
        # Test limit = 0 (below minimum)
        response = await client.get(
            "/api/v1/sync/tasks/record/1",
            params={"limit": 0}
        )

        # Should reject invalid limit
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_sync_tasks_by_record_limit_too_large(self, client):
        """Test get sync tasks by record fails with limit over maximum"""
        # Test limit > 50 (above maximum)
        response = await client.get(
            "/api/v1/sync/tasks/record/1",
            params={"limit": 51}
        )

        # Should reject limit over maximum
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_sync_tasks_by_record_invalid_id(self, client):
        """Test get sync tasks by record fails with invalid record ID"""
        response = await client.get("/api/v1/sync/tasks/record/invalid")

        # Should reject invalid record ID
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_sync_tasks_by_record_structure(self, client):
        """Test sync tasks by record have proper structure"""
        response = await client.get("/api/v1/sync/tasks/record/1")

        if response.status_code == status.HTTP_200_OK:
            data = response.json()

            # If tasks exist, validate structure
            if len(data) > 0:
                task = data[0]

                # Required task fields
                required_fields = [
                    "id",
                    "record_id",
                    "operation",
                    "status",
                    "retry_count",
                    "max_retries",
                ]

                for field in required_fields:
                    assert field in task, f"Missing required field in task: {field}"


# ==================== Error Handling Tests ====================


@pytest.mark.asyncio
class TestSyncAPIErrorHandling:
    """Tests for sync API error handling"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_error_response_structure(self, client):
        """Test error responses have consistent structure"""
        # Trigger an error by requesting non-existent task
        response = await client.get("/api/v1/sync/tasks/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Verify error structure (custom format: {error, message, timestamp})
        error = response.json()
        # Accept both custom format and FastAPI default format
        assert "error" in error or "message" in error or "detail" in error

        # If custom format, verify structure
        if "error" in error:
            assert isinstance(error["error"], str)
            assert "message" in error
            assert isinstance(error["message"], str)


# ==================== Integration Schema Tests ====================


@pytest.mark.asyncio
class TestSyncAPIIntegration:
    """Integration tests for sync API workflow"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    async def test_sync_workflow_contract(self, client):
        """Test complete sync workflow maintains contract"""
        # 1. Check initial status
        status_response = await client.get("/api/v1/sync/status")
        assert status_response.status_code == status.HTTP_200_OK
        initial_status = status_response.json()

        # 2. Get queue
        queue_response = await client.get("/api/v1/sync/queue")
        assert queue_response.status_code == status.HTTP_200_OK
        queue_data = queue_response.json()
        assert "tasks" in queue_data
        assert "total_count" in queue_data

        # 3. Trigger sync
        trigger_response = await client.post("/api/v1/sync/trigger")
        assert trigger_response.status_code == status.HTTP_202_ACCEPTED
        trigger_data = trigger_response.json()
        assert "status" in trigger_data
        # Accept both 'success' (when Notion configured) and 'disabled' (when not configured)
        assert trigger_data["status"] in ["success", "disabled"]

        # 4. Check status again (may have changed)
        final_status_response = await client.get("/api/v1/sync/status")
        assert final_status_response.status_code == status.HTTP_200_OK

    async def test_sync_queue_filtering_contract(self, client):
        """Test sync queue filtering maintains contract"""
        # Test all valid status filters
        for status_value in [0, 1, 2, 3]:
            response = await client.get(
                "/api/v1/sync/queue",
                params={"status_filter": status_value, "limit": 50}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify response structure
            assert "tasks" in data
            assert "total_count" in data
            assert isinstance(data["tasks"], list)
            assert isinstance(data["total_count"], int)
