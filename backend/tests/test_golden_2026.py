"""WP4 测试 — 英语/物理 golden 完整性 + line_id 与 L1 fixture 一致性。

注意：golden 当前为 manual_review_draft（status 字段标注，answer 可能待人工核对），
测试验证的是结构与 line_id 可追溯性，不验证 answer 内容正确性（那是人工核对职责）。
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GOLDEN_DIR = ROOT / "test" / "annotations" / "golden"
FIXTURES_DIR = ROOT / "test" / "fixtures"

SUBJECTS = {
    "english": {
        "golden": "english_2026_real_golden.json",
        "fixture": "l1_native_english_2026.json",
        "expected_questions": 54,
    },
    "physics": {
        "golden": "physics_2026_real_golden.json",
        "fixture": "l1_native_physics_2026.json",
        "expected_questions": 20,
    },
}


def _load(subject: str) -> tuple[dict, dict]:
    golden = json.loads((GOLDEN_DIR / SUBJECTS[subject]["golden"]).read_text(encoding="utf-8"))
    fixture = json.loads((FIXTURES_DIR / SUBJECTS[subject]["fixture"]).read_text(encoding="utf-8"))
    return golden, fixture


def test_english_golden_complete():
    """英语 golden：54 题，每题含 expected_content/expected_anchor/answer/answer_line_ids。"""
    golden, _ = _load("english")
    questions = golden["questions"]
    assert len(questions) == 54, f"英语 golden 应为 54 题: {len(questions)}"
    assert golden["l1_fixture"] == "l1_native_english_2026.json"
    for q in questions:
        assert "expected_content" in q, f"Q{q['question_number']} 缺 expected_content"
        assert "expected_anchor" in q, f"Q{q['question_number']} 缺 expected_anchor"
        assert "answer" in q, f"Q{q['question_number']} 缺 answer 字段"
        assert "answer_line_ids" in q, f"Q{q['question_number']} 缺 answer_line_ids 字段"
        assert "question_number" in q and q["question_number"]
        assert "question_type" in q and q["question_type"]
        ec = q["expected_content"]
        assert "stem" in ec and "options" in ec and "answer" in ec


def test_physics_golden_complete():
    """物理 golden：20 题，每题含 expected_content/expected_anchor/answer/answer_line_ids。"""
    golden, _ = _load("physics")
    questions = golden["questions"]
    assert len(questions) == 20, f"物理 golden 应为 20 题: {len(questions)}"
    assert golden["l1_fixture"] == "l1_native_physics_2026.json"
    for q in questions:
        assert "expected_content" in q
        assert "expected_anchor" in q
        assert "answer" in q
        assert "answer_line_ids" in q
        assert q["question_number"] and q["question_type"]


def test_golden_line_ids_exist_in_l1_fixture():
    """golden 中所有 line_id 必须存在于对应 L1 fixture（native 或 PP，canonical 双源）。

    golden 由 live_pp 产物构建（canonical L1 = native + PP 双源合并），
    line_id 可能来自任一源，因此同时检查 native 与 ppsv3 fixture。
    """
    for subject in SUBJECTS:
        golden, native_fixture = _load(subject)
        fixture_ids = {l["line_id"] for l in native_fixture["lines"]}
        ppsv3_path = FIXTURES_DIR / f"l1_ppsv3_{subject}_2026.json"
        if ppsv3_path.exists():
            ppsv3 = json.loads(ppsv3_path.read_text(encoding="utf-8"))
            fixture_ids |= {l["line_id"] for l in ppsv3["lines"]}
        missing: set[str] = set()
        for q in golden["questions"]:
            for lid in (q.get("stem_line_ids") or []):
                if lid not in fixture_ids:
                    missing.add(f"stem:{lid}")
            for label, lids in (q.get("options_line_ids") or {}).items():
                for lid in lids:
                    if lid not in fixture_ids:
                        missing.add(f"option_{label}:{lid}")
            for lid in (q.get("answer_line_ids") or []):
                if lid not in fixture_ids:
                    missing.add(f"answer:{lid}")
            for lid in (q.get("explanation_line_ids") or []):
                if lid not in fixture_ids:
                    missing.add(f"explanation:{lid}")
        assert not missing, f"{subject}: golden 中存在不在 fixture 的 line_id: {sorted(missing)[:10]}"


def test_live_report_compares_all_three_subjects():
    """run_live_validation 对三科均具备 golden 文件，且评估接口返回完整 8 字段结构。

    注意：英语/物理 golden 为 manual_review_draft（answer 来自 live 结果，自证无
    ground truth 意义），因此本测试只验证接口可用性与字段结构，**不评估准确率**；
    不得用 golden 自身作为 result 做自证评估。
    """
    sys.path.insert(0, str(ROOT / "test" / "scripts"))
    import run_live_validation as rlv
    from run_live_validation import GOLDEN_FIELDS

    LV = ROOT / "test" / "results" / "live_validation"

    # 三科 golden 路径都必须指向存在的文件
    for subject in ("math", "english", "physics"):
        info = rlv.SUBJECTS[subject]
        assert info["golden"].exists(), (
            f"{subject} golden 文件缺失: {info['golden']}"
        )
        golden = json.loads(info["golden"].read_text(encoding="utf-8"))
        # 每科 golden 必须有题目，且每题含评估所需字段（结构完整性）
        assert golden.get("questions"), f"{subject} golden questions 为空"
        for q in golden["questions"]:
            assert "answer" in q, f"{subject} Q{q.get('question_number')} 缺 answer"
            assert "answer_line_ids" in q

    # evaluate_golden_for_subject 必须返回完整 8 字段（用真实 run 数据，非 golden 自身）
    for subject in ("math", "english", "physics"):
        run_path = LV / f"{subject}_run1.json"
        if not run_path.exists():
            continue
        run = json.loads(run_path.read_text(encoding="utf-8"))
        acc = rlv.evaluate_golden_for_subject(run, rlv.SUBJECTS[subject]["golden"])
        assert acc is not None, f"{subject} golden 评估返回 None"
        missing = [f for f in GOLDEN_FIELDS if f not in acc]
        assert not missing, f"{subject} golden 评估缺字段: {missing}"
        for field, stats in acc.items():
            assert "correct" in stats and "total" in stats, (
                f"{subject}.{field} 缺 correct/total"
            )
