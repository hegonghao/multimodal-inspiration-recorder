"""
Usage Analytics Service
用户行为分析服务

This module implements Constitution Principle VII (Data-Driven Iteration)
by tracking user behavior, feature usage, and performance metrics.

Success Criteria Tracking:
- SC-001: Task completion rates (90% target)
- SC-002: Issue frequency (50% reduction target)
- SC-003: Task completion time (40% reduction target)
- SC-004: User satisfaction (4.0/5.0 target)
- SC-005: UI responsiveness (<1s target)
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.orm import selectinload

from src.core.logging_config import get_logger
from src.models.inspiration import InspirationRecord, SyncStatus
from src.database.connection import get_db

logger = get_logger(__name__)


class EventType(str, Enum):
    """Analytics event types"""
    # User actions
    APP_LAUNCHED = "app_launched"
    VOICE_INPUT_STARTED = "voice_input_started"
    VOICE_INPUT_COMPLETED = "voice_input_completed"
    IMAGE_INPUT_STARTED = "image_input_started"
    IMAGE_INPUT_COMPLETED = "image_input_completed"
    TEXT_INPUT_STARTED = "text_input_started"
    TEXT_INPUT_COMPLETED = "text_input_completed"

    # Task completion
    RECORD_CREATED = "record_created"
    RECORD_VIEWED = "record_viewed"
    RECORD_EDITED = "record_edited"
    RECORD_DELETED = "record_deleted"

    # Sync events
    SYNC_TRIGGERED = "sync_triggered"
    SYNC_COMPLETED = "sync_completed"
    SYNC_FAILED = "sync_failed"

    # Performance events
    API_RESPONSE = "api_response"
    UI_ACTION_FEEDBACK = "ui_action_feedback"
    STT_PROCESSING = "stt_processing"
    OCR_PROCESSING = "ocr_processing"
    AI_CLASSIFICATION = "ai_classification"

    # Error events
    ERROR_OCCURRED = "error_occurred"
    ISSUE_REPORTED = "issue_reported"

    # User feedback
    SATISFACTION_RATING = "satisfaction_rating"
    FEEDBACK_SUBMITTED = "feedback_submitted"


class UsageAnalyticsService:
    """
    Service for tracking user behavior and application metrics

    Supports Constitution Principle VII by collecting data for:
    1. Feature usage patterns
    2. Task completion rates and times
    3. Performance metrics
    4. User satisfaction
    5. Issue frequency
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def track_event(
        self,
        event_type: EventType,
        user_id: int = 1,  # Single-user mode
        record_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Track an analytics event

        Args:
            event_type: Type of event
            user_id: User identifier (always 1 in single-user mode)
            record_id: Related record ID if applicable
            metadata: Additional event data (duration, error details, etc.)

        Example:
            >>> await analytics.track_event(
            ...     EventType.VOICE_INPUT_COMPLETED,
            ...     record_id=123,
            ...     metadata={"duration_seconds": 15.3, "file_size_mb": 1.2}
            ... )
        """
        try:
            # In production, this would write to a dedicated analytics table
            # For MVP, we log events for analysis
            logger.info(
                "analytics_event",
                event_type=event_type.value,
                user_id=user_id,
                record_id=record_id,
                metadata=metadata or {},
                timestamp=datetime.utcnow().isoformat(),
            )
        except Exception as e:
            # Analytics should never break app functionality
            logger.error("analytics_tracking_failed", error=str(e), exc_info=True)

    async def track_task_completion(
        self,
        input_type: str,
        duration_seconds: float,
        success: bool = True,
        record_id: Optional[int] = None,
    ) -> None:
        """
        Track task completion for SC-003 (task completion time)

        Args:
            input_type: Input method used (voice/image/text)
            duration_seconds: Time from input start to record saved
            success: Whether task completed successfully
            record_id: Created record ID

        Target: 40% faster than baseline (60s → 36s)
        """
        await self.track_event(
            EventType.RECORD_CREATED if success else EventType.ERROR_OCCURRED,
            record_id=record_id,
            metadata={
                "input_type": input_type,
                "duration_seconds": duration_seconds,
                "success": success,
                "target_duration": 36.0,  # 40% reduction from 60s baseline
            }
        )

    async def track_ui_response(
        self,
        action: str,
        response_time_ms: int,
    ) -> None:
        """
        Track UI responsiveness for SC-005 (<1s feedback requirement)

        Args:
            action: UI action performed (button_tap, navigation, etc.)
            response_time_ms: Time from action to visual feedback

        Target: <1000ms for all actions
        """
        await self.track_event(
            EventType.UI_ACTION_FEEDBACK,
            metadata={
                "action": action,
                "response_time_ms": response_time_ms,
                "target_ms": 1000,
                "meets_target": response_time_ms < 1000,
            }
        )

    async def track_performance_metric(
        self,
        operation: str,
        duration_ms: int,
        target_ms: int,
        success: bool = True,
    ) -> None:
        """
        Track performance metrics for various operations

        Args:
            operation: Operation type (stt, ocr, ai_classification)
            duration_ms: Operation duration
            target_ms: Target duration from requirements
            success: Whether operation succeeded
        """
        await self.track_event(
            EventType.API_RESPONSE,
            metadata={
                "operation": operation,
                "duration_ms": duration_ms,
                "target_ms": target_ms,
                "meets_target": duration_ms < target_ms,
                "success": success,
            }
        )

    async def track_user_satisfaction(
        self,
        rating: int,
        feedback_text: Optional[str] = None,
        days_since_first_use: int = 0,
    ) -> None:
        """
        Track user satisfaction for SC-004 (4.0/5.0 target)

        Args:
            rating: User rating (1-5)
            feedback_text: Optional feedback text
            days_since_first_use: Days user has been using app

        Target: 4.0/5.0 average rating (minimum 20 responses)
        """
        await self.track_event(
            EventType.SATISFACTION_RATING,
            metadata={
                "rating": rating,
                "feedback": feedback_text,
                "days_since_first_use": days_since_first_use,
                "target_rating": 4.0,
            }
        )

    async def track_issue_report(
        self,
        issue_type: str,
        severity: str,
        description: str,
    ) -> None:
        """
        Track user-reported issues for SC-002 (50% reduction target)

        Args:
            issue_type: Category of issue (bug, performance, usability)
            severity: Severity level (low, medium, high, critical)
            description: Issue description
        """
        await self.track_event(
            EventType.ISSUE_REPORTED,
            metadata={
                "issue_type": issue_type,
                "severity": severity,
                "description": description,
            }
        )

    async def get_feature_usage_stats(
        self,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get feature usage statistics

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with usage statistics:
            - total_records: Total records created
            - voice_records: Voice input count
            - image_records: Image input count
            - text_records: Text input count
            - daily_average: Average records per day
            - most_used_input: Most frequently used input type
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Query records created in the time period
            result = await self.db.execute(
                select(
                    func.count(InspirationRecord.id).label("total"),
                    func.sum(
                        case((InspirationRecord.input_type == "voice", 1), else_=0)
                    ).label("voice_count"),
                    func.sum(
                        case((InspirationRecord.input_type == "image", 1), else_=0)
                    ).label("image_count"),
                    func.sum(
                        case((InspirationRecord.input_type == "text", 1), else_=0)
                    ).label("text_count"),
                ).where(InspirationRecord.created_at >= cutoff_date)
            )

            row = result.one()

            total = row.total or 0
            voice_count = row.voice_count or 0
            image_count = row.image_count or 0
            text_count = row.text_count or 0

            # Determine most used input type
            input_counts = {
                "voice": voice_count,
                "image": image_count,
                "text": text_count,
            }
            most_used = max(input_counts, key=input_counts.get) if total > 0 else None

            stats = {
                "period_days": days,
                "total_records": total,
                "voice_records": voice_count,
                "image_records": image_count,
                "text_records": text_count,
                "daily_average": round(total / days, 2) if days > 0 else 0,
                "most_used_input": most_used,
                "voice_percentage": round((voice_count / total * 100), 1) if total > 0 else 0,
                "image_percentage": round((image_count / total * 100), 1) if total > 0 else 0,
                "text_percentage": round((text_count / total * 100), 1) if total > 0 else 0,
            }

            logger.info("feature_usage_calculated", stats=stats)
            return stats

        except Exception as e:
            logger.error("feature_usage_stats_failed", error=str(e), exc_info=True)
            return {
                "error": str(e),
                "period_days": days,
                "total_records": 0,
            }

    async def get_sync_performance_stats(
        self,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get synchronization performance statistics

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with sync statistics:
            - total_records: Total records
            - synced_count: Successfully synced records
            - pending_count: Pending sync records
            - failed_count: Failed sync records
            - sync_success_rate: Percentage of successful syncs
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            result = await self.db.execute(
                select(
                    func.count(InspirationRecord.id).label("total"),
                    func.sum(
                        case((InspirationRecord.sync_status == SyncStatus.SYNCED.value, 1), else_=0)
                    ).label("synced"),
                    func.sum(
                        case((InspirationRecord.sync_status == SyncStatus.PENDING.value, 1), else_=0)
                    ).label("pending"),
                    func.sum(
                        case((InspirationRecord.sync_status == SyncStatus.FAILED.value, 1), else_=0)
                    ).label("failed"),
                ).where(InspirationRecord.created_at >= cutoff_date)
            )

            row = result.one()

            total = row.total or 0
            synced = row.synced or 0
            pending = row.pending or 0
            failed = row.failed or 0

            success_rate = round((synced / total * 100), 1) if total > 0 else 0

            stats = {
                "period_days": days,
                "total_records": total,
                "synced_count": synced,
                "pending_count": pending,
                "failed_count": failed,
                "sync_success_rate": success_rate,
            }

            logger.info("sync_performance_calculated", stats=stats)
            return stats

        except Exception as e:
            logger.error("sync_performance_stats_failed", error=str(e), exc_info=True)
            return {
                "error": str(e),
                "period_days": days,
                "total_records": 0,
            }

    async def get_constitution_compliance_report(self) -> Dict[str, Any]:
        """
        Generate compliance report for Constitution Principles

        Returns:
            Dictionary with compliance metrics:
            - sc_001_task_completion_rate: % users completing first task in 5 min
            - sc_003_avg_task_time: Average task completion time
            - sc_004_avg_satisfaction: Average user satisfaction rating
            - sc_005_ui_responsiveness: % actions with <1s feedback

        Note: This is a simplified MVP implementation.
        Production would track individual user sessions and calculate
        actual metrics based on collected analytics events.
        """
        try:
            # SC-003: Task completion time (target: <36s)
            usage_stats = await self.get_feature_usage_stats(days=7)

            # SC-004: User satisfaction (target: 4.0/5.0)
            # In production, this would query satisfaction ratings from analytics table
            # For MVP, we estimate based on system health
            sync_stats = await self.get_sync_performance_stats(days=7)

            # Calculate estimated satisfaction based on system performance
            # High sync success rate correlates with user satisfaction
            estimated_satisfaction = 3.0 + (sync_stats.get("sync_success_rate", 0) / 100)

            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "period_days": 7,

                # SC-001: Task completion rate
                # Target: 90% of users complete first task in <5 minutes
                "sc_001_task_completion_rate": {
                    "target": 90.0,
                    "current": None,  # Requires client-side analytics
                    "status": "pending_client_implementation",
                    "note": "Tracked via Flutter app analytics",
                },

                # SC-003: Task completion time
                # Target: 40% reduction from baseline (60s → 36s)
                "sc_003_task_completion_time": {
                    "target_seconds": 36.0,
                    "baseline_seconds": 60.0,
                    "current_seconds": None,  # Requires event timing data
                    "status": "pending_analytics_data",
                    "note": "Tracked via track_task_completion() events",
                },

                # SC-004: User satisfaction
                # Target: 4.0/5.0 average (minimum 20 responses)
                "sc_004_user_satisfaction": {
                    "target_rating": 4.0,
                    "minimum_responses": 20,
                    "estimated_rating": round(estimated_satisfaction, 2),
                    "status": "estimated",
                    "note": "Actual ratings collected via track_user_satisfaction()",
                },

                # SC-005: UI responsiveness
                # Target: <1000ms for all actions
                "sc_005_ui_responsiveness": {
                    "target_ms": 1000,
                    "current_ms": None,  # Requires client-side tracking
                    "status": "pending_client_implementation",
                    "note": "Tracked via track_ui_response() events",
                },

                # Feature usage summary
                "feature_usage": usage_stats,

                # Sync performance summary
                "sync_performance": sync_stats,
            }

            logger.info("constitution_compliance_report_generated", report=report)
            return report

        except Exception as e:
            logger.error("compliance_report_failed", error=str(e), exc_info=True)
            return {
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat(),
            }


def get_analytics_service(db: AsyncSession) -> UsageAnalyticsService:
    """
    Get analytics service instance

    Args:
        db: Database session (required)

    Returns:
        Configured analytics service instance

    Example:
        >>> async for db in get_db():
        ...     analytics = get_analytics_service(db)
        ...     stats = await analytics.get_feature_usage_stats()
    """
    return UsageAnalyticsService(db)
