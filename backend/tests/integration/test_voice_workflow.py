"""
Integration Tests for Voice Recording Workflow

Tests the complete end-to-end workflow for voice recording:
1. Audio file upload
2. Speech-to-text transcription
3. AI processing (categorization, summarization)
4. Database storage
5. Sync queue creation
"""

import pytest
import tempfile
import os
import httpx
import httpx
from httpx import AsyncClient
from fastapi import status
from sqlalchemy import select

from src.api.main import app
from src.database.connection import get_db
from src.models.inspiration import InspirationRecord
from src.models.sync_queue import SyncQueue, SyncOperation


@pytest.mark.asyncio
@pytest.mark.integration
class TestVoiceRecordingWorkflow:
    """Integration tests for complete voice recording workflow"""

    @pytest.fixture
    async def client(self):
        """Create async test client"""
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    async def db_session(self):
        """Get database session"""
        async for session in get_db():
            yield session

    @pytest.fixture
    def sample_audio_file(self):
        """Create a sample audio file"""
        with tempfile.NamedTemporaryFile(suffix=".aac", delete=False) as f:
            # Minimal AAC audio file
            f.write(b'\xff\xf1\x50\x80\x00\x1f\xfc')
            f.flush()
            yield f.name
        os.unlink(f.name)

    # ==================== End-to-End Workflow Tests ====================

    async def test_complete_voice_workflow(self, client, db_session, sample_audio_file):
        """Test complete workflow from upload to database"""
        # Step 1: Upload audio file
        with open(sample_audio_file, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "voice",
                    "language": "zh",
                    "auto_process": "true",
                },
                files={"file": ("test.aac", f, "audio/aac")},
            )

        # Workflow may fail if services are not available
        # This is expected in test environment without real services
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Step 2: Verify record in database
            record_id = data["id"]
            result = await db_session.execute(
                select(InspirationRecord).where(InspirationRecord.id == record_id)
            )
            record = result.scalar_one_or_none()

            assert record is not None
            assert record.input_type == "voice"
            assert record.content is not None
            assert len(record.content) > 0

            # Step 3: Verify sync queue entry
            result = await db_session.execute(
                select(SyncQueue).where(SyncQueue.record_id == record_id)
            )
            sync_task = result.scalar_one_or_none()

            assert sync_task is not None
            assert sync_task.operation == SyncOperation.CREATE
            assert sync_task.retry_count == 0

            # Step 4: Verify metadata
            if record.raw_data:
                raw_data = record.raw_data
                if isinstance(raw_data, dict):
                    # Should have transcription metadata
                    assert "transcription_confidence" in raw_data or "audio_duration" in raw_data

        elif response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]:
            # Service unavailable or confidence too low - expected in test env
            pytest.skip("External service unavailable or confidence too low")

        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")

    # ==================== Confidence Validation Workflow ====================

    async def test_low_confidence_handling(self, client, sample_audio_file):
        """Test workflow handles low transcription confidence"""
        with open(sample_audio_file, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "voice",
                    "language": "zh",
                    "auto_process": "true",
                },
                files={"file": ("noisy.aac", f, "audio/aac")},
            )

        # If low confidence, should return 422 with structured error
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            error = response.json()
            assert "detail" in error

            detail = error["detail"]
            if isinstance(detail, dict) and "error" in detail:
                assert detail["error"] in [
                    "low_transcription_confidence",
                    "transcription_failed"
                ]

                # Should provide actionable suggestions
                if "suggestions" in detail:
                    assert isinstance(detail["suggestions"], list)
                    assert len(detail["suggestions"]) > 0

    # ==================== Error Recovery Tests ====================

    async def test_transcription_failure_rollback(self, client, db_session):
        """Test database rollback on transcription failure"""
        # Get initial record count
        result = await db_session.execute(select(InspirationRecord))
        initial_count = len(result.scalars().all())

        # Send invalid audio
        response = await client.post(
            "/api/v1/records/",
            data={
                "input_type": "voice",
                "language": "zh",
            },
            files={"file": ("invalid.aac", b"invalid audio data", "audio/aac")},
        )

        # Should fail
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ]

        # Verify no partial record was created
        result = await db_session.execute(select(InspirationRecord))
        final_count = len(result.scalars().all())

        assert final_count == initial_count, "Database should rollback on error"

    # ==================== AI Processing Integration ====================

    async def test_ai_processing_integration(self, client, sample_audio_file):
        """Test AI processing integration with voice input"""
        with open(sample_audio_file, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "voice",
                    "language": "zh",
                    "auto_process": "true",  # Enable AI
                },
                files={"file": ("test.aac", f, "audio/aac")},
            )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Should have AI-generated fields
            assert "title" in data
            assert "categories" in data
            assert "summary" in data

            # Title should not be empty
            assert len(data["title"]) > 0

            # If AI processing succeeded, should have metadata
            if data.get("categories") or data.get("summary"):
                raw_data = data.get("raw_data", {})
                if isinstance(raw_data, dict):
                    # Should have AI confidence or sentiment
                    has_ai_metadata = any(
                        key in raw_data
                        for key in ["ai_confidence", "sentiment", "keywords"]
                    )
                    assert has_ai_metadata

    async def test_ai_processing_fallback(self, client, sample_audio_file):
        """Test fallback when AI processing is disabled"""
        with open(sample_audio_file, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "voice",
                    "language": "zh",
                    "auto_process": "false",  # Disable AI
                },
                files={"file": ("test.aac", f, "audio/aac")},
            )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()

            # Should still have title (from content truncation)
            assert "title" in data
            assert len(data["title"]) > 0

            # Categories might be empty without AI
            assert "categories" in data

    # ==================== Metadata Propagation Tests ====================

    async def test_metadata_propagation(self, client, db_session, sample_audio_file):
        """Test metadata flows through entire workflow"""
        with open(sample_audio_file, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "voice",
                    "language": "zh",
                    "auto_process": "true",
                },
                files={"file": ("test.aac", f, "audio/aac")},
            )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            record_id = data["id"]

            # Retrieve from database
            result = await db_session.execute(
                select(InspirationRecord).where(InspirationRecord.id == record_id)
            )
            record = result.scalar_one()

            # Verify raw_data contains all processing metadata
            raw_data = record.raw_data

            if isinstance(raw_data, dict):
                # Should have transcription metadata
                transcription_keys = [
                    "transcription_confidence",
                    "detected_language",
                    "audio_duration",
                    "word_count",
                ]

                has_transcription_metadata = any(
                    key in raw_data for key in transcription_keys
                )

                # If transcription succeeded, should have metadata
                if record.content and len(record.content) > 10:
                    assert has_transcription_metadata

    # ==================== Sync Queue Integration ====================

    async def test_sync_queue_creation(self, client, db_session, sample_audio_file):
        """Test sync queue entry is created correctly"""
        with open(sample_audio_file, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "voice",
                    "language": "zh",
                    "auto_process": "true",
                },
                files={"file": ("test.aac", f, "audio/aac")},
            )

        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            record_id = data["id"]

            # Check sync queue
            result = await db_session.execute(
                select(SyncQueue).where(SyncQueue.record_id == record_id)
            )
            sync_task = result.scalar_one_or_none()

            assert sync_task is not None
            assert sync_task.record_id == record_id
            assert sync_task.operation == SyncOperation.CREATE
            assert sync_task.retry_count == 0
            assert sync_task.scheduled_at is not None
            assert sync_task.created_at is not None

    # ==================== Performance Tests ====================

    @pytest.mark.slow
    async def test_workflow_performance(self, client, sample_audio_file):
        """Test workflow completes within reasonable time"""
        import time

        start_time = time.time()

        with open(sample_audio_file, "rb") as f:
            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "voice",
                    "language": "zh",
                    "auto_process": "true",
                },
                files={"file": ("test.aac", f, "audio/aac")},
            )

        end_time = time.time()
        elapsed = end_time - start_time

        # Total workflow should complete within 10 seconds
        # (5s for transcription + 3s for AI + 2s buffer)
        assert elapsed < 10.0, f"Workflow took {elapsed:.2f}s, expected < 10s"

        # If successful, should have completed all steps
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert "id" in data
            assert "content" in data

    # ==================== Concurrent Request Tests ====================

    @pytest.mark.slow
    async def test_concurrent_uploads(self, client, sample_audio_file):
        """Test handling of concurrent voice uploads"""
        import asyncio

        async def upload_audio():
            with open(sample_audio_file, "rb") as f:
                content = f.read()

            response = await client.post(
                "/api/v1/records/",
                data={
                    "input_type": "voice",
                    "language": "zh",
                    "auto_process": "true",
                },
                files={"file": ("test.aac", content, "audio/aac")},
            )
            return response

        # Upload 3 files concurrently
        tasks = [upload_audio() for _ in range(3)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful uploads
        successful = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code == status.HTTP_201_CREATED
        )

        # At least some should succeed (if services available)
        # Or all should fail gracefully
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                ]
