"""P0-5 严格测试：综合题共享材料独立于 stem。

审计发现（PIPELINE_AUDIT_2026_08_22.md §二 A）：
- prompt L518 明文要求综合题 stem_line_ids = 材料全文 + 子题行号 →
  材料整段并入题干（英语完形/阅读 stem 达 2000-2600 字符）。
- content_slicer._merge_question_group L210 显式把材料行并入 stem。

修复（三层）：
1. prompt：stem_line_ids 只含子题行号，材料只在 shared_material_line_ids
2. _slice_single_question：从 stem_line_ids 剔除 shared_material_line_ids（双保险）
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

    def test_material_lines_removed_from_stem_for_independent(self):
        """独立题：共享材料行从 stem 剔除。"""
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

        # 独立题 stem 不含材料行
        assert "共享材料" not in (sq.stem or "")
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
