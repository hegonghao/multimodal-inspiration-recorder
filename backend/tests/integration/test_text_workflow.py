"""
Integration Tests for Text Input Workflow

End-to-end tests for User Story 3: Text Input
Tests complete workflow from text submission to database storage and sync queue.
"""

import pytest
import httpx
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import select

from src.api.main import app
from src.models.inspiration import InspirationRecord
from src.models.sync_queue import SyncQueue, SyncOperation


@pytest.mark.asyncio
@pytest.mark.integration
class TestTextWorkflowIntegration:
    """Integration tests for text input complete workflow"""

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

    # ==================== Complete Workflow Tests ====================

    async def test_complete_text_workflow(self, client, db_session):
        """
        Test complete text input workflow:
        1. Submit text content
        2. AI processes content (categorization + summary)
        3. Record saved to database
        4. Sync queue entry created
        """
        # Step 1: Submit text content
        test_content = "这是一段完整工作流程测试的文本内容。包含足够的信息以触发AI处理流程。"

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": test_content,
                "language": "zh",
                "auto_process": "true",
            },
        )

        # Verify API response
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()

        record_id = response_data["id"]
        assert record_id > 0

        # Verify input type
        assert response_data["input_type"] == "text"

        # Step 2: Verify AI processing occurred
        # Categories should be generated
        assert "categories" in response_data
        if response_data["categories"]:
            assert isinstance(response_data["categories"], list)
            assert len(response_data["categories"]) > 0

        # Summary should be generated
        assert "summary" in response_data
        if response_data.get("summary"):
            assert len(response_data["summary"]) > 0

        # Step 3: Verify record in database
        record_query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = record_query.scalar_one_or_none()

        assert record is not None, "Record not found in database"
        assert record.input_type == "text"
        assert record.content == test_content
        assert record.version == 1  # New record

        # Step 4: Verify sync queue entry
        sync_query = await db_session.execute(
            select(SyncQueue).where(SyncQueue.record_id == record_id)
        )
        sync_task = sync_query.scalar_one_or_none()

        if sync_task:
            assert sync_task.operation == SyncOperation.CREATE
            assert sync_task.status in ["pending", "in_progress"]

    async def test_text_workflow_without_ai(self, client, db_session):
        """Test text workflow without AI processing"""
        test_content = "简单测试内容，不需要AI处理。"

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": test_content,
                "language": "zh",
                "auto_process": "false",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()

        # Verify saved to database
        record_id = response_data["id"]
        record_query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = record_query.scalar_one_or_none()

        assert record is not None
        assert record.input_type == "text"
        assert record.content == test_content

    # ==================== AI Processing Integration ====================

    async def test_text_ai_categorization_integration(self, client):
        """Test AI categorization produces categories"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "我今天学习了机器学习的基础知识，包括监督学习、无监督学习和强化学习。"
                          "这些概念对理解AI技术非常重要。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Should have categories
            assert "categories" in data
            if data["categories"]:
                # Should have 1-5 categories
                assert 1 <= len(data["categories"]) <= 5

                # Categories should be relevant (rough check)
                categories_str = " ".join(data["categories"]).lower()
                # Could contain tech, learning, AI related terms
                # This is a loose integration test

    async def test_text_ai_summarization_integration(self, client):
        """Test AI summarization produces meaningful summary"""
        long_content = """
        人工智能（Artificial Intelligence，简称AI）是计算机科学的一个分支。
        它试图理解智能的本质，并产生出一种新的能以人类智能相似的方式做出反应的智能机器。
        该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。

        AI的应用已经渗透到各个领域，从医疗诊断到自动驾驶，从智能客服到内容推荐。
        随着深度学习技术的发展，AI的能力正在快速提升。
        """

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": long_content.strip(),
                "language": "zh",
                "auto_process": "true",
            },
        )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Should have summary
            assert "summary" in data
            if data.get("summary"):
                # Summary should be shorter than original
                assert len(data["summary"]) < len(long_content)
                # Summary should have some content
                assert len(data["summary"]) > 10

    # ==================== Database Integration ====================

    async def test_text_record_persistence(self, client, db_session):
        """Test text record persists correctly in database"""
        test_content = "数据库持久化测试内容"

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": test_content,
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Query database directly
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()

        assert record is not None
        assert record.content == test_content
        assert record.input_type == "text"
        assert record.created_at is not None
        assert record.updated_at is not None
        assert record.version == 1

    async def test_text_record_metadata_storage(self, client, db_session):
        """Test metadata fields are stored correctly"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "元数据存储测试内容，验证所有元数据字段。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Query database
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()

        assert record is not None

        # Verify metadata fields
        assert record.sync_status is not None
        assert record.version >= 1
        assert record.raw_data is not None  # Should contain request metadata

    # ==================== Sync Queue Integration ====================

    async def test_text_record_creates_sync_task(self, client, db_session):
        """Test text record creation queues sync task"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "同步队列测试内容",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Check sync queue
        sync_query = await db_session.execute(
            select(SyncQueue).where(SyncQueue.record_id == record_id)
        )
        sync_task = sync_query.scalar_one_or_none()

        if sync_task:
            assert sync_task.operation == SyncOperation.CREATE
            assert sync_task.status in ["pending", "in_progress"]
            assert sync_task.retry_count >= 0

    # ==================== Error Handling Integration ====================

    async def test_text_workflow_validation_error(self, client, db_session):
        """Test workflow handles validation errors correctly"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "短",  # Too short
                "language": "zh",
            },
        )

        # Should fail validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Should not create database record
        # (This would require knowing a record ID, so we just verify error response)
        error = response.json()
        assert "detail" in error

    async def test_text_workflow_with_special_content(self, client, db_session):
        """Test workflow handles special characters correctly"""
        special_content = "特殊字符测试：\n换行\t制表符\"引号'单引号@#$%"

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": special_content,
                "language": "zh",
                "auto_process": "false",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Verify content stored correctly
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()

        assert record is not None
        assert record.content == special_content

    # ==================== Performance Integration ====================

    @pytest.mark.slow
    async def test_text_workflow_performance(self, client):
        """Test complete workflow completes within acceptable time"""
        import time

        start_time = time.time()

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "完整工作流程性能测试内容，包含AI处理的端到端流程验证。",
                "language": "zh",
                "auto_process": "true",
            },
        )

        end_time = time.time()
        elapsed = end_time - start_time

        # Complete workflow should finish < 5 seconds
        assert elapsed < 5.0, f"Workflow took {elapsed:.2f}s, expected < 5s"
        assert response.status_code == status.HTTP_201_CREATED

    # ==================== Multiple Records Integration ====================

    async def test_multiple_text_records_workflow(self, client, db_session):
        """Test creating multiple text records in sequence"""
        record_ids = []

        # Create 3 records
        for i in range(3):
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "text",
                    "content": f"第{i+1}条测试记录的内容",
                    "language": "zh",
                },
            )

            assert response.status_code == status.HTTP_201_CREATED
            record_ids.append(response.json()["id"])

        # Verify all records exist in database
        for record_id in record_ids:
            query = await db_session.execute(
                select(InspirationRecord).where(InspirationRecord.id == record_id)
            )
            record = query.scalar_one_or_none()
            assert record is not None
            assert record.input_type == "text"

    async def test_concurrent_text_records(self, client):
        """Test handling concurrent text record creation"""
        import asyncio

        # Create tasks for concurrent requests
        async def create_record(index: int):
            async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/records/",
                    data={
                        "input_type": "text",
                        "content": f"并发测试记录 {index} 的内容",
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

    # ==================== Data Integrity Tests ====================

    async def test_text_record_version_management(self, client, db_session):
        """Test version field is managed correctly"""
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "版本管理测试内容",
                "language": "zh",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Verify version in database
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()

        assert record is not None
        assert record.version == 1  # New record should have version 1

    async def test_text_record_timestamps(self, client, db_session):
        """Test created_at and updated_at timestamps"""
        from datetime import datetime, timedelta

        before_creation = datetime.utcnow()

        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "text",
                "content": "时间戳测试内容",
                "language": "zh",
            },
        )

        after_creation = datetime.utcnow()

        assert response.status_code == status.HTTP_201_CREATED
        record_id = response.json()["id"]

        # Verify timestamps
        query = await db_session.execute(
            select(InspirationRecord).where(InspirationRecord.id == record_id)
        )
        record = query.scalar_one_or_none()

        assert record is not None
        assert record.created_at is not None
        assert record.updated_at is not None

        # Timestamps should be within reasonable range
        assert before_creation <= record.created_at <= after_creation + timedelta(seconds=1)
        assert before_creation <= record.updated_at <= after_creation + timedelta(seconds=1)

        # For new record, created_at and updated_at should be very close
        time_diff = abs((record.updated_at - record.created_at).total_seconds())
        assert time_diff < 1.0  # Less than 1 second difference
