"""P0-5 严格测试：综合题共享材料独立于 stem。

审计发现（bugs.md BUG-012 §二 A）：
- prompt L518 明文要求综合题 stem_line_ids = 材料全文 + 子题行号 →
  材料整段并入题干（英语完形/阅读 stem 达 2000-2600 字符）。
- content_slicer._merge_question_group L210 显式把材料行并入 stem。

修复（三层）：
1. prompt：stem_line_ids 只含子题行号，材料只在 shared_material_line_ids
2. _slice_single_question：材料行并入 stem（材料在前，去重；2026-08-25 修订为
   综合题与带共享材料的独立题统一并入——旧 P0-5 独立题剔除材料导致语文
   材料阅读/文言文题目失去材料上下文）
3. _merge_question_group：合并 stem 不含材料行（材料保留为元数据）

本测试断言 prompt 文本 + 两条切片路径的真实行为。
"""

from app.domains.document.content_slicer import (
    _merge_question_group,
    _slice_single_question,
    slice_questions,
)
from app.domains.document.line_annotator import ANNOTATION_PROMPT
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import (
    CorrectedAnchor,
    L2DocumentAnnotation,
    L2QuestionAnnotation,
    SlicedQuestion,
)


def _doc() -> L1Document:
    lines = [
        L1Line("P1L001", 1, 1, 1, "这是一段共享材料的第一行。", "text"),
        L1Line("P1L002", 1, 2, 2, "这是共享材料的第二行内容。", "text"),
        L1Line("P1L003", 1, 3, 3, "1. 第一道子题题干", "text"),
        L1Line("P1L004", 1, 4, 4, "A. 选项1", "text"),
        L1Line("P1L005", 1, 5, 5, "B. 选项2", "text"),
        L1Line("P1L006", 1, 6, 6, "C. 选项3", "text"),
        L1Line("P1L007", 1, 7, 7, "D. 选项4", "text"),
        L1Line("P1L008", 1, 8, 8, "2. 第二道子题题干", "text"),
    ]
    return L1Document(
        filename="test.pdf", pages=[L1Page(page_no=1, lines=lines)],
        lines=lines, source="ppsv3", total_pages=1,
    )


class TestPromptCompositeMaterialSeparate:
    def test_stem_line_ids_exclude_material_in_prompt(self):
        """prompt 必须要求 stem_line_ids 不含材料行。"""
        assert "只包含子题题干行号" in ANNOTATION_PROMPT
        assert "不包含共享材料行" in ANNOTATION_PROMPT
        assert "材料行只放 shared_material_line_ids" in ANNOTATION_PROMPT

    def test_old_inclusive_wording_removed(self):
        """旧表述"材料全文 + 所有子题的行号"必须移除。"""
        assert "材料全文 + 所有子题的行号" not in ANNOTATION_PROMPT


class TestSliceSingleQuestionMaterialExcluded:
    def test_material_lines_kept_in_stem_for_composite(self):
        """综合题：stem 包含材料行（前端展示需要连贯性）。"""
        doc = _doc()
        q = L2QuestionAnnotation(
            question_number="1",
            question_type="single_choice",
            stem_line_ids=["P1L001", "P1L002", "P1L003"],
            options_line_ids={},
            shared_material_line_ids=["P1L001", "P1L002"],
            is_composite=True,
        )
        line_by_id = {l.line_id: l for l in doc.lines}
        sq = _slice_single_question(q, line_by_id, {})

        # 综合题 stem 包含材料和子题
        assert "共享材料" in (sq.stem or "")
        assert "第一道子题题干" in (sq.stem or "")
        assert sq.shared_material_line_ids == ["P1L001", "P1L002"]

    def test_material_lines_kept_in_stem_for_independent(self):
        """独立题带共享材料：材料行并入 stem（2026-08-25 修订）。

        旧行为（P0-5）从独立题 stem 剔除材料 → 语文材料阅读/文言文等
        LLM 标为独立的共享材料题失去材料上下文，题目无法独立使用
        （报告材料覆盖 0%）。共享材料是题目的必要上下文，无论综合/独立
        都应自包含。
        """
        doc = _doc()
        q = L2QuestionAnnotation(
            question_number="1",
            question_type="single_choice",
            stem_line_ids=["P1L001", "P1L002", "P1L003"],
            options_line_ids={},
            shared_material_line_ids=["P1L001", "P1L002"],
            is_composite=False,
        )
        line_by_id = {l.line_id: l for l in doc.lines}
        sq = _slice_single_question(q, line_by_id, {})

        # 独立题 stem 包含材料 + 题干（材料在前）
        assert "共享材料" in (sq.stem or "")
        assert "第一道子题题干" in (sq.stem or "")
        assert sq.shared_material_line_ids == ["P1L001", "P1L002"]

    def test_no_material_question_unchanged(self):
        """无材料的独立题：stem 原样，不误伤。"""
        doc = _doc()
        q = L2QuestionAnnotation(
            question_number="1",
            question_type="single_choice",
            stem_line_ids=["P1L003"],
            options_line_ids={},
            shared_material_line_ids=[],
        )
        line_by_id = {l.line_id: l for l in doc.lines}
        sq = _slice_single_question(q, line_by_id, {})
        assert "第一道子题题干" in (sq.stem or "")


class TestMergeQuestionGroupMaterialExcluded:
    def _sub_q(self, qno: str, stem_lids: list[str]) -> SlicedQuestion:
        anchor = CorrectedAnchor(
            field="stem", llm_line_ids=list(stem_lids),
            corrected_line_ids=list(stem_lids),
            anchor_status="exact", validation_passed=True,
        )
        return SlicedQuestion(
            question_number=qno, question_type="single_choice",
            stem="", options=[], confidence=0.9,
            stem_anchor=anchor, corrected_anchors=[anchor],
            shared_material_line_ids=["P1L001", "P1L002"],
        )

    def test_merged_stem_contains_material_and_subquestions(self):
        """合并综合题 stem 包含材料 + 子题行（前端展示需要连贯性）。"""
        doc = _doc()
        line_by_id = {l.line_id: l for l in doc.lines}
        group = [
            self._sub_q("1", ["P1L001", "P1L002", "P1L003"]),
            self._sub_q("2", ["P1L001", "P1L002", "P1L008"]),
        ]
        merged = _merge_question_group(group, line_by_id)

        stem = merged.stem or ""
        # 材料在 stem 中
        assert "共享材料" in stem
        # 子题题干在 stem 中
        assert "第一道子题题干" in stem
        assert "第二道子题题干" in stem
        # 元数据保留
        assert merged.shared_material_line_ids == ["P1L001", "P1L002"]
        assert merged.is_composite is True

    def test_merge_through_slice_questions_integration(self):
        """端到端：slice_questions 对综合题 → stem 包含材料 + 子题。"""
        doc = _doc()
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[
                L2QuestionAnnotation(
                    question_number="1",
                    question_type="single_choice",
                    stem_line_ids=["P1L001", "P1L002", "P1L003"],
                    options_line_ids={},
                    shared_material_line_ids=["P1L001", "P1L002"],
                    is_composite=True,
                ),
            ],
        )
        result = slice_questions(annotation, doc)
        assert len(result) == 1
        # 综合题 stem 包含材料
        assert "共享材料" in (result[0].stem or "")
        assert "第一道子题题干" in (result[0].stem or "")


class TestMergeQuestionGroupOptionsPreserved:
    """P0-G-2 测试：_merge_question_group 合并时保留子题选项。"""

    def _sub_q_with_options(self, qno: str, stem_lids: list[str], options: list[dict]) -> SlicedQuestion:
        anchor = CorrectedAnchor(
            field="stem", llm_line_ids=list(stem_lids),
            corrected_line_ids=list(stem_lids),
            anchor_status="exact", validation_passed=True,
        )
        return SlicedQuestion(
            question_number=qno, question_type="single_choice",
            stem="", options=options, confidence=0.9,
            stem_anchor=anchor, corrected_anchors=[anchor],
            shared_material_line_ids=["P1L001", "P1L002"],
        )

    def test_options_aggregated_from_sub_questions(self):
        """子题有选项时，合并后 options 应包含这些选项。"""
        doc = _doc()
        line_by_id = {l.line_id: l for l in doc.lines}
        group = [
            self._sub_q_with_options("1", ["P1L003"], [
                {"label": "A", "text": "选项1"},
                {"label": "B", "text": "选项2"},
            ]),
            self._sub_q_with_options("2", ["P1L008"], [
                {"label": "A", "text": "选项3"},
                {"label": "B", "text": "选项4"},
            ]),
        ]
        merged = _merge_question_group(group, line_by_id)

        # 合并后应有选项
        assert len(merged.options) > 0, "合并后 options 不应为空"
        # 按 label 去重：A 和 B 各保留一个
        labels = [opt["label"] for opt in merged.options]
        assert labels == ["A", "B"], f"label 去重后应为 ['A', 'B']，实际 {labels}"

    def test_options_empty_when_sub_questions_have_no_options(self):
        """子题无选项时，合并后 options 为空。"""
        doc = _doc()
        line_by_id = {l.line_id: l for l in doc.lines}
        group = [
            self._sub_q_with_options("1", ["P1L003"], []),
            self._sub_q_with_options("2", ["P1L008"], []),
        ]
        merged = _merge_question_group(group, line_by_id)
        assert merged.options == [], "子题无选项时合并后 options 应为空"

    def test_options_dedup_by_label(self):
        """子题选项有重复 label 时，去重正确。"""
        doc = _doc()
        line_by_id = {l.line_id: l for l in doc.lines}
        group = [
            self._sub_q_with_options("1", ["P1L003"], [
                {"label": "A", "text": "选项1"},
                {"label": "B", "text": "选项2"},
                {"label": "C", "text": "选项3"},
            ]),
            self._sub_q_with_options("2", ["P1L008"], [
                {"label": "A", "text": "选项4"},  # 重复 A
                {"label": "B", "text": "选项5"},  # 重复 B
                {"label": "D", "text": "选项6"},  # 新增 D
            ]),
        ]
        merged = _merge_question_group(group, line_by_id)

        labels = [opt["label"] for opt in merged.options]
        assert labels == ["A", "B", "C", "D"], f"去重后应为 ['A','B','C','D']，实际 {labels}"
        # A 保留第一个子题的值
        a_opt = next(opt for opt in merged.options if opt["label"] == "A")
        assert a_opt["text"] == "选项1", f"A 保留第一个子题的值，实际 {a_opt['text']}"


class TestCompositeMaterialKeptSeparate:
    """归回测试：composite 容器 stem 只放任务说明，材料放 shared_material。

    DISPLAY_CONTRACT v0.5：综合题容器不是独立题目，
    不把整篇文章拼进 stem。
    """

    def test_material_kept_in_shared_material(self):
        """stem_line_ids 不含材料行时，材料只保留在 shared_material。"""
        doc = _doc()
        q = L2QuestionAnnotation(
            question_number="1",
            question_type="single_choice",
            stem_line_ids=["P1L003"],  # 只有子题行，不含材料
            options_line_ids={},
            shared_material_line_ids=["P1L001", "P1L002"],  # 材料行
            is_composite=True,
        )
        line_by_id = {l.line_id: l for l in doc.lines}
        sq = _slice_single_question(q, line_by_id, {})

        assert "共享材料" not in (sq.stem or "")
        assert "第一道子题题干" in (sq.stem or "")
        assert "共享材料" in (sq.shared_material or "")

    def test_material_stays_in_shared_material(self):
        """材料行不进入容器 stem，保持分离展示。"""
        doc = _doc()
        q = L2QuestionAnnotation(
            question_number="1",
            question_type="single_choice",
            stem_line_ids=["P1L003"],
            options_line_ids={},
            shared_material_line_ids=["P1L001", "P1L002"],
            is_composite=True,
        )
        line_by_id = {l.line_id: l for l in doc.lines}
        sq = _slice_single_question(q, line_by_id, {})

        assert sq.stem == "1. 第一道子题题干"
        assert sq.shared_material == "这是一段共享材料的第一行。\n这是共享材料的第二行内容。"

    def test_no_duplicate_when_stem_ids_already_include_material(self):
        """stem_line_ids 已含材料行时，保持 L2 行号不重复。"""
        doc = _doc()
        q = L2QuestionAnnotation(
            question_number="1",
            question_type="single_choice",
            stem_line_ids=["P1L001", "P1L002", "P1L003"],  # 已含材料
            options_line_ids={},
            shared_material_line_ids=["P1L001", "P1L002"],
            is_composite=True,
        )
        line_by_id = {l.line_id: l for l in doc.lines}
        sq = _slice_single_question(q, line_by_id, {})

        lines = (sq.stem or "").split("\n")
        assert len(lines) == 3, f"应有3行（不重复），实际 {len(lines)} 行: {lines}"

    def test_independent_question_with_material_merges_and_dedupes(self):
        """独立题带共享材料：材料并入 stem 且去重。"""
        doc = _doc()
        q = L2QuestionAnnotation(
            question_number="1",
            question_type="single_choice",
            stem_line_ids=["P1L001", "P1L003"],
            options_line_ids={},
            shared_material_line_ids=["P1L001"],
            is_composite=False,
        )
        line_by_id = {l.line_id: l for l in doc.lines}
        sq = _slice_single_question(q, line_by_id, {})

        lines = (sq.stem or "").split("\n")
        assert lines[0] == "这是一段共享材料的第一行。"
        assert len(lines) == 2
        assert "第一道子题题干" in (sq.stem or "")

    def test_end_to_end_material_stays_separate(self):
        """端到端：综合题容器 stem 不包含材料。"""
        doc = _doc()
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[
                L2QuestionAnnotation(
                    question_number="1",
                    question_type="single_choice",
                    stem_line_ids=["P1L003"],
                    options_line_ids={},
                    shared_material_line_ids=["P1L001", "P1L002"],
                    is_composite=True,
                ),
            ],
        )
        result = slice_questions(annotation, doc)
        assert len(result) == 1
        assert "共享材料" not in (result[0].stem or "")
        assert "第一道子题题干" in (result[0].stem or "")
        assert "共享材料" in (result[0].shared_material or "")
class TestL2PersistenceFields:
    """P0-G-3 测试：L2 持久化包含 shared_material_line_ids 和 stem_markers。"""

    def test_serialization_includes_shared_material(self):
        """序列化后 JSON 包含 shared_material_line_ids。"""
        from app.worker.document_worker import _serialize_l2_for_persistence
        from app.domains.document.schemas_l2 import L2DocumentAnnotation, L2SubQuestion

        l2 = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[
                L2QuestionAnnotation(
                    question_number="1",
                    question_type="single_choice",
                    stem_line_ids=["P1L001", "P1L002"],
                    options_line_ids={"A": ["P1L003"]},
                    shared_material_line_ids=["P1L001"],
                    is_composite=True,
                    sub_questions=[
                        L2SubQuestion(qno="1", question_type="single_choice", answer="A"),
                    ],
                ),
            ],
        )

        result = _serialize_l2_for_persistence(l2)
        q = result["questions"][0]

        assert "shared_material_line_ids" in q, "序列化应包含 shared_material_line_ids"
        assert q["shared_material_line_ids"] == ["P1L001"], f"值应为 ['P1L001']，实际 {q['shared_material_line_ids']}"

    def test_serialization_includes_stem_markers(self):
        """序列化后 JSON 包含 stem_start_marker 和 stem_end_marker。"""
        from app.worker.document_worker import _serialize_l2_for_persistence

        l2 = L2DocumentAnnotation(
            filename="test.pdf",
            questions=[
                L2QuestionAnnotation(
                    question_number="1",
                    question_type="single_choice",
                    stem_line_ids=["P1L001"],
                    options_line_ids={},
                    stem_start_marker="1. 题目开始",
                    stem_end_marker="D. 选项结束",
                ),
            ],
        )

        result = _serialize_l2_for_persistence(l2)
        q = result["questions"][0]

        assert "stem_start_marker" in q, "序列化应包含 stem_start_marker"
        assert "stem_end_marker" in q, "序列化应包含 stem_end_marker"
        assert q["stem_start_marker"] == "1. 题目开始"
        assert q["stem_end_marker"] == "D. 选项结束"
