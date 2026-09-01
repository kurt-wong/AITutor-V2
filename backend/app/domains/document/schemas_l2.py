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
    """综合题中的子题元数据，用于考点频率分析。

    2026-08-27（P4E.1）：新增 stem/options 文本字段——content_slicer 按
    子题行号切片后填充，入库/API/前端全程保留（此前只存行号，链路丢弃
    子题内容导致"完形选项聚合/子题无内容"质量事故，见 LOG v6.43）。

    2026-08-30（展示契约 v0.4）：补齐展示字段，与父题保持一致。
    """

    qno: str                    # 子题编号（如 "1"、"2"、"（1）"）
    question_type: str | None = None  # 子题题型（fill_in / single_choice / ...）
    # 2026-08-26：选择题组综合题（共享题图，"读图完成 18-20 题"）子题
    # 带题干/选项行号，供切片/入库保留各子题完整内容。
    stem_line_ids: list[str] = field(default_factory=list)
    options_line_ids: dict[str, list[str]] = field(default_factory=dict)
    answer: str | None = None   # 子题答案
    answer_line_ids: list[str] = field(default_factory=list)  # 子题答案行号
    explanation_line_ids: list[str] = field(default_factory=list)  # 子题详解行号
    knowledge_points: list[str] = field(default_factory=list)
    score: float | None = None  # 子题分值
    # 切片文本（P4E.1）：由 content_slicer 按行号切片填充，L2 标注层不产生。
    stem: str = ""              # 子题题干文本
    options: list[dict] | None = None  # 子题选项 [{"label": "A", "text": "..."}]
    # 展示契约 v0.4 字段
    stem_region: dict | None = None  # {"start": "题干区开始", "end": "题干区结束"}
    answer_region: dict | None = None  # {"start": "答案区开始", "end": "答案区结束"}
    explanation_region: dict | None = None  # {"start": "详解区开始", "end": "详解区结束"}
    scoring_standard: str | None = None  # 评分标准
    answer_images: list[dict] = field(default_factory=list)  # 答案图片
    sub_sub_questions: list["L2SubQuestion"] | None = None  # recursive nested sub-questions


# ── L2 标注 ──────────────────────────────────────────────────────


@dataclass
class L2QuestionAnnotation:
    """L2 单题标注：LLM 输出的行号引用和元数据。"""

    question_number: str
    question_type: str         # single_choice / multiple_choice / fill_blank / ...
    original_question_type: str | None = None  # LLM raw fine-grained type (cloze/grammar_fill/...)
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
    answer_structure: dict | None = None
    word_bank: list[str] | None = None
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
    # 展示契约 v0.4 字段
    scoring_standard: str | None = None  # 评分标准（如"每空1分，任选3小题完成"）
    answer_images: list[dict] = field(default_factory=list)  # 答案图片


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
    annotation_version: str | None = None  # Prompt 版本标记（用于 A/B 对比可追溯性）


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
    original_question_type: str | None = None  # LLM raw fine-grained type (cloze/grammar_fill/...)
    stem: str = ""
    options: list[dict[str, str]] = field(default_factory=list)  # [{"label": "A", "text": "..."}]
    answer: str | None = None
    answer_structure: dict | None = None
    word_bank: list[str] | None = None
    explanation: str | None = None
    section_id: str | None = None
    shared_material_line_ids: list[str] = field(default_factory=list)  # 共享材料的 L1 行号
    # 展示契约 v0.4 字段（2026-08-30）
    stem_line_ids: list[str] = field(default_factory=list)             # 题干行号
    answer_line_ids: list[str] = field(default_factory=list)           # 答案行号
    explanation_line_ids: list[str] = field(default_factory=list)      # 详解行号
    shared_material_notes_line_ids: list[str] = field(default_factory=list)  # 文言注释行号
    # 区域标记（仅 golden 校验和切片元数据，不进前端）
    stem_region: dict | None = None          # {"start": "题干区开始", "end": "题干区结束"}
    answer_region: dict | None = None        # {"start": "答案区开始", "end": "答案区结束"}
    explanation_region: dict | None = None   # {"start": "详解区开始", "end": "详解区结束"}
    # 内容字段
    scoring_standard: str | None = None      # 评分标准
    shared_material: str | None = None       # 共享材料文本
    shared_material_notes: str | None = None  # 文言注释文本
    # 图片关联
    answer_images: list[dict] = field(default_factory=list)  # 答案图片列表
    difficulty: int | None = None
    score: float | None = None
    knowledge_points: list[str] = field(default_factory=list)
    confidence: float = 0.5
    source_page: int | None = None
    # Phase 2C：Structure Signature（Annotation，非事实）
    structure_signature: dict | None = None
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


def deserialize_l2_from_json(data: dict) -> L2DocumentAnnotation:
    """从 JSON 字典反序列化为 L2DocumentAnnotation。

    与 _serialize_l2_for_persistence 互逆，用于 A/B 对比加载 L2。
    """

    def _parse_sub(raw: dict) -> L2SubQuestion:
        return L2SubQuestion(
            qno=str(raw.get("qno", "")),
            question_type=raw.get("question_type"),
            stem_line_ids=raw.get("stem_line_ids", []),
            options_line_ids=raw.get("options_line_ids", {}),
            answer=raw.get("answer"),
            answer_line_ids=raw.get("answer_line_ids", []),
            explanation_line_ids=raw.get("explanation_line_ids", []),
            knowledge_points=raw.get("knowledge_points", []),
            score=raw.get("score"),
            stem=raw.get("stem", ""),
            options=raw.get("options"),
            scoring_standard=raw.get("scoring_standard"),
            answer_images=raw.get("answer_images", []),
            sub_sub_questions=(
                [_parse_sub(s) for s in raw.get("sub_sub_questions", [])]
                if raw.get("sub_sub_questions") else None
            ),
        )

    questions: list[L2QuestionAnnotation] = []
    for q in data.get("questions", []):
        subs = None
        if q.get("sub_questions"):
            subs = [_parse_sub(s) for s in q["sub_questions"]]
        questions.append(L2QuestionAnnotation(
            question_number=str(q.get("question_number", "")),
            question_type=q.get("question_type", "unknown"),
            original_question_type=q.get("original_question_type"),
            section_id=q.get("section_id"),
            stem_start_marker=q.get("stem_start_marker"),
            stem_end_marker=q.get("stem_end_marker"),
            shared_material_line_ids=q.get("shared_material_line_ids", []),
            stem_line_ids=q.get("stem_line_ids", []),
            options_line_ids=q.get("options_line_ids", {}),
            answer=q.get("answer"),
            answer_structure=q.get("answer_structure"),
            word_bank=q.get("word_bank"),
            answer_line_ids=q.get("answer_line_ids", []),
            explanation_line_ids=q.get("explanation_line_ids", []),
            difficulty=q.get("difficulty"),
            score=q.get("score"),
            knowledge_points=q.get("knowledge_points", []),
            confidence=q.get("confidence", 0.5),
            source_page=q.get("source_page"),
            structure_signature=q.get("structure_signature"),
            is_composite=q.get("is_composite", False),
            sub_questions=subs,
            scoring_standard=q.get("scoring_standard"),
            answer_images=q.get("answer_images", []),
        ))

    corrected_anchors = [
        CorrectedAnchor(
            field=a["field"],
            llm_line_ids=a.get("llm_line_ids", []),
            corrected_line_ids=a.get("corrected_line_ids", []),
            anchor_status=a.get("anchor_status", "unknown"),
            validation_passed=a.get("validation_passed", False),
            evidence=a.get("evidence"),
            question_number=a.get("question_number"),
        )
        for a in data.get("corrected_anchors", [])
    ]

    return L2DocumentAnnotation(
        filename=data.get("filename", ""),
        subject=data.get("subject"),
        grade=data.get("grade"),
        year=data.get("year"),
        school=data.get("school"),
        questions=questions,
        metadata_confidence=data.get("metadata_confidence", 0.5),
        warnings=data.get("warnings", []),
        corrected_anchors=corrected_anchors,
        anchor_status_summary=data.get("anchor_status_summary", {}),
        annotation_version=data.get("annotation_version"),
    )
