"""PaddleOCR v6 asynchronous job client."""

import asyncio
import json
import mimetypes
import time
from pathlib import Path
from typing import Any, Optional

import httpx

from src.core.exceptions import ExternalServiceException
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OCRService:
    """Extract text from images and PDFs through PaddleOCR v6."""

    def __init__(
        self,
        api_url: str,
        token: str,
        model: str = "PP-OCRv6",
        poll_interval: float = 5.0,
        job_timeout: float = 300.0,
        request_timeout: float = 60.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_url or not token:
            raise ValueError("PaddleOCR API URL and token are required")

        self.api_url = api_url.rstrip("/")
        self.token = token
        self.model = model
        self.poll_interval = max(poll_interval, 0.0)
        self.job_timeout = max(job_timeout, 1.0)
        self.request_timeout = max(request_timeout, 1.0)
        self.transport = transport

        if not self.api_url.endswith("/api/v2/ocr/jobs"):
            logger.warning(
                "PaddleOCR v6 endpoint usually ends with /api/v2/ocr/jobs: %s",
                self.api_url,
            )

    async def extract_text_from_image(
        self,
        image_file_path: str,
        language_hints: Optional[list[str]] = None,
        use_chart_recognition: bool = False,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
        use_textline_orientation: bool = False,
    ) -> dict[str, Any]:
        """Submit a local image or PDF and wait for its OCR result."""
        del language_hints
        path = Path(image_file_path)
        if not path.exists():
            raise FileNotFoundError(f"OCR file not found: {image_file_path}")

        if use_chart_recognition:
            logger.warning("PP-OCRv6 does not expose useChartRecognition; option ignored")

        try:
            file_bytes = path.read_bytes()
            if not file_bytes:
                raise ExternalServiceException(
                    "OCR file is empty",
                    error_code="PADDLEOCR_INVALID_INPUT",
                )
            return await self._call_ocr_api(
                file_bytes=file_bytes,
                filename=path.name,
                content_type=mimetypes.guess_type(path.name)[0],
                use_orientation_classify=use_orientation_classify,
                use_unwarping=use_unwarping,
                use_textline_orientation=use_textline_orientation,
            )
        except ExternalServiceException:
            raise
        except Exception as exc:
            logger.exception("PaddleOCR file processing failed")
            raise ExternalServiceException(
                f"Failed to extract text from file: {exc}",
                error_code="OCR_FAILED",
            ) from exc

    async def extract_text_from_bytes(
        self,
        image_bytes: bytes,
        language_hints: Optional[list[str]] = None,
        file_type: int = 1,
        use_chart_recognition: bool = False,
        filename: str | None = None,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
        use_textline_orientation: bool = False,
    ) -> dict[str, Any]:
        """Submit image/PDF bytes and wait for the OCR result."""
        del language_hints
        if not image_bytes:
            raise ExternalServiceException(
                "OCR input is empty",
                error_code="PADDLEOCR_INVALID_INPUT",
            )
        if use_chart_recognition:
            logger.warning("PP-OCRv6 does not expose useChartRecognition; option ignored")

        default_name = "document.pdf" if file_type == 0 else "image.png"
        upload_name = filename or default_name
        content_type = mimetypes.guess_type(upload_name)[0]

        try:
            return await self._call_ocr_api(
                file_bytes=image_bytes,
                filename=upload_name,
                content_type=content_type,
                use_orientation_classify=use_orientation_classify,
                use_unwarping=use_unwarping,
                use_textline_orientation=use_textline_orientation,
            )
        except ExternalServiceException:
            raise
        except Exception as exc:
            logger.exception("PaddleOCR byte processing failed")
            raise ExternalServiceException(
                f"Failed to extract text from bytes: {exc}",
                error_code="OCR_FAILED",
            ) from exc

    async def extract_text_from_url(
        self,
        file_url: str,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
        use_textline_orientation: bool = False,
    ) -> dict[str, Any]:
        """Submit a remote file URL and wait for the OCR result."""
        if not file_url.startswith(("http://", "https://")):
            raise ValueError("file_url must use http or https")

        return await self._call_ocr_api(
            file_url=file_url,
            use_orientation_classify=use_orientation_classify,
            use_unwarping=use_unwarping,
            use_textline_orientation=use_textline_orientation,
        )

    async def _call_ocr_api(
        self,
        file_bytes: bytes | None = None,
        filename: str = "image.png",
        content_type: str | None = None,
        file_url: str | None = None,
        use_orientation_classify: bool = False,
        use_unwarping: bool = False,
        use_textline_orientation: bool = False,
    ) -> dict[str, Any]:
        """Submit, poll and download one PaddleOCR v6 job."""
        if (file_bytes is None) == (file_url is None):
            raise ValueError("Provide exactly one of file_bytes or file_url")

        optional_payload = {
            "useDocOrientationClassify": use_orientation_classify,
            "useDocUnwarping": use_unwarping,
            "useTextlineOrientation": use_textline_orientation,
        }
        headers = {"Authorization": f"bearer {self.token}"}

        try:
            async with httpx.AsyncClient(
                timeout=self.request_timeout,
                transport=self.transport,
                follow_redirects=True,
            ) as client:
                if file_url is not None:
                    response = await client.post(
                        self.api_url,
                        headers={**headers, "Content-Type": "application/json"},
                        json={
                            "fileUrl": file_url,
                            "model": self.model,
                            "optionalPayload": optional_payload,
                        },
                    )
                else:
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        data={
                            "model": self.model,
                            "optionalPayload": json.dumps(optional_payload),
                        },
                        files={
                            "file": (
                                filename,
                                file_bytes,
                                content_type or "application/octet-stream",
                            )
                        },
                    )

                job_id = self._parse_job_submission(response)
                result_url = await self._poll_job(client, headers, job_id)
                return await self._download_result(client, result_url)
        except ExternalServiceException:
            raise
        except httpx.TimeoutException as exc:
            raise ExternalServiceException(
                "PaddleOCR request timed out",
                error_code="PADDLEOCR_TIMEOUT",
            ) from exc
        except httpx.HTTPError as exc:
            raise ExternalServiceException(
                f"PaddleOCR HTTP request failed: {exc}",
                error_code="PADDLEOCR_HTTP_ERROR",
            ) from exc

    def _parse_job_submission(self, response: httpx.Response) -> str:
        if response.status_code != 200:
            raise self._http_error(response, "submit")

        try:
            job_id = response.json()["data"]["jobId"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalServiceException(
                "PaddleOCR submit response did not contain data.jobId",
                error_code="PADDLEOCR_INVALID_RESPONSE",
            ) from exc

        if not isinstance(job_id, str) or not job_id:
            raise ExternalServiceException(
                "PaddleOCR returned an invalid job id",
                error_code="PADDLEOCR_INVALID_RESPONSE",
            )
        return job_id

    async def _poll_job(
        self,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        job_id: str,
    ) -> str:
        deadline = time.monotonic() + self.job_timeout
        status_url = f"{self.api_url}/{job_id}"

        while time.monotonic() < deadline:
            response = await client.get(status_url, headers=headers)
            if response.status_code != 200:
                raise self._http_error(response, "poll")

            try:
                data = response.json()["data"]
                state = str(data["state"]).lower()
            except (KeyError, TypeError, ValueError) as exc:
                raise ExternalServiceException(
                    "PaddleOCR poll response is malformed",
                    error_code="PADDLEOCR_INVALID_RESPONSE",
                ) from exc

            if state == "done":
                try:
                    result_url = data["resultUrl"]["jsonUrl"]
                except (KeyError, TypeError) as exc:
                    raise ExternalServiceException(
                        "PaddleOCR completed without resultUrl.jsonUrl",
                        error_code="PADDLEOCR_INVALID_RESPONSE",
                    ) from exc
                if not isinstance(result_url, str) or not result_url:
                    raise ExternalServiceException(
                        "PaddleOCR returned an invalid result URL",
                        error_code="PADDLEOCR_INVALID_RESPONSE",
                    )
                return result_url

            if state == "failed":
                message = str(data.get("errorMsg") or "Unknown OCR job failure")
                raise ExternalServiceException(
                    f"PaddleOCR job failed: {message}",
                    error_code="PADDLEOCR_JOB_FAILED",
                )

            if state not in {"pending", "running"}:
                raise ExternalServiceException(
                    f"PaddleOCR returned unknown job state: {state}",
                    error_code="PADDLEOCR_INVALID_RESPONSE",
                )

            await asyncio.sleep(self.poll_interval)

        raise ExternalServiceException(
            f"PaddleOCR job did not finish within {self.job_timeout:g} seconds",
            error_code="PADDLEOCR_JOB_TIMEOUT",
        )

    async def _download_result(
        self,
        client: httpx.AsyncClient,
        result_url: str,
    ) -> dict[str, Any]:
        response = await client.get(result_url)
        if response.status_code != 200:
            raise self._http_error(response, "download result")
        return self._parse_jsonl_result(response.text)

    def _parse_jsonl_result(self, content: str) -> dict[str, Any]:
        all_text: list[str] = []
        all_scores: list[float] = []
        blocks: list[dict[str, Any]] = []
        page_count = 0

        for line_number, raw_line in enumerate(content.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExternalServiceException(
                    f"PaddleOCR result contains invalid JSONL at line {line_number}",
                    error_code="PADDLEOCR_INVALID_RESULT",
                ) from exc

            result = item.get("result", item) if isinstance(item, dict) else {}
            entries = result.get("ocrResults") if isinstance(result, dict) else None
            if not isinstance(entries, list) or not entries:
                entries = [result]

            page_count += len(entries)
            for entry in entries:
                texts, scores = self._extract_text_and_scores(entry)
                all_text.extend(texts)
                all_scores.extend(scores)
                for index, text in enumerate(texts):
                    block: dict[str, Any] = {"text": text}
                    if index < len(scores):
                        block["confidence"] = scores[index]
                    blocks.append(block)

        full_text = "\n".join(text for text in all_text if text).strip()
        confidence = (
            sum(all_scores) / len(all_scores)
            if all_scores
            else (0.95 if full_text else 0.0)
        )

        return {
            "text": full_text,
            "confidence": max(0.0, min(confidence, 1.0)),
            "language": self._detect_language(full_text),
            "word_count": len(full_text.split()),
            "blocks": blocks,
            # PP-OCRv6 returns plain OCR lines rather than layout Markdown.
            "markdown": full_text,
            "page_count": page_count,
        }

    def _extract_text_and_scores(self, entry: Any) -> tuple[list[str], list[float]]:
        if isinstance(entry, str):
            try:
                entry = json.loads(entry)
            except json.JSONDecodeError:
                return ([entry] if entry.strip() else []), []
        if not isinstance(entry, dict):
            return [], []

        candidates: list[dict[str, Any]] = []
        for key in ("prunedResult", "result", "res"):
            value = entry.get(key)
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    value = {"text": value}
            if isinstance(value, dict):
                candidates.append(value)
        candidates.append(entry)

        for candidate in candidates:
            raw_texts = None
            for key in ("rec_texts", "recTexts", "texts", "recognizedTexts"):
                if isinstance(candidate.get(key), list):
                    raw_texts = candidate[key]
                    break

            texts = [str(value).strip() for value in raw_texts or [] if str(value).strip()]
            if not texts:
                text = candidate.get("text")
                if isinstance(text, str) and text.strip():
                    texts = [text.strip()]
                markdown = candidate.get("markdown")
                if not texts and isinstance(markdown, dict):
                    markdown_text = markdown.get("text")
                    if isinstance(markdown_text, str) and markdown_text.strip():
                        texts = [markdown_text.strip()]

            if texts:
                raw_scores = None
                for key in ("rec_scores", "recScores", "scores", "confidence"):
                    value = candidate.get(key)
                    if isinstance(value, list):
                        raw_scores = value
                        break
                    if isinstance(value, (int, float)):
                        raw_scores = [value]
                        break
                scores = [float(value) for value in raw_scores or [] if isinstance(value, (int, float))]
                return texts, scores

        return [], []

    def _http_error(self, response: httpx.Response, action: str) -> ExternalServiceException:
        """Convert an upstream error into a useful, bounded diagnostic.

        PaddleOCR sometimes returns HTTP 500 with the actual reason only in the
        response body. Keeping that body in the exception makes the backend log
        actionable without ever including request headers (and therefore the
        bearer token).
        """
        message = f"PaddleOCR {action} failed with HTTP {response.status_code}"
        response_summary = ""
        upstream_trace_id = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                api_message = (
                    payload.get("message")
                    or payload.get("errorMsg")
                    or payload.get("error")
                    or payload.get("msg")
                )
                upstream_trace_id = payload.get("traceId") or payload.get("trace_id")
            else:
                api_message = None
                upstream_trace_id = None
            if api_message:
                response_summary = str(api_message)
        except (ValueError, AttributeError):
            response_summary = ""

        if not response_summary:
            response_summary = response.text.strip()
        if response_summary:
            # Avoid flooding application logs with an HTML proxy page or a
            # huge upstream trace. The first 1000 chars usually contain the
            # actionable error and are enough for incident diagnosis.
            response_summary = response_summary[:1000]
            message = f"{message}: {response_summary}"

        request_id = next(
            (
                response.headers.get(header)
                for header in ("x-request-id", "request-id", "trace-id")
                if response.headers.get(header)
            ),
            None,
        )
        request_id = request_id or upstream_trace_id
        if request_id:
            message = f"{message} (traceId: {request_id})"
        details: dict[str, Any] = {"status_code": response.status_code}
        if response_summary:
            details["response"] = response_summary
        if request_id:
            details["request_id"] = request_id
        return ExternalServiceException(
            message,
            error_code="PADDLEOCR_API_ERROR",
            details=details,
        )

    def _detect_language(self, text: str) -> str:
        if not text:
            return "unknown"
        total = len(text)
        chinese = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        japanese = sum(
            1
            for char in text
            if "\u3040" <= char <= "\u309f" or "\u30a0" <= char <= "\u30ff"
        )
        korean = sum(1 for char in text if "\uac00" <= char <= "\ud7af")
        if chinese / total > 0.3:
            return "zh"
        if japanese / total > 0.3:
            return "ja"
        if korean / total > 0.3:
            return "ko"
        return "en"

    async def health_check(self) -> bool:
        """Check endpoint reachability without submitting a billable OCR job."""
        try:
            async with httpx.AsyncClient(
                timeout=min(self.request_timeout, 10.0),
                transport=self.transport,
                follow_redirects=True,
            ) as client:
                response = await client.get(
                    self.api_url,
                    headers={"Authorization": f"bearer {self.token}"},
                )
            if response.status_code in {401, 403, 404}:
                return False
            return response.status_code < 500
        except httpx.HTTPError as exc:
            logger.error("PaddleOCR health check failed: %s", exc)
            return False


_ocr_service: OCRService | None = None


def get_ocr_service(
    api_url: Optional[str] = None,
    token: Optional[str] = None,
) -> OCRService:
    """Return the configured PaddleOCR v6 singleton."""
    global _ocr_service

    if _ocr_service is None:
        from src.config import settings

        api_url = api_url or settings.PADDLEOCR_API_URL
        token = token or settings.PADDLEOCR_TOKEN
        if not api_url or not token:
            raise ValueError(
                "PaddleOCR API URL and token must be configured "
                "(PADDLEOCR_API_URL, PADDLEOCR_TOKEN)"
            )
        _ocr_service = OCRService(
            api_url=api_url,
            token=token,
            model=settings.PADDLEOCR_MODEL,
            poll_interval=settings.PADDLEOCR_POLL_INTERVAL,
            job_timeout=settings.PADDLEOCR_JOB_TIMEOUT,
            request_timeout=settings.PADDLEOCR_REQUEST_TIMEOUT,
        )

    return _ocr_service
