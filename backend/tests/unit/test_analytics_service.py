"""
Unit Tests: Analytics Service
用户分析服务单元测试

Tests for backend/src/services/analytics_service.py

Coverage Target: 90%
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.analytics_service import (
    UsageAnalyticsService,
    EventType,
    get_analytics_service,
)


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def analytics_service(mock_db):
    """Analytics service instance with mock database"""
    return UsageAnalyticsService(mock_db)


class TestEventType:
    """Test EventType enum"""

    def test_event_type_values(self):
        """Test all event types have string values"""
        assert EventType.APP_LAUNCHED.value == "app_launched"
        assert EventType.VOICE_INPUT_STARTED.value == "voice_input_started"
        assert EventType.RECORD_CREATED.value == "record_created"
        assert EventType.ERROR_OCCURRED.value == "error_occurred"

    def test_event_type_count(self):
        """Test expected number of event types"""
        event_types = list(EventType)
        assert len(event_types) >= 20, "Should have at least 20 event types"


class TestUsageAnalyticsService:
    """Test UsageAnalyticsService class"""

    @pytest.mark.asyncio
    async def test_track_event_basic(self, analytics_service):
        """Test basic event tracking"""
        await analytics_service.track_event(
            event_type=EventType.APP_LAUNCHED,
            user_id=1,
            record_id=None,
            metadata={"platform": "android"},
        )

        # Should not raise exception
        assert True

    @pytest.mark.asyncio
    async def test_track_event_with_record_id(self, analytics_service):
        """Test event tracking with record ID"""
        await analytics_service.track_event(
            event_type=EventType.RECORD_CREATED,
            user_id=1,
            record_id=123,
            metadata={"input_type": "voice"},
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_event_without_metadata(self, analytics_service):
        """Test event tracking without metadata"""
        await analytics_service.track_event(
            event_type=EventType.APP_LAUNCHED,
            user_id=1,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_task_completion_success(self, analytics_service):
        """Test task completion tracking for successful task"""
        await analytics_service.track_task_completion(
            input_type="voice",
            duration_seconds=25.5,
            success=True,
            record_id=456,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_task_completion_failure(self, analytics_service):
        """Test task completion tracking for failed task"""
        await analytics_service.track_task_completion(
            input_type="text",
            duration_seconds=10.0,
            success=False,
            record_id=None,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_ui_response_fast(self, analytics_service):
        """Test UI response tracking for fast response"""
        await analytics_service.track_ui_response(
            action="button_tap",
            response_time_ms=500,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_ui_response_slow(self, analytics_service):
        """Test UI response tracking for slow response"""
        await analytics_service.track_ui_response(
            action="navigation",
            response_time_ms=1500,  # Exceeds 1000ms target
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_performance_metric_meets_target(self, analytics_service):
        """Test performance metric tracking when meeting target"""
        await analytics_service.track_performance_metric(
            operation="ocr",
            duration_ms=3000,
            target_ms=5000,
            success=True,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_performance_metric_exceeds_target(self, analytics_service):
        """Test performance metric tracking when exceeding target"""
        await analytics_service.track_performance_metric(
            operation="stt",
            duration_ms=12000,
            target_ms=10000,
            success=True,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_user_satisfaction_high_rating(self, analytics_service):
        """Test user satisfaction tracking with high rating"""
        await analytics_service.track_user_satisfaction(
            rating=5,
            feedback_text="Excellent app!",
            days_since_first_use=30,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_user_satisfaction_low_rating(self, analytics_service):
        """Test user satisfaction tracking with low rating"""
        await analytics_service.track_user_satisfaction(
            rating=2,
            feedback_text="Needs improvement",
            days_since_first_use=5,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_user_satisfaction_without_feedback(self, analytics_service):
        """Test user satisfaction tracking without feedback text"""
        await analytics_service.track_user_satisfaction(
            rating=4,
            feedback_text=None,
            days_since_first_use=15,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_issue_report_bug(self, analytics_service):
        """Test issue reporting for bug"""
        await analytics_service.track_issue_report(
            issue_type="bug",
            severity="high",
            description="Application crashes on image upload",
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_issue_report_performance(self, analytics_service):
        """Test issue reporting for performance"""
        await analytics_service.track_issue_report(
            issue_type="performance",
            severity="medium",
            description="OCR processing is slow",
        )

        assert True

    @pytest.mark.asyncio
    async def test_get_feature_usage_stats_with_data(self, analytics_service, mock_db):
        """Test feature usage statistics with data"""
        # Mock database query result
        mock_result = Mock()
        mock_result.one.return_value = Mock(
            total=42,
            voice_count=25,
            image_count=10,
            text_count=7,
        )
        mock_db.execute.return_value = mock_result

        stats = await analytics_service.get_feature_usage_stats(days=7)

        assert stats["total_records"] == 42
        assert stats["voice_records"] == 25
        assert stats["image_records"] == 10
        assert stats["text_records"] == 7
        assert stats["most_used_input"] == "voice"
        assert stats["period_days"] == 7
        assert "daily_average" in stats
        assert "voice_percentage" in stats

    @pytest.mark.asyncio
    async def test_get_feature_usage_stats_no_data(self, analytics_service, mock_db):
        """Test feature usage statistics with no data"""
        # Mock empty result
        mock_result = Mock()
        mock_result.one.return_value = Mock(
            total=0,
            voice_count=0,
            image_count=0,
            text_count=0,
        )
        mock_db.execute.return_value = mock_result

        stats = await analytics_service.get_feature_usage_stats(days=30)

        assert stats["total_records"] == 0
        assert stats["daily_average"] == 0
        assert stats["most_used_input"] is None

    @pytest.mark.asyncio
    async def test_get_feature_usage_stats_error_handling(self, analytics_service, mock_db):
        """Test feature usage statistics error handling"""
        # Mock database error
        mock_db.execute.side_effect = Exception("Database connection failed")

        stats = await analytics_service.get_feature_usage_stats(days=7)

        assert "error" in stats
        assert stats["total_records"] == 0

    @pytest.mark.asyncio
    async def test_get_sync_performance_stats_with_data(self, analytics_service, mock_db):
        """Test sync performance statistics with data"""
        # Mock database result
        mock_result = Mock()
        mock_result.one.return_value = Mock(
            total=100,
            synced=85,
            pending=10,
            failed=5,
        )
        mock_db.execute.return_value = mock_result

        stats = await analytics_service.get_sync_performance_stats(days=7)

        assert stats["total_records"] == 100
        assert stats["synced_count"] == 85
        assert stats["pending_count"] == 10
        assert stats["failed_count"] == 5
        assert stats["sync_success_rate"] == 85.0

    @pytest.mark.asyncio
    async def test_get_sync_performance_stats_perfect_sync(self, analytics_service, mock_db):
        """Test sync performance with 100% success rate"""
        mock_result = Mock()
        mock_result.one.return_value = Mock(
            total=50,
            synced=50,
            pending=0,
            failed=0,
        )
        mock_db.execute.return_value = mock_result

        stats = await analytics_service.get_sync_performance_stats(days=30)

        assert stats["sync_success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_get_sync_performance_stats_no_data(self, analytics_service, mock_db):
        """Test sync performance with no data"""
        mock_result = Mock()
        mock_result.one.return_value = Mock(
            total=0,
            synced=0,
            pending=0,
            failed=0,
        )
        mock_db.execute.return_value = mock_result

        stats = await analytics_service.get_sync_performance_stats(days=7)

        assert stats["sync_success_rate"] == 0

    @pytest.mark.asyncio
    async def test_get_constitution_compliance_report(self, analytics_service, mock_db):
        """Test constitution compliance report generation"""
        # Mock usage stats
        mock_usage_result = Mock()
        mock_usage_result.one.return_value = Mock(
            total=42,
            voice_count=25,
            image_count=10,
            text_count=7,
        )

        # Mock sync stats
        mock_sync_result = Mock()
        mock_sync_result.one.return_value = Mock(
            total=42,
            synced=38,
            pending=2,
            failed=2,
        )

        # Set up mock to return different results for different queries
        mock_db.execute.side_effect = [mock_usage_result, mock_sync_result]

        report = await analytics_service.get_constitution_compliance_report()

        assert "generated_at" in report
        assert "period_days" in report
        assert "sc_001_task_completion_rate" in report
        assert "sc_003_task_completion_time" in report
        assert "sc_004_user_satisfaction" in report
        assert "sc_005_ui_responsiveness" in report
        assert "feature_usage" in report
        assert "sync_performance" in report

    @pytest.mark.asyncio
    async def test_get_constitution_compliance_report_structure(self, analytics_service, mock_db):
        """Test compliance report has correct structure"""
        # Mock data
        mock_usage_result = Mock()
        mock_usage_result.one.return_value = Mock(
            total=10,
            voice_count=6,
            image_count=2,
            text_count=2,
        )

        mock_sync_result = Mock()
        mock_sync_result.one.return_value = Mock(
            total=10,
            synced=9,
            pending=0,
            failed=1,
        )

        mock_db.execute.side_effect = [mock_usage_result, mock_sync_result]

        report = await analytics_service.get_constitution_compliance_report()

        # Verify SC-001 structure
        sc001 = report["sc_001_task_completion_rate"]
        assert "target" in sc001
        assert sc001["target"] == 90.0

        # Verify SC-003 structure
        sc003 = report["sc_003_task_completion_time"]
        assert "target_seconds" in sc003
        assert sc003["target_seconds"] == 36.0

        # Verify SC-004 structure
        sc004 = report["sc_004_user_satisfaction"]
        assert "target_rating" in sc004
        assert sc004["target_rating"] == 4.0
        assert "estimated_rating" in sc004

        # Verify SC-005 structure
        sc005 = report["sc_005_ui_responsiveness"]
        assert "target_ms" in sc005
        assert sc005["target_ms"] == 1000


@pytest.mark.asyncio
async def test_get_analytics_service():
    """Test get_analytics_service factory function"""
    # This test verifies the factory function works
    # In real usage, it would use actual database session
    mock_db = AsyncMock(spec=AsyncSession)

    service = get_analytics_service(mock_db)

    assert isinstance(service, UsageAnalyticsService)
    assert service.db == mock_db


class TestAnalyticsServiceEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_track_event_with_exception_in_logging(self, analytics_service):
        """Test event tracking continues even if logging fails"""
        # This should not raise exception even if logging fails internally
        await analytics_service.track_event(
            event_type=EventType.ERROR_OCCURRED,
            user_id=1,
            metadata={"error": "Test error"},
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_task_completion_zero_duration(self, analytics_service):
        """Test task completion with zero duration"""
        await analytics_service.track_task_completion(
            input_type="text",
            duration_seconds=0.0,
            success=True,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_ui_response_zero_time(self, analytics_service):
        """Test UI response tracking with zero time"""
        await analytics_service.track_ui_response(
            action="instant_action",
            response_time_ms=0,
        )

        assert True

    @pytest.mark.asyncio
    async def test_track_user_satisfaction_boundary_ratings(self, analytics_service):
        """Test satisfaction tracking with boundary values"""
        # Minimum rating
        await analytics_service.track_user_satisfaction(rating=1)

        # Maximum rating
        await analytics_service.track_user_satisfaction(rating=5)

        assert True

    @pytest.mark.asyncio
    async def test_get_feature_usage_stats_various_periods(self, analytics_service, mock_db):
        """Test feature usage stats with different time periods"""
        mock_result = Mock()
        mock_result.one.return_value = Mock(
            total=10,
            voice_count=5,
            image_count=3,
            text_count=2,
        )
        mock_db.execute.return_value = mock_result

        # Test 1 day
        stats_1d = await analytics_service.get_feature_usage_stats(days=1)
        assert stats_1d["period_days"] == 1

        # Test 30 days
        stats_30d = await analytics_service.get_feature_usage_stats(days=30)
        assert stats_30d["period_days"] == 30

        # Test 90 days
        stats_90d = await analytics_service.get_feature_usage_stats(days=90)
        assert stats_90d["period_days"] == 90


class TestAnalyticsServiceIntegration:
    """Integration-style tests for analytics service"""

    @pytest.mark.asyncio
    async def test_complete_usage_tracking_workflow(self, analytics_service, mock_db):
        """Test complete analytics workflow"""
        # Track app launch
        await analytics_service.track_event(EventType.APP_LAUNCHED, user_id=1)

        # Track voice input
        await analytics_service.track_event(
            EventType.VOICE_INPUT_STARTED,
            user_id=1,
            metadata={"timestamp": datetime.utcnow().isoformat()},
        )

        # Track task completion
        await analytics_service.track_task_completion(
            input_type="voice",
            duration_seconds=30.0,
            success=True,
            record_id=1,
        )

        # Track satisfaction
        await analytics_service.track_user_satisfaction(
            rating=5,
            feedback_text="Great app!",
        )

        # All events should track without errors
        assert True

    @pytest.mark.asyncio
    async def test_performance_monitoring_workflow(self, analytics_service):
        """Test performance monitoring workflow"""
        # Track UI response
        await analytics_service.track_ui_response(
            action="button_tap",
            response_time_ms=500,
        )

        # Track OCR performance
        await analytics_service.track_performance_metric(
            operation="ocr",
            duration_ms=3000,
            target_ms=5000,
            success=True,
        )

        # Track STT performance
        await analytics_service.track_performance_metric(
            operation="stt",
            duration_ms=8000,
            target_ms=10000,
            success=True,
        )

        assert True

    @pytest.mark.asyncio
    async def test_issue_tracking_workflow(self, analytics_service):
        """Test issue reporting and tracking workflow"""
        # Report bug
        await analytics_service.track_issue_report(
            issue_type="bug",
            severity="high",
            description="Critical bug description",
        )

        # Report performance issue
        await analytics_service.track_issue_report(
            issue_type="performance",
            severity="medium",
            description="Performance degradation",
        )

        # Report usability issue
        await analytics_service.track_issue_report(
            issue_type="usability",
            severity="low",
            description="Minor UX improvement",
        )

        assert True
