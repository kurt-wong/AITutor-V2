"""
L2 标注契约 — LLM 标注结果的结构化镜像。

只存储行号引用、元数据和客观题短答案，不存储题干/选项/详解/解题过程原文。
simple pipeline 中 LLM 直接输出 answer_line_ids / explanation_line_ids，
代码按行号从 L1 原文切片；answer_matcher 仅作为缺失项 fallback。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §3-5。
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── 子题元数据 ──────────────────────────────────────────────────


@dataclass
class L2SubQuestion:
    """综合题中的子题元数据，用于考点频率分析。"""

    qno: str                    # 子题编号（如 "1"、"2"、"（1）"）
    question_type: str | None = None  # 子题题型（fill_in / single_choice / ...）
    answer: str | None = None   # 子题答案
    knowledge_points: list[str] = field(default_factory=list)
    score: float | None = None  # 子题分值


# ── L2 标注 ──────────────────────────────────────────────────────


@dataclass
class L2QuestionAnnotation:
    """L2 单题标注：LLM 输出的行号引用和元数据。"""

    question_number: str
    question_type: str         # single_choice / multiple_choice / fill_blank / ...
    section_id: str | None = None     # 共享材料题的 section 标识（如 "cloze_1"）
    # 语义标记：LLM 只输出从原文复制的短标记，代码负责在 L1 中匹配并切片。
    stem_start_marker: str | None = None
    stem_end_marker: str | None = None
    shared_material_line_ids: list[str] = field(default_factory=list)  # 共享材料的 L1 行号（如阅读理解文章段落）
    stem_line_ids: list[str] = field(default_factory=list)   # ["P1L003", "P1L004", ...]
    options_line_ids: dict[str, list[str]] = field(default_factory=dict)  # {"A": ["P1L008"], ...}
    # 客观题短答案（如 "C"、"AB"）；非客观题由 answer_line_ids 定位后由代码切片。
    # 该字段仅允许从答案区逐字提取的短结果，不允许 LLM 生成题干/选项/详解内容。
    answer: str | None = None
    answer_line_ids: list[str] = field(default_factory=list)       # 该题答案所在 L1 行
    explanation_line_ids: list[str] = field(default_factory=list)  # 该题详解/解题过程所在 L1 行
    difficulty: int | None = None     # 1-5
    score: float | None = None
    knowledge_points: list[str] = field(default_factory=list)
    confidence: float = 0.5           # 0-1
    source_page: int | None = None    # 题目所在起始页码
    # Phase 2C：Structure Signature（Annotation，非事实，随 prompt 版本变化）
    structure_signature: dict | None = None  # {"object": ..., "task": ..., "method": ...}
    # 综合题支持（共享材料 + 多子题）
    is_composite: bool = False        # 是否为综合题（材料 + 子题合并）
    sub_questions: list[L2SubQuestion] | None = None  # 子题元数据（仅综合题）


@dataclass
class L2DocumentAnnotation:
    """L2 文档级标注：整份文档的 LLM 标注结果。

    可追溯性约束（V1 LESSONS 3.16）：
    - 保存 LLM 原始锚点和校正后锚点
    - 保存 anchor_status 用于质量评估
    """

    filename: str
    subject: str | None = None
    grade: str | None = None
    year: int | None = None
    school: str | None = None
    questions: list[L2QuestionAnnotation] = field(default_factory=list)
    metadata_confidence: float = 0.5
    warnings: list[str] = field(default_factory=list)
    # 锚点追踪（可追溯性）
    llm_anchors: list[CorrectedAnchor] = field(default_factory=list)  # LLM 原始输出
    corrected_anchors: list[CorrectedAnchor] = field(default_factory=list)  # 校正后
    anchor_status_summary: dict[str, int] = field(default_factory=dict)  # {"exact": 5, "nearest": 2, ...}
    raw_response: str | None = None  # LLM 原始 JSON 响应，用于诊断 marker 质量问题


# ── 锚点校正 ──────────────────────────────────────────────────────


@dataclass
class CorrectedAnchor:
    """锚点校正结果：LLM 行号经过代码校正后的最终行号范围。"""

    field: str                    # "stem" / "options" / "answer" / "explanation"
    llm_line_ids: list[str]       # LLM 原始输出
    corrected_line_ids: list[str] # 校正后
    anchor_status: str            # exact / nearest / missing / retry
    validation_passed: bool = False  # nearest 是否通过内容校验
    evidence: str | None = None      # 校正依据（如 "吸附到题号标记 5.")
    question_number: str | None = None  # 所属题目编号（用于归属校验）


# ── Source Provenance ──────────────────────────────────────────────


@dataclass
class SourceProvenance:
    """来源标记：每个字段的来源与生成方式，用于可追溯和审核。"""

    field: str        # "answer" / "explanation" / "stem" / "options"
    source: str       # 来源类型（见 SOURCE_TYPES）
    confidence: float = 1.0   # 来源置信度
    evidence: str = ""        # 简短描述来源位置


# 来源类型常量
SOURCE_NATIVE_EXTRACT = "native_extract"
SOURCE_OCR_EXTRACT = "ocr_extract"
SOURCE_DOCUMENT_ANSWER_TABLE = "document_answer_table"
SOURCE_DOCUMENT_INLINE_ANSWER = "document_inline_answer"
SOURCE_DOCUMENT_INLINE_EXPLANATION = "document_inline_explanation"
SOURCE_DOCUMENT_SOLUTION_ANSWER = "document_solution_answer"
SOURCE_LLM_ANNOTATION = "llm_annotation"
SOURCE_LLM_FALLBACK = "llm_fallback"

SOURCE_TYPES = {
    SOURCE_NATIVE_EXTRACT: "从 Native PDF 文本层提取",
    SOURCE_OCR_EXTRACT: "从 OCR/VL 结果提取",
    SOURCE_DOCUMENT_ANSWER_TABLE: "从文末答案表匹配",
    SOURCE_DOCUMENT_INLINE_ANSWER: "从题后【答案】匹配",
    SOURCE_DOCUMENT_INLINE_EXPLANATION: "从题后【详解】/【分析】匹配",
    SOURCE_DOCUMENT_SOLUTION_ANSWER: "从题后解答题解题过程定位答案",
    SOURCE_LLM_ANNOTATION: "LLM 标注的行号切片",
    SOURCE_LLM_FALLBACK: "LLM 推理兜底（仅用于缺失项）",
}


# ── 切片结果 ──────────────────────────────────────────────────────


@dataclass
class SlicedQuestion:
    """内容切片结果：由 L1 原文 + 校正锚点切片生成的题目内容。"""

    question_number: str
    question_type: str
    stem: str = ""
    options: list[dict[str, str]] = field(default_factory=list)  # [{"label": "A", "text": "..."}]
    answer: str | None = None
    explanation: str | None = None
    section_id: str | None = None
    shared_material_line_ids: list[str] = field(default_factory=list)  # 共享材料的 L1 行号
    difficulty: int | None = None
    score: float | None = None
    knowledge_points: list[str] = field(default_factory=list)
    confidence: float = 0.5
    source_page: int | None = None
    # Phase 2C：Structure Signature（Annotation，非事实）
    structure_signature: dict | None = None
    # 行号审计字段（V1_LESSONS 3.22）
    answer_line_ids: list[str] = field(default_factory=list)
    explanation_line_ids: list[str] = field(default_factory=list)
    # 锚点状态
    stem_anchor: CorrectedAnchor | None = None
    options_anchor: CorrectedAnchor | None = None
    answer_anchor: CorrectedAnchor | None = None
    explanation_anchor: CorrectedAnchor | None = None
    # 校正锚点集合（完整审计）
    corrected_anchors: list[CorrectedAnchor] = field(default_factory=list)
    # 来源标记
    answer_provenance: SourceProvenance | None = None
    explanation_provenance: SourceProvenance | None = None
    # 问题列表
    issues: list[str] = field(default_factory=list)
    # 综合题支持
    is_composite: bool = False        # 是否为综合题
    sub_questions: list[L2SubQuestion] | None = None  # 子题元数据
    # 人工复查标记
    review_notes: list[str] | None = None  # 供人工复查的备注
