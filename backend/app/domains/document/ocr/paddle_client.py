import asyncio
import json
import time
from pathlib import Path

import httpx

from app.domains.document.schemas import OcrBlock, OcrDocument, OcrPage, ParsedImage


DEFAULT_OPTIONAL_PAYLOAD = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}


class PaddleOCRClientError(RuntimeError):
    pass


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
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.job_timeout_seconds = job_timeout_seconds
        self.transport = transport

    async def extract(
        self,
        file_path: Path,
        *,
        model: str | None = None,
    ) -> OcrDocument:
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
            response.raise_for_status()
            job_id = response.json().get("data", {}).get("jobId")
            if not job_id:
                raise PaddleOCRClientError("paddle job response missing jobId")

            job_data = await self._poll(client, job_id, headers=headers)
            jsonl_url = (job_data.get("resultUrl") or {}).get("jsonUrl")
            if not jsonl_url:
                raise PaddleOCRClientError("paddle job result missing jsonUrl")

            jsonl_response = await client.get(jsonl_url)
            jsonl_response.raise_for_status()
            return self._parse_jsonl(
                jsonl_response.text,
                filename=file_path.name,
                provider=selected_model,
            )

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
            response.raise_for_status()
            data = response.json().get("data", {})
            state = str(data.get("state", "")).lower()
            if state == "done":
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
        pages: list[OcrPage] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            result = item.get("result", {})
            for layout in result.get("layoutParsingResults", []):
                page_number = len(pages) + 1
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
