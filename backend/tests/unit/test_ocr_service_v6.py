import json
import unittest

import httpx

from src.core.exceptions import ExternalServiceException
from src.services.ocr_service import OCRService


class OCRServiceV6Tests(unittest.IsolatedAsyncioTestCase):
    async def test_multipart_job_poll_and_jsonl_result(self) -> None:
        poll_count = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal poll_count
            if request.method == "POST":
                self.assertEqual(request.headers["authorization"], "bearer test-token")
                self.assertIn("multipart/form-data", request.headers["content-type"])
                body = await request.aread()
                self.assertIn(b"PP-OCRv6", body)
                self.assertIn(b"useDocUnwarping", body)
                return httpx.Response(200, json={"data": {"jobId": "job-1"}})

            if request.url.host == "results.example":
                jsonl = json.dumps(
                    {
                        "result": {
                            "ocrResults": [
                                {
                                    "prunedResult": {
                                        "rec_texts": ["第一行", "Second line"],
                                        "rec_scores": [0.9, 0.8],
                                    }
                                }
                            ]
                        }
                    },
                    ensure_ascii=False,
                )
                return httpx.Response(200, text=jsonl)

            poll_count += 1
            if poll_count == 1:
                return httpx.Response(200, json={"data": {"state": "running"}})
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "resultUrl": {"jsonUrl": "https://results.example/job.jsonl"},
                    }
                },
            )

        service = OCRService(
            api_url="https://paddleocr.example/api/v2/ocr/jobs",
            token="test-token",
            poll_interval=0,
            transport=httpx.MockTransport(handler),
        )
        result = await service.extract_text_from_bytes(
            b"fake image bytes",
            filename="test.png",
            use_unwarping=True,
        )

        self.assertEqual(result["text"], "第一行\nSecond line")
        self.assertAlmostEqual(result["confidence"], 0.85)
        self.assertEqual(result["page_count"], 1)
        self.assertEqual(len(result["blocks"]), 2)

    async def test_url_submission_uses_json_payload(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                payload = json.loads((await request.aread()).decode())
                self.assertEqual(payload["fileUrl"], "https://files.example/doc.pdf")
                self.assertEqual(payload["model"], "PP-OCRv6")
                return httpx.Response(200, json={"data": {"jobId": "job-url"}})
            if request.url.host == "results.example":
                return httpx.Response(
                    200,
                    text=json.dumps({"result": {"text": "URL result"}}),
                )
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "done",
                        "resultUrl": {"jsonUrl": "https://results.example/url.jsonl"},
                    }
                },
            )

        service = OCRService(
            api_url="https://paddleocr.example/api/v2/ocr/jobs",
            token="test-token",
            poll_interval=0,
            transport=httpx.MockTransport(handler),
        )
        result = await service.extract_text_from_url("https://files.example/doc.pdf")
        self.assertEqual(result["text"], "URL result")

    async def test_failed_job_raises_service_error(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            if request.method == "POST":
                return httpx.Response(200, json={"data": {"jobId": "job-failed"}})
            return httpx.Response(
                200,
                json={"data": {"state": "failed", "errorMsg": "unsupported file"}},
            )

        service = OCRService(
            api_url="https://paddleocr.example/api/v2/ocr/jobs",
            token="test-token",
            poll_interval=0,
            transport=httpx.MockTransport(handler),
        )
        with self.assertRaises(ExternalServiceException) as caught:
            await service.extract_text_from_bytes(b"bad file")
        self.assertEqual(caught.exception.error_code, "PADDLEOCR_JOB_FAILED")

    async def test_http_500_includes_upstream_diagnostic_without_auth_header(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                500,
                json={"msg": "temporary model backend failure", "traceId": "req-123"},
            )

        service = OCRService(
            api_url="https://paddleocr.example/api/v2/ocr/jobs",
            token="test-token",
            transport=httpx.MockTransport(handler),
        )
        with self.assertRaises(ExternalServiceException) as caught:
            await service.extract_text_from_bytes(b"image bytes")

        self.assertIn("HTTP 500", caught.exception.message)
        self.assertIn("temporary model backend failure", caught.exception.message)
        self.assertIn("traceId: req-123", caught.exception.message)
        self.assertEqual(caught.exception.details["request_id"], "req-123")


if __name__ == "__main__":
    unittest.main()
