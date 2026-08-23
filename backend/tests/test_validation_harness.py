"""验证框架（Validation Harness）测试 — WP1 门禁行为。

覆盖 test/scripts/run_live_validation.py 的 generate_report 门禁逻辑：
  - overall=PASS 只允许 mode=live_pp 且全部阈值通过
  - 答案为空超阈值必须 FAIL
  - golden 指标缺失必须 FAIL
  - mock 结果必须持久化且有对应 JSON 文件
"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "scripts"))

import run_live_validation as rlv
import run_phase1_eval as rpe

GOLDEN_FIELDS = rlv.GOLDEN_FIELDS


def _full_golden(correct: int = 8, total: int = 8) -> dict:
    return {f: {"correct": correct, "total": total} for f in GOLDEN_FIELDS}


def _good_quality(**overrides) -> dict:
    q = {
        "math": {"question_count": 21, "answer_matched": 21, "answer_empty": 0,
                 "answer_empty_ratio": 0.0, "high_conf": 13, "blocked": 8,
                 "questions_with_issues": 21, "total_issues": 30},
        "english": {"question_count": 54, "answer_matched": 54, "answer_empty": 0,
                    "answer_empty_ratio": 0.0, "high_conf": 40, "blocked": 0,
                    "questions_with_issues": 54, "total_issues": 60},
        "physics": {"question_count": 20, "answer_matched": 20, "answer_empty": 0,
                    "answer_empty_ratio": 0.0, "high_conf": 15, "blocked": 0,
                    "questions_with_issues": 20, "total_issues": 25},
    }
    for k, v in overrides.items():
        q[k] = v
    return q


def _good_report_kwargs(**overrides) -> dict:
    kwargs = dict(
        mode="live_pp",
        mock_results={
            "math": {"status": "succeeded", "question_count": 1, "errors": [], "_elapsed_s": 0.3},
            "english": {"status": "succeeded", "question_count": 1, "errors": [], "_elapsed_s": 1.6},
            "physics": {"status": "succeeded", "question_count": 1, "errors": [], "_elapsed_s": 0.2},
        },
        live_runs={
            "math": [{"status": "succeeded", "question_count": 21, "errors": [], "_elapsed_s": 470.0}],
            "english": [{"status": "succeeded", "question_count": 54, "errors": [], "_elapsed_s": 800.0}],
            "physics": [{"status": "succeeded", "question_count": 20, "errors": [], "_elapsed_s": 477.0}],
        },
        reproducibility={"math": [], "english": [], "physics": []},
        golden_accuracy={
            "math": _full_golden(), "english": _full_golden(), "physics": _full_golden(),
        },
        quality=_good_quality(),
        ppsv3_sources={"math": "real_ocr", "english": "real_ocr", "physics": "real_ocr"},
        ocr_attempted=True,
    )
    for k, v in overrides.items():
        kwargs[k] = v
    return kwargs


def test_report_requires_live_pp_mode():
    """mode 不是 live_pp 时 overall 必须 FAIL。"""
    for bad_mode in ("native_mock_pp", "native_only", None):
        report = rlv.generate_report(**_good_report_kwargs(mode=bad_mode))
        assert report["overall"] == "FAIL", f"mode={bad_mode!r} 必须 FAIL"
        assert any("live_pp" in f for f in report["failures"]), (
            f"mode={bad_mode!r} 的 failures 应包含 mode 原因: {report['failures']}"
        )

    # 对照：mode=live_pp 且全部阈值通过 → PASS
    report = rlv.generate_report(**_good_report_kwargs())
    assert report["overall"] == "PASS", f"live_pp 全过必须 PASS: {report['failures']}"
    assert report["failures"] == []


def test_report_fails_on_empty_answers():
    """英语 answer_empty 超阈值时报告必须 FAIL（原始总数口径）。"""
    q = _good_quality()
    q["english"] = {"question_count": 54, "answer_matched": 0, "answer_empty": 54,
                    "answer_empty_ratio": 1.0, "high_conf": 0, "blocked": 54,
                    "questions_with_issues": 54, "total_issues": 54}
    report = rlv.generate_report(**_good_report_kwargs(quality=q))
    assert report["overall"] == "FAIL"
    assert any("english" in f and "answer_empty" in f for f in report["failures"]), (
        f"failures 应指出英语答案为空: {report['failures']}"
    )


def test_report_fails_when_short_answer_empty_exceeds_threshold():
    """解答题（short_answer）空答案同样计入 answer_empty（不得自我放宽）。"""
    # 数学：5 题解答题空答案 → answer_empty=5/21=23.8% > 5% → FAIL
    q = _good_quality()
    q["math"] = {"question_count": 21, "answer_matched": 16, "answer_empty": 5,
                 "answer_empty_ratio": 0.238, "high_conf": 11, "blocked": 10,
                 "questions_with_issues": 21, "total_issues": 30}
    report = rlv.generate_report(**_good_report_kwargs(quality=q))
    assert report["overall"] == "FAIL", (
        f"解答题空答案 23.8% > 5% 必须 FAIL（不得按题型放宽）: {report['failures']}"
    )
    assert any("math" in f and "answer_empty" in f for f in report["failures"])


def test_report_fails_when_golden_metrics_missing():
    """golden 指标缺失（缺字段或整科缺失）时报告必须 FAIL。"""
    # 缺 stem_content 字段
    partial = {f: {"correct": 8, "total": 8} for f in GOLDEN_FIELDS if f != "stem_content"}
    ga = _good_report_kwargs()["golden_accuracy"]
    ga["english"] = partial
    report = rlv.generate_report(**_good_report_kwargs(golden_accuracy=ga))
    assert report["overall"] == "FAIL"
    assert any("english" in f and "stem_content" in f for f in report["failures"]), (
        f"failures 应指出 golden 缺 stem_content: {report['failures']}"
    )

    # 整科 golden 缺失（None）
    ga2 = _good_report_kwargs()["golden_accuracy"]
    ga2["physics"] = None
    report2 = rlv.generate_report(**_good_report_kwargs(golden_accuracy=ga2))
    assert report2["overall"] == "FAIL"
    assert any("physics" in f and "missing" in f for f in report2["failures"]), (
        f"failures 应指出 physics golden 缺失: {report2['failures']}"
    )


def test_report_contains_mock_run_files(tmp_path):
    """report["mock"] 非空，且每个 mock run 有对应 JSON 文件。"""
    kwargs = _good_report_kwargs()
    report = rlv.generate_report(**kwargs)
    assert report["mock"], "report[\"mock\"] 不能为空"
    assert set(report["mock"].keys()) == {"math", "english", "physics"}

    # mock run 必须持久化为 JSON 文件（模拟 main() 的写入行为）
    for subject, r in kwargs["mock_results"].items():
        out_path = tmp_path / f"mock_{subject}.json"
        out_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        assert out_path.exists(), f"mock_{subject}.json 应存在"
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        assert loaded["status"] == r["status"]
        assert loaded["question_count"] == r["question_count"]


# ── check_reproducibility 内部重复检测 ────────────────────


def _make_run_result(questions: list[dict]) -> dict:
    return {"status": "succeeded", "questions": questions}


class _FakePipelineResult:
    def __init__(self, **data):
        self._data = data

    def to_dict(self) -> dict:
        return dict(self._data)


def test_check_reproducibility_detects_duplicate_stem_line_ids():
    """同一 run 内 stem_line_ids 重复时，check_reproducibility 必须报错。"""
    questions = [
        {"question_number": "15", "question_type": "short_answer",
         "answer": "42", "stem_line_ids": ["P5L008", "P5L009", "P6L006", "P6L006"]},
    ]
    run_a = _make_run_result(questions)
    run_b = _make_run_result(questions)
    errors = rlv.check_reproducibility(run_a, run_b)
    dup_errors = [e for e in errors if "duplicates" in e]
    assert dup_errors, (
        f"Q15 stem_line_ids 重复 P6L006 应被检测到: {errors}"
    )


def test_check_reproducibility_no_false_positive_for_unique_ids():
    """stem_line_ids 无重复时不误报。"""
    questions = [
        {"question_number": "15", "question_type": "short_answer",
         "answer": "42", "stem_line_ids": ["P5L008", "P5L009", "P6L006", "P6L007"]},
    ]
    run_a = _make_run_result(questions)
    run_b = _make_run_result(questions)
    errors = rlv.check_reproducibility(run_a, run_b)
    dup_errors = [e for e in errors if "duplicates" in e]
    assert not dup_errors, f"无重复时不误报: {dup_errors}"


def test_check_reproducibility_detects_answer_line_id_diff():
    """两次运行的 answer_line_ids 不同时，check_reproducibility 必须报错。"""
    run_a = _make_run_result([
        {"question_number": "21", "question_type": "short_answer",
         "answer": "不存在", "stem_line_ids": ["P8L001"],
         "answer_line_ids": ["P8L001", "P9L001"]},
    ])
    run_b = _make_run_result([
        {"question_number": "21", "question_type": "short_answer",
         "answer": "不存在", "stem_line_ids": ["P8L001"],
         "answer_line_ids": ["P8L001", "P8L007", "P9L001"]},
    ])
    errors = rlv.check_reproducibility(run_a, run_b)
    assert any("answer_line_ids" in e for e in errors), errors


def test_check_reproducibility_normalizes_numbered_answer_prefixes():
    run_a = _make_run_result([
        {"question_number": "21", "question_type": "short_answer",
         "answer": "21. a variety of 22. prohibited 23. ahead of",
         "stem_line_ids": ["P8L001"], "answer_line_ids": ["P9L001"]},
    ])
    run_b = _make_run_result([
        {"question_number": "21", "question_type": "short_answer",
         "answer": "(21) a variety of (22) prohibited (23) ahead of",
         "stem_line_ids": ["P8L001"], "answer_line_ids": ["P9L001"]},
    ])
    errors = rlv.check_reproducibility(run_a, run_b)
    assert errors == [], errors


def test_check_reproducibility_normalizes_cloze_to_single_choice():
    run_a = _make_run_result([
        {
            "question_number": "1",
            "question_type": "cloze",
            "answer": "A",
            "stem_line_ids": ["P1L001"],
            "answer_line_ids": ["P5L001"],
        },
    ])
    run_b = _make_run_result([
        {
            "question_number": "1",
            "question_type": "single_choice",
            "answer": "A",
            "stem_line_ids": ["P1L001"],
            "answer_line_ids": ["P5L001"],
        },
    ])
    errors = rlv.check_reproducibility(run_a, run_b)
    assert errors == [], errors


def test_check_reproducibility_composite_compares_subquestion_contract():
    run_a = _make_run_result([
        {
            "question_number": "21",
            "question_type": "fill_in",
            "is_composite": True,
            "answer": "21. a variety of 22. prohibited",
            "stem_line_ids": ["P2L017"],
            "answer_line_ids": ["P11L024", "P11L025"],
            "sub_questions": [
                {"qno": "21", "answer": "a variety of"},
                {"qno": "22", "answer": "prohibited"},
            ],
        },
    ])
    run_b = _make_run_result([
        {
            "question_number": "21",
            "question_type": "fill_in",
            "is_composite": True,
            "answer": "a variety of",
            "stem_line_ids": ["P2L002", "P2L003", "P2L004"],
            "answer_line_ids": ["P11L024", "P11L025"],
            "sub_questions": [
                {"qno": "21", "answer": "a variety of"},
                {"qno": "22", "answer": "prohibited"},
            ],
        },
    ])
    errors = rlv.check_reproducibility(run_a, run_b)
    assert errors == [], errors


def test_normalize_answer_text_strips_score_suffix():
    """分值后缀不应影响 golden answer 比较。"""
    assert rpe.normalize_answer_text("B (2分)") == rpe.normalize_answer_text("B")
    assert rpe.normalize_answer_text("B（2分公式1分结果1分）") == rpe.normalize_answer_text("B")


def test_normalize_answer_text_latex_equivalence():
    """LaTeX 格式差异不应被误判为答案错误。"""
    assert rpe.normalize_answer_text(r"$\frac{\sqrt{2}}{2}$") == rpe.normalize_answer_text("sqrt(2)/2")
    assert rpe.normalize_answer_text(r"(-\infty,-8]\cup[6,+\infty)") == rpe.normalize_answer_text("(-inf,-8]U[6,+inf)")


# ── run_one 超时与进度回调 ─────────────────────────────────


def test_run_one_timeout_returns_failed_run(monkeypatch):
    """单次 run 超过 run_timeout 时，run_one 必须返回 status=failed 而不是无限等待。"""
    async def slow_run_pipeline(**kwargs):
        callback = kwargs.get("progress_callback")
        if callback is not None:
            await callback("llm_annotation", 0.4)
        await asyncio.sleep(10)
        raise AssertionError("超时后不应继续执行")

    monkeypatch.setattr(rlv, "run_pipeline", slow_run_pipeline)
    result = asyncio.run(
        rlv.run_one(
            None,
            gateway=None,
            label="live:math:run1",
            run_timeout=0.05,
        )
    )
    assert result["status"] == "failed"
    assert result["question_count"] == 0
    assert "timed out" in result["errors"][0]
    assert result["_label"] == "live:math:run1"


def test_run_one_exception_returns_failed_run(monkeypatch):
    """run_pipeline 异常时，run_one 应落盘为 failed run，而不是让验证脚本崩溃。"""
    async def boom_run_pipeline(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(rlv, "run_pipeline", boom_run_pipeline)
    result = asyncio.run(
        rlv.run_one(None, gateway=None, label="live:physics:run2", run_timeout=5)
    )
    assert result["status"] == "failed"
    assert "boom" in result["errors"][0]


def test_run_one_forwards_progress_callback(monkeypatch):
    """run_one 必须把进度回调传给 run_pipeline，供 stage 进度输出使用。"""
    seen: list[tuple[str, float]] = []

    async def fake_run_pipeline(**kwargs):
        callback = kwargs.get("progress_callback")
        assert callback is not None, "run_one 必须传入 progress_callback"
        await callback("dual_source_merge", 0.3)
        await callback("llm_annotation", 0.4)
        return _FakePipelineResult(status="succeeded", questions=[])

    monkeypatch.setattr(rlv, "run_pipeline", fake_run_pipeline)

    async def capture_progress(stage: str, progress: float) -> None:
        seen.append((stage, progress))

    result = asyncio.run(
        rlv.run_one(
            None,
            gateway=None,
            label="live:english:run1",
            run_timeout=5,
            progress_callback=capture_progress,
        )
    )
    assert result["status"] == "succeeded"
    assert ("dual_source_merge", 0.3) in seen
    assert ("llm_annotation", 0.4) in seen
