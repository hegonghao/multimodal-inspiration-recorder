import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
from notion_client.errors import APIErrorCode, APIResponseError

from src.services.notion_sync import NotionSyncService


def _notion_404_error() -> APIResponseError:
    request = httpx.Request("GET", "https://api.notion.com/v1/pages/page-1")
    response = httpx.Response(404, request=request)
    return APIResponseError(
        response=response,
        message="Could not find page",
        code=APIErrorCode.ObjectNotFound,
    )


class NotionSyncServiceTests(unittest.IsolatedAsyncioTestCase):
    def _service_with_page(self, page_or_error) -> NotionSyncService:
        service = NotionSyncService(notion_token="test-token", database_id="test-db")
        service._rate_limit = AsyncMock()
        service.client = SimpleNamespace(
            pages=SimpleNamespace(retrieve=AsyncMock(side_effect=page_or_error))
        )
        return service

    async def test_page_archived_is_deleted_state(self) -> None:
        service = self._service_with_page([{"archived": True}])

        deleted = await service.is_page_archived_or_missing("page-1")

        self.assertTrue(deleted)

    async def test_page_in_trash_is_deleted_state(self) -> None:
        service = self._service_with_page([{"in_trash": True}])

        deleted = await service.is_page_archived_or_missing("page-1")

        self.assertTrue(deleted)

    async def test_page_not_archived_is_not_deleted_state(self) -> None:
        service = self._service_with_page([{"archived": False, "in_trash": False}])

        deleted = await service.is_page_archived_or_missing("page-1")

        self.assertFalse(deleted)

    async def test_missing_page_is_deleted_state(self) -> None:
        service = self._service_with_page([_notion_404_error()])

        deleted = await service.is_page_archived_or_missing("page-1")

        self.assertTrue(deleted)
