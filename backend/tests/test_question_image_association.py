"""P0-1 严格测试：_build_question_images 使用真实 SlicedQuestion 结构。

审计发现（bugs.md BUG-012 §四 D）：
- `_build_question_images` 原先用 `getattr(q, "stem_line_ids")` / `getattr(q, "options_line_ids")`
  读行号，但生产 SlicedQuestion（schemas_l2.L142-179）**没有这两个属性**，
  行号实际存放在 `stem_anchor.corrected_line_ids` 与 `corrected_anchors`（field 前缀 option_）。
- 结果是 stem/options 分支在生产环境永不执行，配图关联率仅 15.5%（1426→221 张）。
- 原单测用 MagicMock 暴露假属性，掩盖了真实结构差异（单测全绿、生产失效）。

本测试用**真实 SlicedQuestion / CorrectedAnchor 结构**构造，修复前必然失败、
修复后必须通过；同时断言输出补齐了 page_no/bbox/source/figure_id 元数据（P1-8）。
"""

from app.domains.document.pipeline import (
    _build_question_images,
    _question_field_line_ids,
    _question_option_line_ids,
)
from app.domains.document.schemas_l1 import L1Document, L1Image, L1Line, L1Page
from app.domains.document.schemas_l2 import CorrectedAnchor, SlicedQuestion


def _line(line_id: str, text: str, bbox: dict) -> L1Line:
    return L1Line(
        line_id=line_id, page_no=1, line_no_in_page=1, order=1,
        text=text, block_type="text", bbox=bbox, source="ppsv3",
    )


def _doc(lines: list[L1Line], images: list[L1Image]) -> L1Document:
    return L1Document(
        filename="t.pdf", pages=[L1Page(page_no=1, lines=lines)],
        lines=lines, images=images, source="ppsv3", total_pages=1,
    )


def _image(image_id: str, bbox: dict, page_no: int = 1) -> L1Image:
    return L1Image(
        image_id=image_id, page_no=page_no, bbox=bbox,
        source="ppsv3", figure_id=f"fig-{image_id}",
        placement="unknown",
    )


def _real_question(
    qno: str,
    stem_line_ids: list[str],
    option_line_ids: list[str] | None = None,
) -> SlicedQuestion:
    """构造真实 SlicedQuestion：行号只放 anchor 结构，不设 stem_line_ids 属性。"""
    stem_anchor = CorrectedAnchor(
        field="stem",
        llm_line_ids=list(stem_line_ids),
        corrected_line_ids=list(stem_line_ids),
        anchor_status="exact",
        validation_passed=True,
    )
    corrected_anchors = [stem_anchor]
    if option_line_ids:
        for i, lid in enumerate(option_line_ids):
            label = chr(ord("A") + i)
            corrected_anchors.append(CorrectedAnchor(
                field=f"option_{label}",
                llm_line_ids=[lid],
                corrected_line_ids=[lid],
                anchor_status="exact",
                validation_passed=True,
            ))
    q = SlicedQuestion(
        question_number=qno,
        question_type="single_choice",
        stem="1. 测试题干",
        options=[{"label": "A", "text": "x"}],
        confidence=0.9,
        stem_anchor=stem_anchor,
        corrected_anchors=corrected_anchors,
        answer_line_ids=["P2L001"],
    )
    # 明确不设置这些属性：验证修复后从 anchor 读取（此前 getattr 返回 None）
    assert not hasattr(q, "stem_line_ids")
    assert not hasattr(q, "options_line_ids")
    return q


class TestRealSlicedQuestionStructure:
    """用真实 SlicedQuestion 结构验证配图关联（修复前必然失败）。"""

    def test_stem_image_associated_via_anchor(self):
        """图片在 stem 行 bbox 内 → 关联为 stem（行号从 stem_anchor 读取）。"""
        stem_line = _line("P1L001", "1. 题干", {"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        img = _image("img1", {"x1": 200, "y1": 210, "x2": 400, "y2": 250})
        doc = _doc([stem_line], [img])
        q = _real_question("1", stem_line_ids=["P1L001"])

        result = _build_question_images([q], doc.images, doc)

        assert len(result) == 1, f"应关联 1 张图，实际 {result}"
        assert result[0]["question_number"] == "1"
        assert result[0]["image_id"] == "img1"
        assert result[0]["placement"] == "stem"

    def test_options_image_associated_via_corrected_anchors(self):
        """图片在选项行 bbox 内 → 关联为 options（行号从 corrected_anchors 读取）。"""
        stem_line = _line("P1L001", "1. 题干", {"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        opt_line = _line("P1L002", "A. 选项", {"x1": 100, "y1": 230, "x2": 300, "y2": 250})
        img = _image("img2", {"x1": 150, "y1": 235, "x2": 250, "y2": 260})
        doc = _doc([stem_line, opt_line], [img])
        q = _real_question("1", stem_line_ids=["P1L001"], option_line_ids=["P1L002"])

        result = _build_question_images([q], doc.images, doc)

        assert len(result) == 1, f"应关联 1 张图，实际 {result}"
        assert result[0]["placement"] == "options"

    def test_output_includes_full_metadata(self):
        """输出补齐 page_no/bbox/source/figure_id（P1-8，此前只有 3 个 key）。"""
        stem_line = _line("P1L001", "1. 题干", {"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        img = _image("img3", {"x1": 200, "y1": 210, "x2": 400, "y2": 250}, page_no=1)
        doc = _doc([stem_line], [img])
        q = _real_question("1", stem_line_ids=["P1L001"])

        result = _build_question_images([q], doc.images, doc)

        assert len(result) == 1
        entry = result[0]
        for key in ("question_number", "image_id", "placement",
                    "page_no", "bbox", "source", "figure_id"):
            assert key in entry, f"缺少元数据 key: {key}"
        assert entry["page_no"] == 1
        assert entry["bbox"] == {"x1": 200, "y1": 210, "x2": 400, "y2": 250}
        assert entry["source"] == "ppsv3"
        assert entry["figure_id"] == "fig-img3"

    def test_stem_priority_over_options(self):
        """图片同时命中 stem 与 options 行 → 优先 stem。"""
        stem_line = _line("P1L001", "1. 题干", {"x1": 100, "y1": 200, "x2": 500, "y2": 220})
        opt_line = _line("P1L002", "A. 选项", {"x1": 100, "y1": 200, "x2": 300, "y2": 220})
        img = _image("img4", {"x1": 200, "y1": 205, "x2": 250, "y2": 215})
        doc = _doc([stem_line, opt_line], [img])
        q = _real_question("1", stem_line_ids=["P1L001"], option_line_ids=["P1L002"])

        result = _build_question_images([q], doc.images, doc)

        assert result[0]["placement"] == "stem"

    def test_answer_line_ids_still_supported(self):
        """answer_line_ids 属性路径保留（答案区图片关联为 answer_area）。"""
        ans_line = _line("P2L001", "1. C", {"x1": 100, "y1": 300, "x2": 200, "y2": 320})
        img = _image("img5", {"x1": 110, "y1": 305, "x2": 180, "y2": 325}, page_no=2)
        # 只放 P2L001 在 doc 中，stem/options 行都不在 → 走 answer 路径
        doc = _doc([ans_line], [img])
        q = _real_question("1", stem_line_ids=["P1L001"])

        result = _build_question_images([q], doc.images, doc)

        assert result[0]["placement"] == "answer_area"


class TestQuestionFieldLineIdsHelpers:
    """辅助函数：从真实结构读取行号。"""

    def test_field_line_ids_reads_stem_anchor(self):
        q = _real_question("1", stem_line_ids=["P1L001", "P1L002"])
        assert _question_field_line_ids(q, "stem") == ["P1L001", "P1L002"]

    def test_field_line_ids_fallback_to_attribute(self):
        """兼容测试 mock：直接暴露 stem_line_ids 属性时回退读取。"""
        from unittest.mock import MagicMock
        q = MagicMock()
        q.stem_line_ids = ["P1L001"]
        q.stem_anchor = None
        assert _question_field_line_ids(q, "stem") == ["P1L001"]

    def test_option_line_ids_from_corrected_anchors(self):
        q = _real_question("1", stem_line_ids=["P1L001"],
                           option_line_ids=["P1L002", "P1L003"])
        assert sorted(_question_option_line_ids(q)) == ["P1L002", "P1L003"]

    def test_option_line_ids_fallback_to_dict_attribute(self):
        from unittest.mock import MagicMock
        q = MagicMock()
        q.options_line_ids = {"A": ["P1L002"], "B": ["P1L003"]}
        q.corrected_anchors = []
        assert sorted(_question_option_line_ids(q)) == ["P1L002", "P1L003"]
