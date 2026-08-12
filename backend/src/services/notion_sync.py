"""
Notion API Client Service

Handles synchronization of inspiration records with Notion database,
including rate limiting, retry logic, and error handling.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

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

from src.models.inspiration import InspirationRecord
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
    TITLE_PROPERTY = "总结"
    CONTENT_PROPERTY = "内容"
    INPUT_TYPE_PROPERTY = "输入方式"
    SUMMARY_PROPERTY = "摘要"
    CREATED_AT_PROPERTY = "创建日期"
    SOURCE_PROPERTY = "来源"

    PROPERTY_TYPES = {
        CONTENT_PROPERTY: "rich_text",
        INPUT_TYPE_PROPERTY: "select",
        SUMMARY_PROPERTY: "rich_text",
        CREATED_AT_PROPERTY: "date",
        SOURCE_PROPERTY: "select",
    }


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

    _schema_ready_databases: set[str] = set()

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

    async def ensure_database_schema(self) -> bool:
        """Reconcile the target Notion database to the six public columns."""
        if self.database_id in self._schema_ready_databases:
            return True

        async def retrieve_operation():
            return await self.client.databases.retrieve(database_id=self.database_id)

        try:
            database = await self._retry_with_backoff(
                operation_name="retrieve_database_schema",
                operation_func=retrieve_operation,
            )
            properties = database.get("properties", {})
            title_name = next(
                (
                    name
                    for name, definition in properties.items()
                    if definition.get("type") == "title"
                ),
                None,
            )
            if not title_name:
                logger.error("notion_title_property_missing")
                return False

            desired_names = {
                NotionConfig.TITLE_PROPERTY,
                *NotionConfig.PROPERTY_TYPES.keys(),
            }
            delete_updates: Dict[str, Any] = {}
            recreate_names: set[str] = set()

            for name, definition in properties.items():
                property_type = definition.get("type")
                if property_type == "title":
                    continue
                expected_type = NotionConfig.PROPERTY_TYPES.get(name)
                if name not in desired_names:
                    delete_updates[name] = None
                elif expected_type != property_type:
                    delete_updates[name] = None
                    recreate_names.add(name)

            if delete_updates:
                async def delete_operation():
                    return await self.client.databases.update(
                        database_id=self.database_id,
                        properties=delete_updates,
                    )

                await self._retry_with_backoff(
                    operation_name="remove_extra_database_properties",
                    operation_func=delete_operation,
                )

            if title_name != NotionConfig.TITLE_PROPERTY:
                async def rename_title_operation():
                    return await self.client.databases.update(
                        database_id=self.database_id,
                        properties={
                            title_name: {"name": NotionConfig.TITLE_PROPERTY}
                        },
                    )

                await self._retry_with_backoff(
                    operation_name="rename_database_title_property",
                    operation_func=rename_title_operation,
                )

            create_updates: Dict[str, Any] = {}
            for name, property_type in NotionConfig.PROPERTY_TYPES.items():
                if name not in properties or name in recreate_names:
                    create_updates[name] = {property_type: {}}

            if create_updates:
                async def create_operation():
                    return await self.client.databases.update(
                        database_id=self.database_id,
                        properties=create_updates,
                    )

                await self._retry_with_backoff(
                    operation_name="create_required_database_properties",
                    operation_func=create_operation,
                )

            self._schema_ready_databases.add(self.database_id)
            logger.info(
                "notion_database_schema_reconciled",
                database_id=self.database_id,
                properties=sorted(desired_names),
            )
            return True
        except APIResponseError as e:
            logger.error(
                "notion_database_schema_reconcile_failed",
                database_id=self.database_id,
                status_code=e.status,
                error=str(e),
            )
            return False

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

        The public database shape is limited to six fields.

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
            # Source marker
            NotionConfig.SOURCE_PROPERTY: {
                "select": {"name": record.source or "灵感记录器"}
            },
            # Empty rich_text clears a previous abstract during updates.
            NotionConfig.SUMMARY_PROPERTY: {
                "rich_text": (
                    [{"text": {"content": record.summary[:2000]}}]
                    if record.summary
                    else []
                )
            },
        }

        return properties

    def _map_input_type(self, input_type: str) -> str:
        """Map input type to Chinese display names"""
        mapping = {
            "voice": "语音",
            "text": "文字",
            "image": "图片",
            "pdf": "PDF",
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

        if not await self.ensure_database_schema():
            return None

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

        if not await self.ensure_database_schema():
            return False

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

    async def is_page_archived_or_missing(self, notion_page_id: str) -> bool:
        """
        Check whether a Notion page was deleted/archived from Notion.

        Notion exposes user-facing deletion as page archival/trash. If the page
        can no longer be retrieved, treat it as deleted so local state can be
        cleaned up by the background worker.
        """
        logger.debug(
            "checking_notion_page_deleted_state",
            notion_page_id=notion_page_id,
        )

        try:
            await self._rate_limit()
            page = await self.client.pages.retrieve(page_id=notion_page_id)
        except APIResponseError as e:
            if e.status == 404 or getattr(e, "code", None) == "object_not_found":
                logger.info(
                    "notion_page_missing",
                    notion_page_id=notion_page_id,
                    status_code=e.status,
                )
                return True

            logger.warning(
                "notion_page_deleted_state_check_failed",
                notion_page_id=notion_page_id,
                error=str(e),
                status_code=e.status,
            )
            return False

        archived = bool(page.get("archived") or page.get("in_trash"))
        if archived:
            logger.info(
                "notion_page_archived_or_in_trash",
                notion_page_id=notion_page_id,
            )
        return archived

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
