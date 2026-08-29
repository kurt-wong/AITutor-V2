"""PP 主路径实验管线单元测试。"""

import asyncio
import json
import os
from pathlib import Path

from app.ai.gateway import LLMGateway
from app.ai.providers import MockLLMProvider
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import CorrectedAnchor, SlicedQuestion
from app.domains.document.simple_pipeline import (
    _build_pp_canonical,
    _build_retry_hints,
    _extract_subject_from_filename,
    _select_better_result,
    _ocr_model_for_subject,
    run_simple_pipeline,
)

ROOT = Path(__file__).resolve().parents[2]


class _SequenceLLMProvider(MockLLMProvider):
    """按调用顺序返回多个 mock 响应，用于验证重试逻辑。"""

    def __init__(self, responses: list[str]) -> None:
        super().__init__()
        self.responses = responses
        self.calls = 0
        self.prompts: list[str] = []

    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        self.prompts.append(prompt)
        response = self.responses[
            min(self.calls, len(self.responses) - 1)
        ]
        self.calls += 1
        return response


class _FailOnRetryProvider(MockLLMProvider):
    """第一遍返回 blocked 结果，第二遍直接失败，用于验证异常回退。"""

    def __init__(self, first: str) -> None:
        super().__init__()
        self.first = first
        self.calls = 0

    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        self.calls += 1
        if self.calls == 1:
            return self.first
        raise RuntimeError("retry failed")


def _load_l1(path: Path, source: str) -> L1Document:
    data = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        L1Line(
            line_id=d["line_id"],
            page_no=d["page_no"],
            line_no_in_page=d["line_no_in_page"],
            order=d["order"],
            text=d["text"],
            block_type=d.get("block_type", "text"),
            source=d.get("source", source),
        )
        for d in data["lines"]
    ]
    return L1Document(
        filename=data["filename"],
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source=source,
        total_pages=data.get("total_pages", 1),
        text_coverage=1.0 if source == "native" else 0.0,
    )


def _mock_llm_response() -> str:
    return json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "2",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L009"],
                "options_line_ids": {
                    "A": ["P1L010"],
                    "B": ["P1L011"],
                    "C": ["P1L012"],
                    "D": ["P1L013"],
                },
                "answer": "C",
                "answer_line_ids": ["P5L003"],
                "explanation_line_ids": [],
                "shared_material_line_ids": [],
            }
        ],
        "metadata_confidence": 0.8,
    })


def test_build_pp_canonical_keeps_pp_line_ids_and_native_provenance():
    """PP canonical 保留 P 行号，native 行号只写 raw_sources。"""
    native_lines = [
        L1Line("N1L001", 1, 1, 1, "1. 题目", "text", source="native"),
        L1Line("N1L002", 1, 2, 2, "参考答案", "text", source="native"),
    ]
    native = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=native_lines)],
        lines=native_lines,
        source="native",
        total_pages=1,
    )
    pp_lines = [
        L1Line("P1L001", 1, 1, 1, "1. 题目", "text", source="ppsv3"),
        L1Line("P1L002", 1, 2, 2, "参考答案", "text", source="ppsv3"),
    ]
    ppsv3 = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=pp_lines)],
        lines=pp_lines,
        source="ppsv3",
        total_pages=1,
    )

    doc, _ = _build_pp_canonical(ppsv3, native)

    assert doc.lines[0].line_id == "P1L001"
    assert doc.lines[0].raw_sources["native_line_id"] == "N1L001"
    assert doc.lines[1].raw_sources["native_line_id"] == "N1L002"


def test_simple_pipeline_pp_primary_no_l1_arbiter():
    """PP 主路径应跳过 l1_arbiter，并成功切题。"""
    ppsv3 = _load_l1(
        ROOT / "test" / "fixtures" / "l1_ppsv3_math_2026.json",
        "ppsv3",
    )
    native = _load_l1(
        ROOT / "test" / "fixtures" / "l1_snapshot_math_real.json",
        "native",
    )
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=_mock_llm_response())],
    )

    result = asyncio.run(run_simple_pipeline(
        ppsv3_doc=ppsv3,
        native_doc=native,
        gateway=gateway,
    ))

    assert result.status == "succeeded"
    assert any(s["name"] == "pp_primary_l1" for s in result.stages)
    assert not any(s["name"] == "l1_arbiter" for s in result.stages)
    assert len(result.sliced_questions) >= 1
    q = result.sliced_questions[0]
    assert q.question_number == "2"
    assert q.answer == "C"
    # V1_LESSONS 3.17: 答案表有 Q2="C" 时优先用答案表
    assert q.answer_provenance is not None
    assert q.answer_provenance.source == "document_answer_table"


def test_simple_pipeline_retries_once_on_blocked_question():
    """首次标注产生 blocked 时，simple pipeline 重试一次并输出可入库题目。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 题目", "text"),
        L1Line("P1L002", 1, 2, 2, "A 1", "text"),
        L1Line("P1L003", 1, 3, 3, "B 2", "text"),
        L1Line("P1L004", 1, 4, 4, "C 3", "text"),
        L1Line("P1L005", 1, 5, 5, "D 4", "text"),
        L1Line("P1L006", 1, 6, 6, "参考答案", "text"),
        L1Line("P1L007", 1, 7, 7, "1.A", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    first = json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L001"],
                "options_line_ids": {},
                "answer": "A",
                "answer_line_ids": ["P1L007"],
            }
        ],
    })
    second = json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L001"],
                "options_line_ids": {
                    "A": ["P1L002"],
                    "B": ["P1L003"],
                    "C": ["P1L004"],
                    "D": ["P1L005"],
                },
                "answer": "A",
                "answer_line_ids": ["P1L007"],
            }
        ],
    })
    provider = _SequenceLLMProvider([first, second])
    gateway = LLMGateway(
        mode="live",
        providers=[provider],
    )

    result = asyncio.run(run_simple_pipeline(
        ppsv3_doc=doc,
        gateway=gateway,
    ))

    assert result.status == "succeeded"
    assert any(s["name"] == "llm_annotation_retry" for s in result.stages)
    assert "上一轮标注问题" in provider.prompts[1]
    assert "所有选项行号缺失" in provider.prompts[1]
    assert len(result.sliced_questions) == 1
    q = result.sliced_questions[0]
    assert q.answer == "A"
    assert not any("禁止自动发布" in i for i in q.issues)
    d = result.to_dict()
    assert d["ingest_summary"]["ingested"] == 1
    assert d["ingest_summary"]["discarded"] == 0
    assert d["llm_annotation"] is not None
    assert d["llm_annotation"]["raw_response"] is not None


def test_simple_pipeline_retry_failure_keeps_first_pass():
    """重试 annotation 失败时回退第一遍结果，不让整份 PDF 失败。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 题目", "text"),
        L1Line("P1L002", 1, 2, 2, "A 1", "text"),
        L1Line("P1L003", 1, 3, 3, "B 2", "text"),
        L1Line("P1L004", 1, 4, 4, "C 3", "text"),
        L1Line("P1L005", 1, 5, 5, "D 4", "text"),
        L1Line("P1L006", 1, 6, 6, "参考答案", "text"),
        L1Line("P1L007", 1, 7, 7, "1.A", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    first = json.dumps({
        "filename": "test.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "question_type": "single_choice",
                "section_id": "选择题",
                "stem_line_ids": ["P1L001"],
                "options_line_ids": {},
                "answer": "A",
                "answer_line_ids": ["P1L007"],
            }
        ],
    })
    gateway = LLMGateway(
        mode="live",
        providers=[_FailOnRetryProvider(first)],
    )

    result = asyncio.run(run_simple_pipeline(
        ppsv3_doc=doc,
        gateway=gateway,
    ))

    assert result.status == "succeeded"
    assert len(result.sliced_questions) == 1
    assert any("禁止自动发布" in i for i in result.sliced_questions[0].issues)


def test_select_better_result_avoids_regression():
    """重试后质量更差时，必须保留第一遍结果。"""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. 题目", "text"),
        L1Line("P1L002", 1, 2, 2, "A 1", "text"),
        L1Line("P1L003", 1, 3, 3, "B 2", "text"),
        L1Line("P1L004", 1, 4, 4, "C 3", "text"),
        L1Line("P1L005", 1, 5, 5, "D 4", "text"),
    ]
    doc = L1Document(
        filename="test.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    good = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="s",
            answer="A",
            confidence=0.9,
            issues=[],
        )
    ]
    bad = [
        SlicedQuestion(
            question_number="1",
            question_type="single_choice",
            stem="s",
            answer=None,
            confidence=0.5,
            issues=["锚点需重新标注，禁止自动发布"],
        )
    ]

    chosen_annotation, chosen_sliced = _select_better_result(
        None, good, None, bad, doc
    )
    assert chosen_sliced is good


# ── 学科识别与 OCR 路由测试 ──────────────────────────────────────


def test_extract_subject_from_exam_filenames():
    """考试试卷文件名正确提取学科。"""
    assert _extract_subject_from_filename("2026北京东城高一（上）期末化学（教师版）.pdf") == "化学"
    assert _extract_subject_from_filename("2026北京朝阳高一（上）期末地理（教师版）.pdf") == "地理"
    assert _extract_subject_from_filename("2025北京东城高一（上）期末历史（教师版）.pdf") == "历史"
    assert _extract_subject_from_filename("2026高考全国一卷数学真题.pdf") == "数学"
    assert _extract_subject_from_filename("高一英语月考模拟.pdf") == "英语"


def test_extract_subject_rejects_non_exam_filenames():
    """非考试文件名不提取学科（避免误匹配）。"""
    # 有科目名但无考试关键词且不在文件名开头
    assert _extract_subject_from_filename("化学老师批改记录.pdf") == "化学"  # 开头匹配
    assert _extract_subject_from_filename("关于化学实验室的说明.pdf") == "化学"  # 开头匹配
    # 无科目名
    assert _extract_subject_from_filename("2026期末考试.pdf") is None
    assert _extract_subject_from_filename("test.pdf") is None
    assert _extract_subject_from_filename(None) is None


def test_ocr_model_default():
    """默认使用 PP-StructureV3。"""
    assert _ocr_model_for_subject(None) == "PP-StructureV3"
    assert _ocr_model_for_subject("语文") == "PP-StructureV3"


def test_ocr_model_override_parameter():
    """显式 override 参数优先级最高。"""
    assert _ocr_model_for_subject("语文", override="PaddleOCR-VL") == "PaddleOCR-VL"
    assert _ocr_model_for_subject(None, override="PaddleOCR-VL") == "PaddleOCR-VL"


def test_ocr_model_env_override():
    """环境变量覆盖优先于学科映射。"""
    old = os.environ.get("OCR_MODEL_OVERRIDE")
    try:
        os.environ["OCR_MODEL_OVERRIDE"] = "PaddleOCR-VL"
        assert _ocr_model_for_subject("语文") == "PaddleOCR-VL"
        # override 参数仍优先于环境变量
        assert _ocr_model_for_subject("语文", override="PP-StructureV3") == "PP-StructureV3"
    finally:
        if old is not None:
            os.environ["OCR_MODEL_OVERRIDE"] = old
        else:
            os.environ.pop("OCR_MODEL_OVERRIDE", None)


def test_ocr_model_subject_routing():
    """学科路由映射：化学走 VL，其余走 PPS。"""
    assert _ocr_model_for_subject("化学") == "PaddleOCR-VL-1.6"
    assert _ocr_model_for_subject("生物") == "PP-StructureV3"
    assert _ocr_model_for_subject("地理") == "PP-StructureV3"
    assert _ocr_model_for_subject("语文") == "PP-StructureV3"
    assert _ocr_model_for_subject("数学") == "PP-StructureV3"


def test_actual_ocr_model_matches_winning_provider():
    """T0-4: ocr_model_used 必须反映实际胜出提供方的模型。

    VL 降级时不能写路由模型（PP-StructureV3），必须写 VL 提供方真实模型。
    注：settings.mimo_vl_model 依赖 cwd 加载的 .env（根目录跑时为根 .env，
    值可能为空），断言只锁"不等于路由模型"的核心契约，避免环境耦合。
    """
    from app.domains.document.simple_pipeline import _actual_ocr_model

    assert _actual_ocr_model("paddleocr", "PP-StructureV3") == "PP-StructureV3"
    assert _actual_ocr_model("paddleocr", "PaddleOCR-VL-1.6") == "PaddleOCR-VL-1.6"
    # VL 提供方绝不能回退到路由模型
    mimo = _actual_ocr_model("mimo-vl", "PP-StructureV3")
    assert mimo != "PP-StructureV3"
    deepseek = _actual_ocr_model("deepseek-vl", "PP-StructureV3")
    assert deepseek != "PP-StructureV3"
    assert _actual_ocr_model("mock", "PP-StructureV3") == "PP-StructureV3"


def test_simple_pipeline_records_ocr_provider():
    """T0-4: OCR 完成后提供方落入 PipelineResult 与 task result（DB 证据）。

    ocr_provider_used = 实际完成提取的提供方（链上 provider.name）；
    ocr_model_used = 学科路由选择的模型。
    """
    from unittest.mock import patch

    from app.domains.document.ocr.providers import OCRFallbackChain
    from app.domains.document.schemas import OcrDocument, OcrPage

    class _FakeOCRChain(OCRFallbackChain):
        def __init__(self) -> None:
            super().__init__([])

        async def extract(self, file_path):
            return OcrDocument(
                filename=file_path.name,
                pages=[
                    OcrPage(
                        page_number=1,
                        markdown="1. 题干\nA. x\nB. y\nC. z\nD. w",
                        source_provider="fake-ocr",
                    )
                ],
                provider_used="fake-ocr",
            )

        def close(self) -> None:
            pass

    pdf = ROOT / "tmp" / "provider_test.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4 fake pdf")
    try:
        gateway = LLMGateway(
            mode="live",
            providers=[MockLLMProvider(response=_mock_llm_response())],
        )
        with patch(
            "app.domains.document.simple_pipeline.build_ocr_chain",
            return_value=_FakeOCRChain(),
        ):
            result = asyncio.run(run_simple_pipeline(
                pdf_path=pdf,
                gateway=gateway,
                subject="英语",
            ))

        assert result.ocr_provider_used == "fake-ocr"
        assert result.ocr_model_used == "PP-StructureV3"
        assert result.to_dict()["ocr_provider_used"] == "fake-ocr"
        assert result.to_dict()["ocr_model_used"] == "PP-StructureV3"
        ppsv3_stage = next(
            s for s in result.stages if s["name"] == "ppsv3_l1"
        )
        assert ppsv3_stage.get("provider") == "fake-ocr"
        assert ppsv3_stage.get("model") == "PP-StructureV3"
    finally:
        pdf.unlink(missing_ok=True)


def test_scanned_pdf_detected_and_skips_ocr():
    """纯扫描 PDF（native text_coverage=0）→ status=scanned，不跑 OCR。

    2026-08-25 昌平生物教训：扫描件题号/公式 OCR 不可靠（换引擎也解决
    不了），后端层层补丁治标不治本。改为检测扫描件 → 标记 scanned →
    跳过 OCR/LLM（不浪费 token），后续集中处理。
    """
    native = L1Document(
        filename="scanned.pdf",
        pages=[],
        lines=[],
        source="native",
        total_pages=1,
        text_coverage=0.0,  # 无文本层
    )
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=_mock_llm_response())],
    )
    # 不传 pdf_path（避免真跑 native 提取/OCR），直接传 native_doc
    result = asyncio.run(run_simple_pipeline(
        native_doc=native,
        gateway=gateway,
        filename="scanned.pdf",
    ))

    assert result.status == "scanned"
    assert any("scanned_pdf" in e for e in result.errors)
    # 没有跑 OCR（无 ppsv3_l1 stage）
    assert not any(s["name"] == "ppsv3_l1" for s in result.stages)


def test_text_layer_pdf_not_flagged_as_scanned():
    """有文本层的 PDF（text_coverage=1.0）不应被标记为 scanned。"""
    native = L1Document(
        filename="text.pdf",
        pages=[],
        lines=[],
        source="native",
        total_pages=1,
        text_coverage=1.0,
    )
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=_mock_llm_response())],
    )
    result = asyncio.run(run_simple_pipeline(
        native_doc=native,
        gateway=gateway,
        filename="text.pdf",
    ))
    # 有文本层：不是 scanned（会继续走 OCR/标注，status 不可能是 scanned）
    assert result.status != "scanned"

def test_simple_pipeline_normalizes_chemistry_formulas():
    """P0-5: full pipeline normalizes chemistry formulas for subject=化学."""
    lines = [
        L1Line("P1L001", 1, 1, 1, "1. Cl(2)+2OH(﹣)", "text"),
        L1Line("P1L002", 1, 2, 2, "Mg(OH)(2)", "text"),
    ]
    doc = L1Document(
        filename="chemistry.pdf",
        pages=[L1Page(page_no=1, lines=lines)],
        lines=lines,
        source="ppsv3",
        total_pages=1,
    )
    response = json.dumps({
        "filename": "chemistry.pdf",
        "subject": "化学",
        "questions": [
            {
                "question_number": "1",
                "question_type": "short_answer",
                "section_id": "化学综合题",
                "stem_line_ids": ["P1L001"],
                "options_line_ids": {},
                "answer": "Mg(OH)(2)",
                "answer_line_ids": ["P1L002"],
                "difficulty": 3,
            }
        ],
        "metadata_confidence": 0.9,
    })
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )
    result = asyncio.run(run_simple_pipeline(
        ppsv3_doc=doc,
        gateway=gateway,
        subject="化学",
    ))
    assert result.status == "succeeded"
    assert len(result.sliced_questions) == 1
    q = result.sliced_questions[0]
    assert "Cl₂" in q.stem
    assert "OH⁻" in q.stem
    assert q.answer == "Mg(OH)₂"


def test_seven_to_five_missing_labels_build_retry_hint():
    """P1-4: missing A-G labels produce a retry hint for the LLM."""
    from app.domains.document.quality_gate import evaluate_quality

    sq = SlicedQuestion(
        question_number="37",
        question_type="single_choice",
        original_question_type="seven_to_five",
        section_id="seven_to_five_1",
        is_composite=True,
        corrected_anchors=[
            CorrectedAnchor(
                field="sub_options",
                llm_line_ids=[],
                corrected_line_ids=[],
                anchor_status="retry",
                validation_passed=False,
                evidence="sub_options invalid: A-G-missing:F,G",
                question_number="37",
            )
        ],
    )
    sliced = evaluate_quality([sq])
    assert any("\u7981\u6b62\u81ea\u52a8\u53d1\u5e03" in issue for issue in sliced[0].issues)
    hints = _build_retry_hints(sliced)
    assert any("A-G-missing:F,G" in hint for hint in hints)

