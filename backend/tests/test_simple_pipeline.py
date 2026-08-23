"""PP 主路径实验管线单元测试。"""

import asyncio
import json
import os
from pathlib import Path

from app.ai.gateway import LLMGateway
from app.ai.providers import MockLLMProvider
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import SlicedQuestion
from app.domains.document.simple_pipeline import (
    _build_pp_canonical,
    _extract_subject_from_filename,
    _ocr_model_for_subject,
    _select_better_result,
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
