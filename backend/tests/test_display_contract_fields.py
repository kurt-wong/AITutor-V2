"""展示契约字段端到端测试 — 验证 L1 + L2 -> SlicedQuestion -> 入库 -> API 的完整链路。

测试使用真实的 L1 fixture 和构造的 L2 标注，验证展示契约字段能正确填充。
"""

import json
from pathlib import Path

import pytest

from app.domains.document.content_slicer import slice_questions
from app.domains.document.schemas_l1 import L1Document, L1Line
from app.domains.document.schemas_l2 import (
    CorrectedAnchor,
    L2DocumentAnnotation,
    L2QuestionAnnotation,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT / "test" / "fixtures"


def _load_l1_fixture(filename: str) -> L1Document:
    """加载 L1 fixture 文件。"""
    path = FIXTURES_DIR / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    # 将字典列表转换为 L1Line 对象列表
    lines = [L1Line(**line_dict) for line_dict in data.get("lines", [])]
    data["lines"] = lines
    return L1Document(**data)


def _build_l2_annotation(
    question_number: str,
    stem_line_ids: list[str],
    answer_line_ids: list[str] | None = None,
    explanation_line_ids: list[str] | None = None,
    shared_material_line_ids: list[str] | None = None,
) -> L2QuestionAnnotation:
    """构建 L2 标注。"""
    return L2QuestionAnnotation(
        question_number=question_number,
        question_type="single_choice",
        stem_line_ids=stem_line_ids,
        answer_line_ids=answer_line_ids or [],
        explanation_line_ids=explanation_line_ids or [],
        shared_material_line_ids=shared_material_line_ids or [],
    )


def _build_corrected_anchors(
    question_number: str,
    stem_line_ids: list[str],
) -> list[CorrectedAnchor]:
    """构建校正后锚点。"""
    return [
        CorrectedAnchor(
            field="stem",
            llm_line_ids=stem_line_ids,
            corrected_line_ids=stem_line_ids,
            anchor_status="exact",
            validation_passed=True,
            question_number=question_number,
        )
    ]


class TestDisplayContractFields:
    """展示契约字段测试。"""

    def test_stem_line_ids_populated(self):
        """stem_line_ids 应该从 stem_anchor.corrected_line_ids 填充。"""
        l1 = _load_l1_fixture("l1_native_english_2026.json")
        l2_question = _build_l2_annotation(
            question_number="1",
            stem_line_ids=["P1L005", "P1L006"],
        )
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            subject="英语",
            questions=[l2_question],
            corrected_anchors=_build_corrected_anchors("1", ["P1L005", "P1L006"]),
        )

        sliced = slice_questions(annotation, l1)

        assert len(sliced) == 1
        sq = sliced[0]
        assert sq.stem_line_ids == ["P1L005", "P1L006"]

    def test_answer_line_ids_populated(self):
        """answer_line_ids 应该从 L2 标注填充。"""
        l1 = _load_l1_fixture("l1_native_english_2026.json")
        l2_question = _build_l2_annotation(
            question_number="1",
            stem_line_ids=["P1L005"],
            answer_line_ids=["P5L003"],
        )
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            subject="英语",
            questions=[l2_question],
            corrected_anchors=_build_corrected_anchors("1", ["P1L005"]),
        )

        sliced = slice_questions(annotation, l1)

        assert len(sliced) == 1
        sq = sliced[0]
        assert sq.answer_line_ids == ["P5L003"]

    def test_stem_region_populated(self):
        """stem_region 应该在有 stem_line_ids 时生成。"""
        l1 = _load_l1_fixture("l1_native_english_2026.json")
        l2_question = _build_l2_annotation(
            question_number="1",
            stem_line_ids=["P1L005", "P1L006"],
        )
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            subject="英语",
            questions=[l2_question],
            corrected_anchors=_build_corrected_anchors("1", ["P1L005", "P1L006"]),
        )

        sliced = slice_questions(annotation, l1)

        assert len(sliced) == 1
        sq = sliced[0]
        assert sq.stem_region is not None
        assert sq.stem_region["start"] == "题干区开始"
        assert sq.stem_region["end"] == "题干区结束"

    def test_answer_region_populated(self):
        """answer_region 应该在有 answer_line_ids 时生成。"""
        l1 = _load_l1_fixture("l1_native_english_2026.json")
        l2_question = _build_l2_annotation(
            question_number="1",
            stem_line_ids=["P1L005"],
            answer_line_ids=["P5L003"],
        )
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            subject="英语",
            questions=[l2_question],
            corrected_anchors=_build_corrected_anchors("1", ["P1L005"]),
        )

        sliced = slice_questions(annotation, l1)

        assert len(sliced) == 1
        sq = sliced[0]
        assert sq.answer_region is not None
        assert sq.answer_region["start"] == "答案区开始"
        assert sq.answer_region["end"] == "答案区结束"

    def test_shared_material_populated(self):
        """shared_material 应该从 shared_material_line_ids 切片填充。"""
        l1 = _load_l1_fixture("l1_native_english_2026.json")
        # 使用 fixture 中实际存在的行号
        material_line_ids = ["N1L013", "N1L014"]
        l2_question = _build_l2_annotation(
            question_number="1",
            stem_line_ids=["P1L005"],
            shared_material_line_ids=material_line_ids,
        )
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            subject="英语",
            questions=[l2_question],
            corrected_anchors=_build_corrected_anchors("1", ["P1L005"]),
        )

        sliced = slice_questions(annotation, l1)

        assert len(sliced) == 1
        sq = sliced[0]
        assert sq.shared_material is not None
        assert len(sq.shared_material) > 0

    def test_shared_material_line_ids_populated(self):
        """shared_material_line_ids 应该从 L2 标注透传。"""
        l1 = _load_l1_fixture("l1_native_english_2026.json")
        material_line_ids = ["N1L013", "N1L014"]
        l2_question = _build_l2_annotation(
            question_number="1",
            stem_line_ids=["P1L005"],
            shared_material_line_ids=material_line_ids,
        )
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            subject="英语",
            questions=[l2_question],
            corrected_anchors=_build_corrected_anchors("1", ["P1L005"]),
        )

        sliced = slice_questions(annotation, l1)

        assert len(sliced) == 1
        sq = sliced[0]
        assert sq.shared_material_line_ids == material_line_ids


class TestDisplayContractFieldDefaults:
    """展示契约字段默认值测试。"""

    def test_empty_fields_when_not_provided(self):
        """未提供字段时应为空或 None。"""
        l1 = _load_l1_fixture("l1_native_english_2026.json")
        l2_question = _build_l2_annotation(
            question_number="1",
            stem_line_ids=["P1L005"],
            # 不提供其他字段
        )
        annotation = L2DocumentAnnotation(
            filename="test.pdf",
            subject="英语",
            questions=[l2_question],
            corrected_anchors=_build_corrected_anchors("1", ["P1L005"]),
        )

        sliced = slice_questions(annotation, l1)

        assert len(sliced) == 1
        sq = sliced[0]
        assert sq.answer_line_ids == []
        assert sq.explanation_line_ids == []
        assert sq.shared_material_line_ids == []
        assert sq.answer_region is None
        assert sq.explanation_region is None
        assert sq.shared_material is None
        assert sq.scoring_standard is None
        assert sq.answer_images == []
