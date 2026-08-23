import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from app.domains.document.schemas import OcrBlock, OcrDocument, OcrPage, ParsedImage

logger = logging.getLogger(__name__)


DEFAULT_OPTIONAL_PAYLOAD = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}

# ---- 熔断状态（模块级，进程内所有 PaddleOCRClient 实例共享）----
# paddle AIStudio API 服务端"任务提交队列已满"（HTTP 400 code 10010）是共享队列状态，
# 不是本项目并发导致的瞬时故障。连续触发说明服务端队列持续满，重试只会浪费等待时间，
# 应快速熔断并降级到 VL（mimo/deepseek），熔断到期后自动恢复尝试。
_circuit_breaker: dict[str, float] = {"open_until": 0.0}  # time.monotonic() 截止时间
_CIRCUIT_OPEN_SECONDS = 300.0  # 熔断打开 5 分钟
_CIRCUIT_TRIGGER_COUNT = 2  # 连续 2 次 10010 触发熔断


def _circuit_open() -> bool:
    """判断 paddle 熔断是否打开。"""
    return time.monotonic() < _circuit_breaker["open_until"]


def _trip_circuit() -> None:
    """打开熔断。"""
    _circuit_breaker["open_until"] = time.monotonic() + _CIRCUIT_OPEN_SECONDS
    logger.warning("paddle circuit breaker OPEN for %.0fs (queue full)", _CIRCUIT_OPEN_SECONDS)


def _is_queue_full_error(response: httpx.Response) -> bool:
    """判断是否为服务端"任务提交队列已满"（10010）。

    官方错误码表无 10010；服务端返回 HTTP 400 + code 10010 表示共享队列满。
    与 429（超出单日解析页数）不同，10010 是并发队列状态，不是配额。
    """
    if response.status_code != 400:
        return False
    body = response.text or ""
    return "10010" in body or "queue full" in body.lower()


class PaddleOCRClientError(RuntimeError):
    pass


@dataclass(order=True)
class _QueueItem:
    """优先级队列元素：priority 越小越先执行。"""
    priority: int
    file_path: Path = field(compare=False)
    model: str | None = field(compare=False, default=None)
    future: asyncio.Future = field(compare=False, default=None)


class PaddleOCRQueue:
    """本地队列：控制 PaddleOCR 并发提交，支持优先级、重试、状态跟踪。

    使用方式：
        queue = PaddleOCRQueue(client, max_concurrent=1)
        document = await queue.submit(file_path, priority=10)
    """

    def __init__(
        self,
        client: "PaddleOCRClient",
        *,
        max_concurrent: int = 1,
    ) -> None:
        self._client = client
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: asyncio.PriorityQueue[_QueueItem] = asyncio.PriorityQueue()
        self._in_flight = 0
        self._total_submitted = 0
        self._total_completed = 0
        self._total_failed = 0
        self._worker_task: asyncio.Task | None = None

    async def submit(
        self,
        file_path: Path,
        *,
        model: str | None = None,
        priority: int = 10,
    ) -> OcrDocument:
        """提交 OCR 任务到本地队列，等待完成后返回结果。

        Args:
            file_path: PDF 文件路径
            model: OCR 模型（默认使用 client 配置）
            priority: 优先级，越小越先执行（默认 10）

        Returns:
            OcrDocument: OCR 识别结果
        """
        future: asyncio.Future[OcrDocument] = asyncio.get_running_loop().create_future()
        item = _QueueItem(
            priority=priority,
            file_path=file_path,
            model=model,
            future=future,
        )
        await self._queue.put(item)
        self._total_submitted += 1
        logger.info(
            "paddle_queue: enqueued %s priority=%d queue_size=%d",
            file_path.name,
            priority,
            self._queue.qsize(),
        )

        # 启动后台 worker（如果未运行）
        self._ensure_worker()

        # 等待结果
        return await future

    def _ensure_worker(self) -> None:
        """确保后台 worker 正在运行。"""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.ensure_future(self._worker_loop())

    def close(self) -> None:
        """取消后台 worker，防止 long-running 场景残留 pending task。"""
        worker = self._worker_task
        self._worker_task = None
        if worker is not None and not worker.done():
            worker.cancel()

    async def _worker_loop(self) -> None:
        """后台 worker：从队列取出任务，控制并发提交。"""
        while True:
            try:
                item = await self._queue.get()
            except asyncio.CancelledError:
                break

            # 等待信号量（控制并发）
            await self._semaphore.acquire()
            self._in_flight += 1

            try:
                # 提取 PDF
                document = await self._client.extract(
                    item.file_path,
                    model=item.model,
                )
                item.future.set_result(document)
                self._total_completed += 1
                logger.info(
                    "paddle_queue: completed %s in_flight=%d queue_size=%d",
                    item.file_path.name,
                    self._in_flight,
                    self._queue.qsize(),
                )
            except Exception as exc:
                item.future.set_exception(exc)
                self._total_failed += 1
                logger.warning(
                    "paddle_queue: failed %s error=%s",
                    item.file_path.name,
                    exc,
                )
            finally:
                self._in_flight -= 1
                self._semaphore.release()

    @property
    def stats(self) -> dict[str, Any]:
        """返回队列状态统计。"""
        return {
            "queue_size": self._queue.qsize(),
            "in_flight": self._in_flight,
            "total_submitted": self._total_submitted,
            "total_completed": self._total_completed,
            "total_failed": self._total_failed,
        }


class PaddleOCRClient:
    name = "paddleocr"

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        model: str = "PP-StructureV3",
        timeout_seconds: float = 60.0,
        poll_interval_seconds: float = 5.0,
        job_timeout_seconds: float = 600.0,
        submit_max_retries: int = 5,
        submit_retry_delay: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.job_timeout_seconds = job_timeout_seconds
        self.submit_max_retries = submit_max_retries
        self.submit_retry_delay = submit_retry_delay
        self.transport = transport

    @staticmethod
    def _http_error(response: httpx.Response, context: str) -> PaddleOCRClientError:
        """把 HTTP 状态码和响应体包装成可审计的 PaddleOCRClientError。

        不能只抛 raise_for_status() 的通用错误：丢失 status/body 会导致
        OCR 链路失败原因不可复现（"PaddleOCR 返回格式错误"必须可审计）。
        """
        try:
            body = response.text[:500]
        except Exception:
            body = "<body unreadable>"
        return PaddleOCRClientError(
            f"paddle {context} HTTP {response.status_code}: {body}"
        )

    async def extract(
        self,
        file_path: Path,
        *,
        model: str | None = None,
    ) -> OcrDocument:
        logger.info(f"Extracting structure from {file_path.name}...")
        if not self.token:
            raise PaddleOCRClientError("PADDLEOCR_VL_TOKEN is not configured")

        selected_model = model or self.model
        headers = {"Authorization": f"bearer {self.token}"}
        data = {
            "model": selected_model,
            "optionalPayload": json.dumps(DEFAULT_OPTIONAL_PAYLOAD),
        }

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            # 熔断检查：paddle 服务端队列持续满（10010）时直接跳过，
            # 不浪费重试等待，让 OCRFallbackChain 立即降级到 VL。
            if _circuit_open():
                raise PaddleOCRClientError(
                    "paddle circuit breaker open (queue full), skipping to VL fallback"
                )
            response = await self._submit_with_retry(
                client,
                file_path=file_path,
                headers=headers,
                data=data,
            )
            job_id = response.json().get("data", {}).get("jobId")
            if not job_id:
                raise PaddleOCRClientError("paddle job response missing jobId")

            job_data = await self._poll(client, job_id, headers=headers)
            jsonl_url = (job_data.get("resultUrl") or {}).get("jsonUrl")
            if not jsonl_url:
                raise PaddleOCRClientError("paddle job result missing jsonUrl")

            jsonl_response = await client.get(jsonl_url)
            if jsonl_response.status_code >= 400:
                raise self._http_error(jsonl_response, "download")
            document = self._parse_jsonl(
                jsonl_response.text,
                filename=file_path.name,
                provider=selected_model,
            )
            document.provider_used = selected_model
            return document

    async def _submit_with_retry(
        self,
        client: httpx.AsyncClient,
        *,
        file_path: Path,
        headers: dict[str, str],
        data: dict,
    ) -> httpx.Response:
        last_error: PaddleOCRClientError | None = None
        queue_full_streak = 0
        for attempt in range(self.submit_max_retries + 1):
            try:
                with file_path.open("rb") as file_handle:
                    response = await client.post(
                        self.base_url,
                        headers=headers,
                        data=data,
                        files={
                            "file": (
                                file_path.name,
                                file_handle,
                                _content_type(file_path),
                            )
                        },
                    )
                if response.status_code < 400:
                    return response

                error = self._http_error(response, "submit")

                # 队列满（10010）：快速重试 2 次后触发熔断，不按普通瞬态错误重试 6 次。
                # 10010 是服务端共享队列状态，重试 155s 大概率仍满；熔断后直接降级 VL。
                if _is_queue_full_error(response):
                    queue_full_streak += 1
                    if queue_full_streak < _CIRCUIT_TRIGGER_COUNT and attempt < self.submit_max_retries:
                        delay = self.submit_retry_delay * (2 ** attempt)
                        logger.warning(
                            "paddle submit queue full (10010), attempt=%d/%d retrying in %.1fs",
                            attempt + 1, _CIRCUIT_TRIGGER_COUNT, delay,
                        )
                        await asyncio.sleep(delay)
                        last_error = error
                        continue
                    _trip_circuit()
                    raise error

                if self._is_transient_error(response) and attempt < self.submit_max_retries:
                    delay = self.submit_retry_delay * (2 ** attempt)
                    logger.warning(
                        "paddle submit transient error %d, attempt=%d/%d retrying in %.1fs",
                        response.status_code,
                        attempt + 1,
                        self.submit_max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    last_error = error
                    continue
                raise error
            except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
                if attempt < self.submit_max_retries:
                    delay = self.submit_retry_delay * (2 ** attempt)
                    logger.warning(
                        "paddle submit network error: %s, attempt=%d/%d retrying in %.1fs",
                        exc,
                        attempt + 1,
                        self.submit_max_retries + 1,
                        delay,
                    )
                    last_error = PaddleOCRClientError(f"paddle submit network error: {exc}")
                    await asyncio.sleep(delay)
                    continue
                raise PaddleOCRClientError(f"paddle submit network error after {attempt + 1} attempts: {exc}")
        raise last_error  # pragma: no cover - defensive path

    @staticmethod
    def _is_transient_error(response: httpx.Response) -> bool:
        """判断是否为可重试的瞬态错误（队列满、5xx、429）。"""
        if response.status_code in (429, 502, 503, 504):
            return True
        if response.status_code == 400:
            body = response.text or ""
            if "10010" in body or "queue full" in body.lower():
                return True
        return False

    async def _poll(
        self,
        client: httpx.AsyncClient,
        job_id: str,
        *,
        headers: dict[str, str],
    ) -> dict:
        deadline = time.monotonic() + self.job_timeout_seconds
        while True:
            response = await client.get(
                f"{self.base_url}/{job_id}",
                headers=headers,
            )
            if response.status_code >= 400:
                raise self._http_error(response, "poll")
            data = response.json().get("data", {})
            state = str(data.get("state", "")).lower()
            if state == "done":
                # C1 修复：校验 extractProgress，确保所有页面已提取
                extract_progress = data.get("extractProgress")
                if not extract_progress or not isinstance(extract_progress, dict):
                    raise PaddleOCRClientError(
                        "paddle extraction missing extractProgress; "
                        f"raw data={_safe_preview(data)}"
                    )
                total = extract_progress.get("totalPages")
                extracted = extract_progress.get("extractedPages")
                if type(total) is not int or total < 1:
                    raise PaddleOCRClientError(
                        f"paddle extraction invalid totalPages: {total!r}; "
                        f"raw data={_safe_preview(data)}"
                    )
                if type(extracted) is not int or extracted < 1:
                    raise PaddleOCRClientError(
                        f"paddle extraction invalid extractedPages: {extracted!r}; "
                        f"raw data={_safe_preview(data)}"
                    )
                if extracted != total:
                    raise PaddleOCRClientError(
                        f"paddle extraction incomplete: {extracted}/{total} pages; "
                        f"raw data={_safe_preview(data)}"
                    )
                return data
            if state == "failed":
                error = data.get("errorMsg") or data.get("error_msg") or "unknown"
                raise PaddleOCRClientError(f"paddle job failed: {error}")
            if time.monotonic() >= deadline:
                raise PaddleOCRClientError("paddle job timed out")
            await asyncio.sleep(self.poll_interval_seconds)

    def _parse_jsonl(
        self,
        text: str,
        *,
        filename: str,
        provider: str,
    ) -> OcrDocument:
        """解析 PP-StructureV3 JSONL 为 OcrDocument。

        页号来源（兼容真实 API 两种格式）：
        1. JSONL 行顶层 `page` 字段（部分 API 提供）；
        2. 无 `page` 字段时，按 layoutParsingResults 元素顺序递增编号
           （PaddleOCR 官方示例行为：每个元素对应一页）。
        """
        pages: list[OcrPage] = []
        page_counter = 0
        for line_idx, raw_line in enumerate(text.splitlines()):
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PaddleOCRClientError(
                    f"JSONL line {line_idx} is not valid JSON: {exc}; "
                    f"raw={line[:200]!r}"
                ) from exc
            # C2 修复：优先使用显式 page 字段
            explicit_page = item.get("page")
            if explicit_page is not None:
                if not isinstance(explicit_page, int) or explicit_page < 1:
                    raise PaddleOCRClientError(
                        f"JSONL line {line_idx} has invalid 'page' value: {explicit_page!r}; "
                        f"raw={line[:200]!r}"
                    )
            result = item.get("result", {})
            layouts = result.get("layoutParsingResults", [])
            for layout in layouts:
                if explicit_page is not None:
                    page_number = explicit_page
                else:
                    # 真实 PP API 不返回 page 字段：按元素顺序编号（每元素一页）
                    page_counter += 1
                    page_number = page_counter
                markdown = (layout.get("markdown") or {}).get("text", "")
                images = self._collect_images(
                    layout,
                    page_number=page_number,
                )
                blocks = self._collect_blocks(layout)
                pages.append(
                    OcrPage(
                        page_number=page_number,
                        markdown=markdown,
                        images=images,
                        blocks=blocks,
                        source_provider=provider,
                    )
                )
        if not pages:
            raise PaddleOCRClientError("paddle job returned no layout pages")
        return OcrDocument(filename=filename, pages=pages)

    def _collect_images(
        self,
        layout: dict,
        *,
        page_number: int,
    ) -> list[ParsedImage]:
        images: list[ParsedImage] = []
        markdown_images = (layout.get("markdown") or {}).get("images", {}) or {}
        for image_id, url in markdown_images.items():
            bbox = _parse_image_bbox(str(image_id))
            images.append(
                ParsedImage(
                    id=str(image_id),
                    url=_http_url(url),
                    page_number=page_number,
                    role="diagram",
                    bbox=bbox,
                )
            )
        output_images = layout.get("outputImages", {}) or {}
        for image_id, url in output_images.items():
            bbox = _parse_image_bbox(str(image_id))
            images.append(
                ParsedImage(
                    id=str(image_id),
                    url=_http_url(url),
                    page_number=page_number,
                    role="output",
                    bbox=bbox,
                )
            )
        return images

    def _collect_blocks(self, layout: dict) -> list[OcrBlock]:
        """从 prunedResult.parsing_res_list 提取 block 级 bbox 数据。"""
        blocks: list[OcrBlock] = []
        pruned = layout.get("prunedResult") or {}
        parsing_list = pruned.get("parsing_res_list") or []
        for entry in parsing_list:
            label = entry.get("block_label", "")
            content = entry.get("block_content", "")
            raw_bbox = entry.get("block_bbox")
            bbox = None
            if raw_bbox:
                if isinstance(raw_bbox, list) and len(raw_bbox) >= 4:
                    # PP-StructureV3 返回 [x1, y1, x2, y2] 数组
                    bbox = {
                        "x1": float(raw_bbox[0]), "y1": float(raw_bbox[1]),
                        "x2": float(raw_bbox[2]), "y2": float(raw_bbox[3]),
                    }
                elif isinstance(raw_bbox, dict):
                    x1 = raw_bbox.get("x1") or raw_bbox.get("left") or raw_bbox.get("x")
                    y1 = raw_bbox.get("y1") or raw_bbox.get("top") or raw_bbox.get("y")
                    x2 = raw_bbox.get("x2") or raw_bbox.get("right")
                    y2 = raw_bbox.get("y2") or raw_bbox.get("bottom")
                    if x1 is not None and y1 is not None and x2 is not None and y2 is not None:
                        bbox = {"x1": float(x1), "y1": float(y1), "x2": float(x2), "y2": float(y2)}
            if label or content:
                blocks.append(OcrBlock(label=label, content=content, bbox=bbox))
        return blocks


def _content_type(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "application/pdf"
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if path.suffix.lower() == ".png":
        return "image/png"
    return "application/octet-stream"


def _http_url(value) -> str | None:
    text = str(value)
    if text.startswith(("http://", "https://")):
        return text
    return None


def _parse_image_bbox(image_id: str) -> dict | None:
    """从图片文件名解析 bbox 坐标。

    PP-StructureV3 图片文件名格式：img_in_formula_box_{x1}_{y1}_{x2}_{y2}.jpg
    """
    import re
    m = re.search(r"_(\d+)_(\d+)_(\d+)_(\d+)\.\w+$", image_id)
    if m:
        x1, y1, x2, y2 = (float(v) for v in m.groups())
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
    return None


def _safe_preview(data: dict, limit: int = 300) -> str:
    """把原始响应 data 转成可审计的短文本片段（不打印密钥/超长内容）。"""
    try:
        text = json.dumps(data, ensure_ascii=False)[:limit]
    except Exception:
        text = f"<unserializable: {type(data).__name__}>"
    return text
