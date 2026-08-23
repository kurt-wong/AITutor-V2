"""
L1 行模型 — 文档解析的统一中间表示。

Native 和 OCR 输出必须统一为同一个 L1Document，LLM 只面对 canonical L1，不关心来源。

行 ID 格式：
- PP-StructureV3：P{page}L{line_in_page}（如 P1L001）
- Native：N{page}L{line_in_page}（如 N1L001）

canonical 双源 L1 保留 PP 行号体系；native 行号只写入 raw_sources 的
`native_line_id`，不暴露给 LLM 标注阶段。
L1 原文不可变，LLM 只输出行号引用，不输出题目内容文本。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §2。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class L1Line:
    """L1 行模型：带页码的稳定行 ID。"""

    line_id: str          # "P1L001"/"N1L001" — 全局唯一，按来源区分前缀
    page_no: int          # 1-based 页码
    line_no_in_page: int  # 页内行号（1-based）
    order: int            # 全局排序序号（1-based，跨页连续）
    text: str             # 行文本（不可变）
    block_type: str       # text / formula / table / figure_placeholder
    bbox: dict | None = None     # {"x1": 0, "y1": 0, "x2": 100, "y2": 20}
    source: str = "native"       # native / paddleocr / mimo / deepseek_vl（已选定来源）
    continuation: bool = False   # 是否跨页续行
    # 双源字段
    raw_sources: dict = field(default_factory=dict)  # {"native": "...", "ppsv3": "...", "native_line_id": "N1L001"}
    selected_source: str = ""    # 最终选定来源（空=待仲裁）
    evidence: str = ""           # 选定依据
    confidence: float = 1.0      # 置信度


@dataclass
class L1Image:
    """L1 图片模型：文档中的图片资源。

    遵守 DSD question_images 和 V1 LESSONS 3.4/3.26 约束：
    - 图片必须带 page/bbox/placement/source
    - placement 描述图片在题目中的位置（题干/选项/详解/答案区/独立）
    """

    image_id: str         # 文档级唯一
    page_no: int
    bbox: dict | None = None     # {"x1": 0, "y1": 0, "x2": 100, "y2": 20}
    xref: int | None = None      # PyMuPDF xref（Native 路径）
    source: str = "native"       # native / paddleocr
    figure_id: str = ""          # 文档级去重标识
    url: str | None = None       # 图片 URL（OCR 路径）
    placement: str = "unknown"   # stem / options / explanation / answer_area / standalone / unknown


@dataclass
class L1Page:
    """L1 页面模型：单页的行和图片。"""

    page_no: int
    lines: list[L1Line] = field(default_factory=list)
    images: list[L1Image] = field(default_factory=list)


@dataclass
class L1Document:
    """L1 文档模型：Native/OCR 统一输出，LLM 只面对这一层。

    不可变契约（V1 LESSONS 3.1）：
    - lines 是 canonical lines（后处理后的行）
    - raw_lines 是处理前的原始行，用于追溯
    - postprocess_l1() 返回新对象，不修改原始文档
    """

    filename: str
    pages: list[L1Page] = field(default_factory=list)
    lines: list[L1Line] = field(default_factory=list)   # canonical lines（按 order 排序）
    images: list[L1Image] = field(default_factory=list)
    source: str = "native"          # native / ocr / mixed
    total_pages: int = 0
    text_coverage: float = 0.0      # 文本层覆盖率（Native 路径）
    raw_lines: list[L1Line] = field(default_factory=list)  # 原始行（不可变追溯）

    def get_line_by_id(self, line_id: str) -> L1Line | None:
        """按 line_id 查找行。"""
        for line in self.lines:
            if line.line_id == line_id:
                return line
        return None

    def get_lines_by_ids(self, line_ids: list[str]) -> list[L1Line]:
        """按 line_id 列表查找行，保持顺序。"""
        result = []
        for lid in line_ids:
            line = self.get_line_by_id(lid)
            if line is not None:
                result.append(line)
        return result

    def get_page_text(self, page_no: int) -> str:
        """获取指定页的完整文本（行间换行）。"""
        page_lines = [l for l in self.lines if l.page_no == page_no]
        page_lines.sort(key=lambda l: l.line_no_in_page)
        return "\n".join(l.text for l in page_lines)

    def get_range_text(self, line_ids: list[str]) -> str:
        """按行 ID 列表获取文本片段（行间换行）。"""
        lines = self.get_lines_by_ids(line_ids)
        return "\n".join(l.text for l in lines)
