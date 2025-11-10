"""
Analytics API Endpoints
分析和监控API端点

Constitution Principle VII (Data-Driven Iteration) Implementation

Provides endpoints for:
- T086: Performance monitoring dashboard
- Feature usage statistics
- Success criteria tracking
- Constitution compliance reporting
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db
from src.services.analytics_service import UsageAnalyticsService, EventType
from src.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/usage", response_model=Dict[str, Any])
async def get_usage_statistics(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get feature usage statistics

    **Purpose**: Monitor feature adoption and usage patterns (Constitution Principle VII)

    **Query Parameters**:
    - days: Number of days to analyze (1-90, default: 7)

    **Returns**:
    - total_records: Total records created
    - voice_records: Voice input count
    - image_records: Image input count
    - text_records: Text input count
    - daily_average: Average records per day
    - most_used_input: Most frequently used input type
    - Percentage breakdown by input type

    **Example Response**:
    ```json
    {
      "period_days": 7,
      "total_records": 42,
      "voice_records": 25,
      "image_records": 10,
      "text_records": 7,
      "daily_average": 6.0,
      "most_used_input": "voice",
      "voice_percentage": 59.5,
      "image_percentage": 23.8,
      "text_percentage": 16.7
    }
    ```
    """
    analytics = UsageAnalyticsService(db)
    stats = await analytics.get_feature_usage_stats(days=days)
    return stats


@router.get("/sync-performance", response_model=Dict[str, Any])
async def get_sync_performance(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get synchronization performance statistics

    **Purpose**: Monitor Notion sync reliability

    **Query Parameters**:
    - days: Number of days to analyze (1-90, default: 7)

    **Returns**:
    - total_records: Total records in period
    - synced_count: Successfully synced records
    - pending_count: Pending sync records
    - failed_count: Failed sync records
    - sync_success_rate: Percentage of successful syncs

    **Example Response**:
    ```json
    {
      "period_days": 7,
      "total_records": 42,
      "synced_count": 38,
      "pending_count": 2,
      "failed_count": 2,
      "sync_success_rate": 90.5
    }
    ```
    """
    analytics = UsageAnalyticsService(db)
    stats = await analytics.get_sync_performance_stats(days=days)
    return stats


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_performance_dashboard(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive performance monitoring dashboard

    **Purpose**: T086 - Performance monitoring dashboard for key metrics

    **Provides**:
    - Feature usage patterns
    - Sync performance metrics
    - Constitution compliance report
    - System health indicators

    **Query Parameters**:
    - days: Number of days to analyze (1-90, default: 7)

    **Example Response**:
    ```json
    {
      "generated_at": "2025-10-28T10:30:00Z",
      "period_days": 7,
      "usage_stats": {
        "total_records": 42,
        "voice_records": 25,
        "most_used_input": "voice"
      },
      "sync_stats": {
        "sync_success_rate": 90.5
      },
      "health": {
        "overall_status": "healthy",
        "active_users": 1
      }
    }
    ```
    """
    analytics = UsageAnalyticsService(db)

    # Gather all metrics
    usage_stats = await analytics.get_feature_usage_stats(days=days)
    sync_stats = await analytics.get_sync_performance_stats(days=days)

    # Calculate overall system health
    total_records = usage_stats.get("total_records", 0)
    sync_success_rate = sync_stats.get("sync_success_rate", 0)

    # Health status based on activity and sync performance
    if total_records == 0:
        health_status = "inactive"
    elif sync_success_rate >= 95:
        health_status = "excellent"
    elif sync_success_rate >= 85:
        health_status = "good"
    elif sync_success_rate >= 70:
        health_status = "fair"
    else:
        health_status = "needs_attention"

    dashboard = {
        "generated_at": usage_stats.get("generated_at", ""),
        "period_days": days,
        "usage_stats": usage_stats,
        "sync_stats": sync_stats,
        "health": {
            "overall_status": health_status,
            "total_records_created": total_records,
            "daily_average": usage_stats.get("daily_average", 0),
            "sync_reliability": sync_success_rate,
            "active_users": 1,  # Single-user mode
        },
        "recommendations": _generate_recommendations(usage_stats, sync_stats),
    }

    logger.info("performance_dashboard_accessed", period_days=days)
    return dashboard


@router.get("/constitution-compliance", response_model=Dict[str, Any])
async def get_constitution_compliance(
    db: AsyncSession = Depends(get_db),
):
    """
    Get Constitution Principle VII compliance report

    **Purpose**: Monitor adherence to success criteria defined in project constitution

    **Success Criteria Tracked**:
    - SC-001: Task completion rate (target: 90% in <5 min)
    - SC-003: Task completion time (target: <36s, 40% reduction)
    - SC-004: User satisfaction (target: 4.0/5.0)
    - SC-005: UI responsiveness (target: <1000ms)

    **Returns**:
    - Compliance status for each success criterion
    - Current metrics vs targets
    - Feature usage summary
    - Sync performance summary

    **Example Response**:
    ```json
    {
      "generated_at": "2025-10-28T10:30:00Z",
      "sc_003_task_completion_time": {
        "target_seconds": 36.0,
        "status": "pending_analytics_data"
      },
      "sc_004_user_satisfaction": {
        "target_rating": 4.0,
        "estimated_rating": 3.9,
        "status": "estimated"
      },
      "feature_usage": {...},
      "sync_performance": {...}
    }
    ```
    """
    analytics = UsageAnalyticsService(db)
    report = await analytics.get_constitution_compliance_report()

    logger.info("constitution_compliance_accessed")
    return report


@router.post("/track-satisfaction")
async def track_user_satisfaction(
    rating: int = Query(..., ge=1, le=5, description="Satisfaction rating (1-5)"),
    feedback: Optional[str] = Query(None, max_length=1000, description="Optional feedback text"),
    days_using: int = Query(default=0, ge=0, description="Days since first use"),
    db: AsyncSession = Depends(get_db),
):
    """
    Track user satisfaction rating

    **Purpose**: Collect data for SC-004 (User satisfaction target: 4.0/5.0)

    **Body Parameters**:
    - rating: User rating from 1-5 stars (required)
    - feedback: Optional feedback text (max 1000 chars)
    - days_using: Days since first use (default: 0)

    **Target**: 4.0/5.0 average rating (minimum 20 responses)

    **Example Response**:
    ```json
    {
      "success": true,
      "message": "感谢您的反馈！",
      "rating_submitted": 5,
      "target_rating": 4.0
    }
    ```
    """
    analytics = UsageAnalyticsService(db)

    await analytics.track_user_satisfaction(
        rating=rating,
        feedback_text=feedback,
        days_since_first_use=days_using,
    )

    return {
        "success": True,
        "message": "感谢您的反馈！您的意见对我们改进产品非常重要。",
        "rating_submitted": rating,
        "target_rating": 4.0,
        "note": "我们的目标是达到4.0/5.0的平均满意度",
    }


@router.post("/track-issue")
async def track_user_issue(
    issue_type: str = Query(..., description="Issue category (bug/performance/usability)"),
    severity: str = Query(default="medium", description="Severity (low/medium/high/critical)"),
    description: str = Query(..., min_length=10, max_length=1000, description="Issue description"),
    db: AsyncSession = Depends(get_db),
):
    """
    Track user-reported issue

    **Purpose**: Collect data for SC-002 (Issue frequency reduction target: 50%)

    **Query Parameters**:
    - issue_type: Category of issue (bug, performance, usability)
    - severity: Severity level (low, medium, high, critical)
    - description: Issue description (10-1000 chars)

    **Example Response**:
    ```json
    {
      "success": true,
      "message": "问题已记录，我们会尽快处理",
      "issue_id": "20251028-001",
      "target_reduction": "50%"
    }
    ```
    """
    analytics = UsageAnalyticsService(db)

    await analytics.track_issue_report(
        issue_type=issue_type,
        severity=severity,
        description=description,
    )

    # Generate issue ID based on timestamp
    from datetime import datetime
    issue_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    return {
        "success": True,
        "message": "问题已记录，感谢您的反馈！我们会尽快处理。",
        "issue_id": issue_id,
        "issue_type": issue_type,
        "severity": severity,
        "target_reduction": "50%",
        "note": "我们的目标是将问题频率减少50%",
    }


def _generate_recommendations(
    usage_stats: Dict[str, Any],
    sync_stats: Dict[str, Any],
) -> List[str]:
    """
    Generate recommendations based on analytics data

    Args:
        usage_stats: Feature usage statistics
        sync_stats: Sync performance statistics

    Returns:
        List of actionable recommendations
    """
    recommendations = []

    # Check activity level
    total_records = usage_stats.get("total_records", 0)
    if total_records == 0:
        recommendations.append("开始创建您的第一条灵感记录！语音、图片或文字输入都很简单。")
    elif total_records < 10:
        recommendations.append("继续记录灵感！您已经创建了第一批记录，尝试不同的输入方式体验完整功能。")

    # Check input type diversity
    voice_pct = usage_stats.get("voice_percentage", 0)
    image_pct = usage_stats.get("image_percentage", 0)
    text_pct = usage_stats.get("text_percentage", 0)

    if voice_pct > 80:
        recommendations.append("您主要使用语音输入。试试图片OCR功能，快速提取书籍或网页中的文字！")
    elif image_pct > 80:
        recommendations.append("您主要使用图片输入。语音输入可以让您边走边记录灵感！")
    elif text_pct > 80:
        recommendations.append("您主要使用文字输入。尝试语音输入，解放双手，更自然地记录想法！")

    # Check sync performance
    sync_rate = sync_stats.get("sync_success_rate", 0)
    failed_count = sync_stats.get("failed_count", 0)

    if sync_rate < 90 and failed_count > 0:
        recommendations.append(
            f"有{failed_count}条记录同步失败。检查Notion连接配置或点击'重试失败的同步'。"
        )
    elif sync_rate == 100 and total_records > 0:
        recommendations.append("所有记录已成功同步到Notion！您的灵感得到了妥善保护。")

    # Daily usage pattern
    daily_avg = usage_stats.get("daily_average", 0)
    if daily_avg < 1 and total_records > 0:
        recommendations.append("建议每天至少记录一条灵感，养成持续创作的习惯！")

    return recommendations if recommendations else ["系统运行正常，继续保持创作热情！"]
