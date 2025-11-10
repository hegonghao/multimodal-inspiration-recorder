"""
Notion API Client Service

Handles synchronization of inspiration records with Notion database,
including rate limiting, retry logic, and error handling.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from notion_client import AsyncClient
from notion_client.errors import APIResponseError
from tenacity import (
    retry,
    retry_if_exception_type,
    wait_exponential,
    stop_after_attempt,
    before_sleep_log,
)
import structlog

from src.models.inspiration import InspirationRecord, SyncStatus
from src.config import settings

logger = structlog.get_logger(__name__)


# ==================== Notion API Configuration ====================


class NotionConfig:
    """Notion API configuration and constants"""

    # Rate limiting: 3 requests per second
    RATE_LIMIT_DELAY = 0.4  # 400ms between requests to stay under 3 req/s

    # Retry configuration
    RETRY_MIN_WAIT = 4  # Minimum 4 seconds
    RETRY_MAX_WAIT = 60  # Maximum 60 seconds
    MAX_RETRY_ATTEMPTS = 5

    # Default property names for Notion database
    TITLE_PROPERTY = "名称1"  # Matches user's database
    CONTENT_PROPERTY = "内容"
    INPUT_TYPE_PROPERTY = "输入方式"
    CATEGORIES_PROPERTY = "分类"
    TAGS_PROPERTY = "标签"
    SUMMARY_PROPERTY = "摘要"
    CREATED_AT_PROPERTY = "创建日期"  # Matches user's database
    UPDATED_AT_PROPERTY = "通知时间"  # Matches user's database
    SOURCE_PROPERTY = "来源"


# ==================== Notion API Client ====================


class NotionSyncService:
    """
    Service for synchronizing InspirationRecords with Notion database.

    Features:
    - Rate limiting compliance (3 req/s)
    - Exponential backoff retry with Retry-After header support
    - Rich property mapping (text, select, multi-select, date, etc.)
    - Error handling and logging
    """

    def __init__(
        self,
        notion_token: Optional[str] = None,
        database_id: Optional[str] = None,
    ):
        """
        Initialize Notion sync service.

        Args:
            notion_token: Notion API integration token
            database_id: Target Notion database ID
        """
        # Priority: parameter > NOTION_TOKEN (preferred) > NOTION_API_KEY (fallback)
        self.notion_token = (
            notion_token or
            getattr(settings, "NOTION_TOKEN", None) or
            getattr(settings, "NOTION_API_KEY", None)
        )
        self.database_id = database_id or getattr(
            settings, "NOTION_DATABASE_ID", None
        )

        if not self.notion_token:
            raise ValueError("Notion API token not provided in settings or parameters")

        if not self.database_id:
            raise ValueError("Notion database ID not provided in settings or parameters")

        self.client = AsyncClient(auth=self.notion_token)
        self.last_request_time = 0.0

    async def _rate_limit(self):
        """Apply rate limiting delay (3 req/s = 400ms between requests)"""
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < NotionConfig.RATE_LIMIT_DELAY:
            delay = NotionConfig.RATE_LIMIT_DELAY - time_since_last_request
            logger.debug(
                "rate_limit_delay",
                delay_seconds=delay,
                last_request=self.last_request_time,
            )
            await asyncio.sleep(delay)

        self.last_request_time = asyncio.get_event_loop().time()

    @retry(
        retry=retry_if_exception_type(APIResponseError),
        wait=wait_exponential(
            multiplier=1,
            min=NotionConfig.RETRY_MIN_WAIT,
            max=NotionConfig.RETRY_MAX_WAIT,
        ),
        stop=stop_after_attempt(NotionConfig.MAX_RETRY_ATTEMPTS),
        before_sleep=before_sleep_log(logger, logging.INFO),
    )
    async def _retry_with_backoff(self, operation_name: str, operation_func):
        """
        Execute Notion API operation with exponential backoff retry.

        Respects Retry-After header for 429 rate limit responses.

        Args:
            operation_name: Description of operation for logging
            operation_func: Async function to execute

        Returns:
            Result from operation_func

        Raises:
            APIResponseError: After max retries exceeded
        """
        try:
            await self._rate_limit()
            result = await operation_func()
            logger.info(
                "notion_api_success",
                operation=operation_name,
            )
            return result

        except APIResponseError as e:
            logger.warning(
                "notion_api_error",
                operation=operation_name,
                status_code=e.status,
                error_code=e.code,
                message=str(e),
            )

            # Handle 429 rate limit with Retry-After header
            if e.status == 429:
                retry_after = int(e.headers.get("Retry-After", 10))
                logger.info(
                    "rate_limit_hit",
                    retry_after_seconds=retry_after,
                    operation=operation_name,
                )
                await asyncio.sleep(retry_after)

            raise  # Re-raise for tenacity retry handling

    def _build_page_properties(
        self, record: InspirationRecord
    ) -> Dict[str, Any]:
        """
        Build Notion page properties from InspirationRecord.

        Maps InspirationRecord fields to Notion property types:
        - title: Title property
        - content: Rich text property
        - input_type: Select property
        - categories: Multi-select property
        - dates: Date properties

        Args:
            record: InspirationRecord to convert

        Returns:
            Dict of Notion page properties
        """
        properties = {
            # Title property (required)
            NotionConfig.TITLE_PROPERTY: {
                "title": [
                    {
                        "text": {"content": record.title[:100]}  # Notion title limit
                    }
                ]
            },
            # Content as rich text
            NotionConfig.CONTENT_PROPERTY: {
                "rich_text": [
                    {
                        "text": {
                            "content": record.content[:2000]  # Notion text limit
                        }
                    }
                ]
            },
            # Input type as select
            NotionConfig.INPUT_TYPE_PROPERTY: {
                "select": {"name": self._map_input_type(record.input_type)}
            },
            # Created date
            NotionConfig.CREATED_AT_PROPERTY: {
                "date": {"start": record.created_at.isoformat()}
            },
            # Updated date
            NotionConfig.UPDATED_AT_PROPERTY: {
                "date": {"start": record.updated_at.isoformat()}
            },
            # Source marker
            NotionConfig.SOURCE_PROPERTY: {
                "select": {"name": "灵感记录器"}
            },
        }

        # Add category tags as multi-select if available
        if record.category_tags:
            logger.info(
                "processing_category_tags",
                record_id=record.id,
                category_tags=record.category_tags[:100] if record.category_tags else None,
                category_tags_type=type(record.category_tags).__name__,
            )
            try:
                # Parse category_tags (stored as JSON string or comma-separated)
                if isinstance(record.category_tags, str):
                    # Try JSON first
                    try:
                        categories = json.loads(record.category_tags)
                        logger.info(
                            "parsed_category_tags_as_json",
                            record_id=record.id,
                            categories=categories,
                        )
                    except json.JSONDecodeError:
                        # Fall back to comma-separated
                        categories = [tag.strip() for tag in record.category_tags.split(',')]
                        logger.debug(
                            "parsed_category_tags_as_csv",
                            record_id=record.id,
                            categories=categories,
                        )
                elif isinstance(record.category_tags, list):
                    categories = record.category_tags
                    logger.debug(
                        "category_tags_already_list",
                        record_id=record.id,
                        categories=categories,
                    )
                else:
                    categories = []
                    logger.warning(
                        "category_tags_unexpected_type",
                        record_id=record.id,
                        type=type(record.category_tags).__name__,
                    )

                # Limit to 5 tags and create multi-select property
                if categories:
                    properties[NotionConfig.CATEGORIES_PROPERTY] = {
                        "multi_select": [
                            {"name": cat[:100]} for cat in categories[:5] if cat
                        ]
                    }
                    logger.info(
                        "added_category_tags_to_properties",
                        record_id=record.id,
                        categories_count=len(categories[:5]),
                        categories=categories[:5],
                    )
                else:
                    logger.warning(
                        "category_tags_empty_after_parse",
                        record_id=record.id,
                    )
            except Exception as e:
                logger.warning(
                    "failed_to_parse_category_tags",
                    record_id=record.id,
                    error=str(e),
                )

        # Add summary as rich text if available
        if record.summary:
            properties[NotionConfig.SUMMARY_PROPERTY] = {
                "rich_text": [
                    {
                        "text": {
                            "content": record.summary[:2000]
                        }
                    }
                ]
            }

        return properties

    def _map_input_type(self, input_type: str) -> str:
        """Map input type to Chinese display names"""
        mapping = {
            "voice": "语音",
            "text": "文字",
            "image": "图片",
        }
        return mapping.get(input_type, input_type)

    # ==================== Public API Methods ====================

    async def create_page(
        self, record: InspirationRecord
    ) -> Optional[str]:
        """
        Create a new page in Notion database from InspirationRecord.

        Args:
            record: InspirationRecord to sync to Notion

        Returns:
            Notion page ID if successful, None if failed

        Raises:
            APIResponseError: After max retries exceeded
        """
        logger.info(
            "creating_notion_page",
            record_id=record.id,
            title=record.title[:50],
        )

        properties = self._build_page_properties(record)

        async def create_operation():
            return await self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
            )

        try:
            response = await self._retry_with_backoff(
                operation_name=f"create_page_record_{record.id}",
                operation_func=create_operation,
            )

            page_id = response["id"]
            logger.info(
                "notion_page_created",
                record_id=record.id,
                notion_page_id=page_id,
            )
            return page_id

        except APIResponseError as e:
            logger.error(
                "notion_create_failed",
                record_id=record.id,
                error=str(e),
                status_code=e.status,
            )
            return None

    async def update_page(
        self, notion_page_id: str, record: InspirationRecord
    ) -> bool:
        """
        Update existing Notion page with InspirationRecord data.

        Args:
            notion_page_id: Notion page ID to update
            record: InspirationRecord with updated data

        Returns:
            True if update successful, False otherwise

        Raises:
            APIResponseError: After max retries exceeded
        """
        logger.info(
            "updating_notion_page",
            record_id=record.id,
            notion_page_id=notion_page_id,
        )

        properties = self._build_page_properties(record)

        async def update_operation():
            return await self.client.pages.update(
                page_id=notion_page_id,
                properties=properties,
            )

        try:
            await self._retry_with_backoff(
                operation_name=f"update_page_{notion_page_id}",
                operation_func=update_operation,
            )

            logger.info(
                "notion_page_updated",
                record_id=record.id,
                notion_page_id=notion_page_id,
            )
            return True

        except APIResponseError as e:
            logger.error(
                "notion_update_failed",
                record_id=record.id,
                notion_page_id=notion_page_id,
                error=str(e),
                status_code=e.status,
            )
            return False

    async def archive_page(self, notion_page_id: str) -> bool:
        """
        Archive (soft delete) a Notion page.

        Idempotent operation: if page is already archived, returns True.

        Args:
            notion_page_id: Notion page ID to archive

        Returns:
            True if archive successful or already archived, False otherwise

        Raises:
            APIResponseError: After max retries exceeded (non-idempotent errors)
        """
        logger.info(
            "archiving_notion_page",
            notion_page_id=notion_page_id,
        )

        # First, check if page is already archived to avoid API error
        try:
            async def get_page_operation():
                return await self.client.pages.retrieve(page_id=notion_page_id)

            page = await self._retry_with_backoff(
                operation_name=f"get_page_{notion_page_id}",
                operation_func=get_page_operation,
            )

            if page.get("archived", False):
                logger.info(
                    "notion_page_already_archived",
                    notion_page_id=notion_page_id,
                )
                return True

        except APIResponseError as e:
            logger.warning(
                "notion_page_retrieve_failed",
                notion_page_id=notion_page_id,
                error=str(e),
                status_code=e.status,
            )
            # Continue to attempt archive anyway

        # Attempt to archive the page
        async def archive_operation():
            return await self.client.pages.update(
                page_id=notion_page_id,
                archived=True,
            )

        try:
            await self._retry_with_backoff(
                operation_name=f"archive_page_{notion_page_id}",
                operation_func=archive_operation,
            )

            logger.info(
                "notion_page_archived",
                notion_page_id=notion_page_id,
            )
            return True

        except APIResponseError as e:
            # Handle idempotent case: page is already archived
            error_message = str(e).lower()
            if "archived" in error_message and ("can't edit" in error_message or "already" in error_message):
                logger.info(
                    "notion_page_already_archived_on_update",
                    notion_page_id=notion_page_id,
                    message="Page was archived between check and update",
                )
                return True

            # Non-idempotent error
            logger.error(
                "notion_archive_failed",
                notion_page_id=notion_page_id,
                error=str(e),
                status_code=e.status,
            )
            return False

    async def verify_connection(self) -> bool:
        """
        Verify Notion API connection and database access.

        Returns:
            True if connection successful, False otherwise
        """
        logger.info("verifying_notion_connection")

        async def verify_operation():
            # Test database retrieval
            return await self.client.databases.retrieve(
                database_id=self.database_id
            )

        try:
            response = await self._retry_with_backoff(
                operation_name="verify_connection",
                operation_func=verify_operation,
            )

            logger.info(
                "notion_connection_verified",
                database_id=self.database_id,
                database_title=response.get("title", [{}])[0]
                .get("text", {})
                .get("content", "Unknown"),
            )
            return True

        except APIResponseError as e:
            logger.error(
                "notion_connection_failed",
                database_id=self.database_id,
                error=str(e),
                status_code=e.status,
            )
            return False

    async def close(self):
        """Close Notion API client session"""
        await self.client.aclose()
        logger.info("notion_client_closed")


# ==================== Helper Functions ====================


async def get_notion_service() -> NotionSyncService:
    """
    Dependency injection for NotionSyncService.

    Returns:
        Configured NotionSyncService instance
    """
    return NotionSyncService()
