"""
LLM Provider Smoke Test - Phase 0 Task 0.3

验证 LLM Provider 是否能正确输出 JSON 格式的题目标注结果。

测试内容：
1. JSON 结构合规性
2. 行号范围（不输出 LaTeX）
3. MIMO json_object 行为
4. 无 LaTeX 混入 JSON

运行方式：
    # Mock 模式（默认）
    python -m pytest test/scripts/llm_smoke_test.py -v

    # Live 模式（需要 .env 中 LLM_GATEWAY_MODE=live）
    python test/scripts/llm_smoke_test.py --live

输出：
    - test/scripts/smoke_report.json：Smoke Test 报告
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

import pytest

# 添加 backend 目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.ai.json_utils import parse_json_object


# ── Fixtures 加载 ──────────────────────────────────────────────────


def load_fixture(fixture_name: str) -> dict:
    """从 test/fixtures 加载 L1 fixture。"""
    fixture_path = Path(__file__).parent.parent / "fixtures" / fixture_name
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_l1_text_for_llm(fixture: dict) -> str:
    """从 L1 fixture 提取 LLM 可读文本。

    格式：
        P1L001: 高一数学期中试卷
        P1L002: 一、选择题（每题3分，共30分）
        ...
    """
    lines = []
    for line in fixture["lines"]:
        lines.append(f"{line['line_id']}: {line['text']}")
    for image in fixture.get("images", []):
        bbox = image.get("bbox")
        bbox_text = json.dumps(bbox, ensure_ascii=False) if bbox else "null"
        lines.append(
            f"{image['image_id']}: [图片 page={image['page_no']} bbox={bbox_text} placement={image.get('placement', 'unknown')}]"
        )
    return "\n".join(lines)


# ── Mock Provider ──────────────────────────────────────────────────


class MockLLMProvider:
    """Mock LLM Provider，用于无 API 调用的测试。"""

    def __init__(self, name: str = "mock"):
        self.name = name

    async def complete(
        self,
        prompt: str,
        *,
        temperature: float = 0.2,
    ) -> str:
        """返回 Mock LLM 响应（JSON 格式）。"""
        mock_response = {
            "questions": [
                {
                    "question_number": "1",
                    "question_type": "choice",
                    "section_id": "选择题",
                    "stem_line_range": {"start": 3, "end": 3},
                    "options_line_range": {"start": 4, "end": 4},
                    "difficulty": 1,
                    "score": 3.0,
                    "knowledge_points": ["函数求值"],
                    "confidence": 0.9,
                    "source_page": 1,
                }
            ]
        }
        return json.dumps(mock_response, ensure_ascii=False)


# ── Live Provider ──────────────────────────────────────────────────


def load_dotenv():
    """加载 backend/.env 文件。"""
    env_path = Path(__file__).parent.parent.parent / "backend" / ".env"
    if not env_path.exists():
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                __import__("os").environ.setdefault(key.strip(), value.strip())


def get_live_providers() -> list[tuple[str, str, str, str]]:
    """从环境变量获取 Live Provider 配置。

    返回：[(provider_name, base_url, api_key, model), ...]
    """
    load_dotenv()
    providers = []

    # DeepSeek
    deepseek_url = __import__("os").environ.get("DEEPSEEK_BASE_URL")
    deepseek_key = __import__("os").environ.get("DEEPSEEK_API_KEY")
    deepseek_model = __import__("os").environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
    if deepseek_url and deepseek_key:
        providers.append(("deepseek", deepseek_url, deepseek_key, deepseek_model))

    # MIMO
    mimo_url = __import__("os").environ.get("MIMO_BASE_URL")
    mimo_key = __import__("os").environ.get("MIMO_API_KEY")
    mimo_model = __import__("os").environ.get("MIMO_MODEL", "mimo-v2.5")
    if mimo_url and mimo_key:
        providers.append(("mimo", mimo_url, mimo_key, mimo_model))

    # Qwen VL（注意：配置键是 QWEN_VL_BASE_URL，不是 QWEN_BASE_URL）
    qwen_url = __import__("os").environ.get("QWEN_VL_BASE_URL")
    qwen_key = __import__("os").environ.get("QWEN_VL_API_KEY")
    qwen_model = __import__("os").environ.get("QWEN_VL_MODEL", "qwen-vl-max")
    if qwen_url and qwen_key:
        providers.append(("qwen_vl", qwen_url, qwen_key, qwen_model))

    return providers


def create_live_provider(name: str, base_url: str, api_key: str, model: str):
    """创建 Live Provider 实例。"""
    from app.ai.providers.http import HTTPLLMProvider

    # V1_LESSONS 3.25: MIMO 需要 response_format=json_object 才能稳定返回 JSON
    response_format = {"type": "json_object"} if name == "mimo" else None

    return HTTPLLMProvider(
        name=name,
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=120.0,
        response_format=response_format,
    )


# ── 验证逻辑 ──────────────────────────────────────────────────────


def validate_json_structure(response: str) -> dict:
    """验证 JSON 结构合规性。"""
    try:
        parsed = parse_json_object(response)
    except Exception as e:
        return {"valid": False, "error": f"JSON 解析失败: {e}"}

    if "questions" not in parsed:
        return {"valid": False, "error": "缺少 'questions' 字段"}

    if not isinstance(parsed["questions"], list):
        return {"valid": False, "error": "'questions' 不是数组"}

    return {"valid": True, "parsed": parsed}


def validate_line_ranges(parsed: dict) -> list[str]:
    """验证行号范围（不包含 LaTeX）。"""
    issues = []

    for i, question in enumerate(parsed["questions"]):
        q_num = question.get("question_number", f"#{i+1}")

        # 检查行号范围
        if "stem_line_range" not in question:
            issues.append(f"题目 {q_num}: 缺少 stem_line_range")
        else:
            stem_range = question["stem_line_range"]
            if not isinstance(stem_range.get("start"), int):
                issues.append(f"题目 {q_num}: stem_line_range.start 不是整数")
            if not isinstance(stem_range.get("end"), int):
                issues.append(f"题目 {q_num}: stem_line_range.end 不是整数")

        q_type = str(question.get("question_type") or "").lower()
        options_optional = q_type in {
            "fill",
            "fill_blank",
            "blank",
            "subjective",
            "essay",
            "answer",
            "填空",
            "填空题",
            "主观题",
            "解答题",
            "简答题",
            "计算题",
            "应用题",
            "非选择题",
        }
        choice_like = any(
            marker in q_type
            for marker in ("choice", "select", "单选", "多选", "选择")
        )
        if "options_line_range" not in question:
            if choice_like and not options_optional:
                issues.append(f"题目 {q_num}: 缺少 options_line_range")

        # 检查 LaTeX
        question_str = json.dumps(question, ensure_ascii=False)
        latex_patterns = ["\\frac", "\\sqrt", "\\sum", "\\int", "$$"]
        for pattern in latex_patterns:
            if pattern in question_str:
                issues.append(f"题目 {q_num}: 包含 LaTeX '{pattern}'")

    return issues


# ── Smoke Test ──────────────────────────────────────────────────────


def run_smoke_test(
    provider_name: str,
    provider,
    fixture: dict,
    prompt: str,
) -> dict:
    """运行单个 Provider 的 Smoke Test。"""
    start_time = time.time()
    report = {
        "provider": provider_name,
        "fixture": fixture.get("filename", "unknown"),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "unknown",
        "response_time_ms": 0,
        "json_valid": False,
        "line_range_issues": [],
        "latex_issues": [],
        "error": None,
    }

    try:
        # 构造完整的 LLM prompt（包含 JSON 格式要求）
        full_prompt = f"""分析以下文本中的题目，返回 JSON。

文本内容：
{prompt}

返回格式（只输出 JSON，不要 Markdown 代码块）：
{{"questions": [{{"question_number": "1", "question_type": "choice", "stem_line_range": {{"start": 3, "end": 3}}, "options_line_range": {{"start": 4, "end": 7}}}}]}}"""

        # 调用 Provider
        response = asyncio.run(provider.complete(full_prompt))
        report["response_time_ms"] = int((time.time() - start_time) * 1000)

        # 验证 JSON 结构
        validation = validate_json_structure(response)
        report["json_valid"] = validation["valid"]

        if not validation["valid"]:
            report["status"] = "failed"
            report["error"] = validation["error"]
            return report

        # 验证行号范围
        line_issues = validate_line_ranges(validation["parsed"])
        report["line_range_issues"] = line_issues

        # 统计 LaTeX 问题
        report["latex_issues"] = [
            issue for issue in line_issues if "LaTeX" in issue
        ]

        # 判断状态
        if line_issues:
            report["status"] = "warning"
        else:
            report["status"] = "passed"

    except Exception as e:
        report["status"] = "error"
        report["error"] = str(e)
        report["response_time_ms"] = int((time.time() - start_time) * 1000)

    return report


def save_report(reports: list[dict]) -> Path:
    """保存 Smoke Test 报告。"""
    report_path = Path(__file__).parent / "smoke_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "version": "1.0",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tests": reports,
                "summary": {
                    "total": len(reports),
                    "passed": sum(1 for r in reports if r["status"] == "passed"),
                    "warning": sum(1 for r in reports if r["status"] == "warning"),
                    "failed": sum(1 for r in reports if r["status"] in ("failed", "error")),
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    return report_path


# ── Pytest 测试 ────────────────────────────────────────────────────


class TestLLMSmokeTest:
    """Smoke tests for LLM provider JSON output structure."""

    def test_mock_provider_returns_valid_json(self):
        """Mock Provider 返回有效 JSON。"""
        provider = MockLLMProvider()
        result = asyncio.run(provider.complete("Test prompt"))
        validation = validate_json_structure(result)
        assert validation["valid"], validation.get("error")

    def test_json_contains_line_ranges_not_latex(self):
        """JSON 包含行号范围，不包含 LaTeX。"""
        provider = MockLLMProvider()
        result = asyncio.run(provider.complete("Test prompt"))
        validation = validate_json_structure(result)
        assert validation["valid"]

        issues = validate_line_ranges(validation["parsed"])
        assert not issues, f"发现问题: {issues}"

    def test_fill_question_does_not_require_options_range(self):
        """填空题/主观题允许省略 options_line_range。"""
        parsed = {
            "questions": [
                {
                    "question_number": "4",
                    "question_type": "fill",
                    "stem_line_range": {"start": 19, "end": 19},
                }
            ]
        }
        assert validate_line_ranges(parsed) == []

    def test_chinese_question_type_does_not_require_options_range(self):
        """中文填空题/解答题也允许省略 options_line_range。"""
        parsed = {
            "questions": [
                {
                    "question_number": "6",
                    "question_type": "解答题",
                    "stem_line_range": {"start": 22, "end": 24},
                }
            ]
        }
        assert validate_line_ranges(parsed) == []

    def test_choice_question_still_requires_options_range(self):
        """选择题缺少 options_line_range 仍应告警。"""
        parsed = {
            "questions": [
                {
                    "question_number": "1",
                    "question_type": "单项选择题",
                    "stem_line_range": {"start": 3, "end": 3},
                }
            ]
        }
        assert validate_line_ranges(parsed) != []

    def test_fixture_loads_correctly(self):
        """L1 fixture 加载正确（postprocessed 后 38 行）。"""
        fixture = load_fixture("l1_snapshot.json")
        assert "lines" in fixture
        assert len(fixture["lines"]) == 38
        assert fixture["lines"][0]["line_id"] == "P1L001"

    def test_golden_set_loads_correctly(self):
        """Golden Set 加载正确。"""
        golden_path = Path(__file__).parent.parent / "annotations" / "golden" / "math_exercise_2024.json"
        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)
        assert "questions" in golden
        assert len(golden["questions"]) == 7

        # 检查新增字段
        q1 = golden["questions"][0]
        assert "answer" in q1
        assert "explanation" in q1
        assert "answer_line_ids" in q1
        assert "answer_source" in q1
        assert "explanation_line_ids" in q1
        assert "explanation_source" in q1
        assert "image_ids" in q1

    def test_english_golden_set_loads_correctly(self):
        """English Golden Set 加载正确（10 题，含完形填空共享材料）。"""
        golden_path = Path(__file__).parent.parent / "annotations" / "golden" / "english_exercise_2024.json"
        with open(golden_path, "r", encoding="utf-8") as f:
            golden = json.load(f)
        assert "questions" in golden
        assert len(golden["questions"]) == 10
        assert golden.get("postprocessed") is True

        # 检查所有必要字段（含非空断言）
        for q in golden["questions"]:
            qn = q["question_number"]
            assert "answer" in q and q["answer"], f"Q{qn} 缺少 answer"
            assert "explanation" in q and q["explanation"], f"Q{qn} 缺少 explanation"
            assert "answer_line_ids" in q and len(q["answer_line_ids"]) > 0, f"Q{qn} answer_line_ids 为空"
            assert "answer_source" in q and q["answer_source"], f"Q{qn} 缺少 answer_source"
            assert q.get("explanation_line_ids"), f"Q{qn} explanation_line_ids 为空"
            assert "explanation_source" in q and q["explanation_source"], f"Q{qn} 缺少 explanation_source"
            assert "image_ids" in q, f"Q{qn} 缺少 image_ids"
            # expected_anchor 必须包含 answer_line_ids 和 explanation_line_ids
            anchor = q.get("expected_anchor", {})
            assert "answer_line_ids" in anchor and len(anchor["answer_line_ids"]) > 0, f"Q{qn} expected_anchor.answer_line_ids 为空"
            assert "explanation_line_ids" in anchor and len(anchor["explanation_line_ids"]) > 0, f"Q{qn} expected_anchor.explanation_line_ids 为空"

        # 检查完形填空共享材料题（Q6-Q10，共 5 题共享同一篇材料）
        cloze_q = [q for q in golden["questions"] if q.get("section_id", "").startswith("Part III")]
        assert len(cloze_q) == 5, f"完形填空应有 5 题，实际 {len(cloze_q)} 题"
        for q in cloze_q:
            assert "shared_material_line_ids" in q, f"Q{q['question_number']} 缺少 shared_material_line_ids"

    def test_english_fixture_loads_correctly(self):
        """English L1 fixture 加载正确（postprocessed 后 69 行）。"""
        fixture = load_fixture("l1_snapshot_english.json")
        assert "lines" in fixture
        assert len(fixture["lines"]) == 69
        assert fixture.get("postprocessed") is True
        assert fixture["lines"][0]["line_id"] == "P1L001"
        # 验证选项已拆分（Q1 的 A/B/C/D 各占一行）
        q1_options = [l for l in fixture["lines"] if l["line_id"] in ("P1L004", "P1L005", "P1L006", "P1L007")]
        assert len(q1_options) == 4, "Q1 选项应拆分为 4 行"
        # 验证详解区已存在（Q1-Q10 对应 P1L060-P1L069）
        explanation_lines = [l for l in fixture["lines"] if l["line_id"].startswith("P1L06")]
        assert len(explanation_lines) == 10, "English fixture 应包含 10 行详解"

    def test_extract_l1_text_for_llm(self):
        """extract_l1_text_for_llm 生成正确格式。"""
        fixture = load_fixture("l1_snapshot.json")
        text = extract_l1_text_for_llm(fixture)
        assert "P1L001: 高一数学期中试卷" in text
        assert "P1L003: 1. 已知函数" in text


# ── 独立运行 ──────────────────────────────────────────────────────


def test_mock_provider_standalone():
    """独立测试 Mock Provider。"""
    provider = MockLLMProvider()
    result = asyncio.run(provider.complete("Test prompt"))
    validation = validate_json_structure(result)
    assert validation["valid"]
    print("[PASS] Mock provider returns valid JSON")


def test_fixture_standalone():
    """独立测试 Fixture 加载（postprocessed 后 38 行）。"""
    fixture = load_fixture("l1_snapshot.json")
    assert len(fixture["lines"]) == 38
    print(f"[PASS] Fixture loaded: {len(fixture['lines'])} lines")


def test_golden_set_standalone():
    """独立测试 Golden Set 加载。"""
    golden_path = Path(__file__).parent.parent / "annotations" / "golden" / "math_exercise_2024.json"
    with open(golden_path, "r", encoding="utf-8") as f:
        golden = json.load(f)
    assert len(golden["questions"]) == 7
    print(f"[PASS] Golden set loaded: {len(golden['questions'])} questions")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM Provider Smoke Test")
    parser.add_argument("--live", action="store_true", help="测试 Live Provider")
    args = parser.parse_args()

    print("Running LLM Smoke Tests...")
    print()

    # 加载 fixture
    fixture = load_fixture("l1_snapshot.json")
    # 使用完整 fixture 文本，确保 LLM 有足够上下文
    prompt_text = extract_l1_text_for_llm(fixture)

    reports = []

    # Mock Provider
    mock_provider = MockLLMProvider()
    mock_report = run_smoke_test("mock", mock_provider, fixture, prompt_text)
    reports.append(mock_report)
    print(f"[{mock_report['status'].upper()}] mock: {mock_report['response_time_ms']}ms")

    # Live Provider（如果启用）
    if args.live:
        live_providers = get_live_providers()
        if not live_providers:
            print("[SKIP] 未配置 Live Provider（需要 .env 中设置 DEEPSEEK/MIMO/QWEN_VL 的 BASE_URL 和 API_KEY）")
        else:
            for name, url, key, model in live_providers:
                print(f"[INFO] 测试 Live Provider: {name} ({url}, model={model})")
                try:
                    live_provider = create_live_provider(name, url, key, model)
                    live_report = run_smoke_test(name, live_provider, fixture, prompt_text)
                    reports.append(live_report)
                    print(f"[{live_report['status'].upper()}] {name}: {live_report['response_time_ms']}ms")
                except Exception as e:
                    print(f"[ERROR] {name}: {e}")

    # 保存报告
    report_path = save_report(reports)
    print()
    print(f"报告已保存: {report_path}")

    # 打印摘要
    summary = {
        "passed": sum(1 for r in reports if r["status"] == "passed"),
        "warning": sum(1 for r in reports if r["status"] == "warning"),
        "failed": sum(1 for r in reports if r["status"] in ("failed", "error")),
    }
    print(f"摘要: {summary['passed']} passed, {summary['warning']} warning, {summary['failed']} failed")
