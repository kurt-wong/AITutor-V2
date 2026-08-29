"""Golden 展示契约字段校验。

校验 test/annotations/golden/ 下当前验收 golden 是否已按
Docs/00_Requirements/DISPLAY_CONTRACT.md v0.4 补齐展示结构字段。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "test" / "annotations" / "golden"

CONTRACT_VERSION = "0.4"
REQUIRED_QUESTION_FIELDS = {
    "stem_region",
    "answer_region",
    "explanation_region",
    "shared_material_line_ids",
    "shared_material_notes",
    "shared_material_notes_line_ids",
    "scoring_standard",
    "is_composite",
    "sub_questions",
    "word_bank",
    "answer_structure",
    "images",
    "answer_images",
}


def _real_golden_paths():
    paths = [
        GOLDEN_DIR / "english_2026_real_golden.json",
        GOLDEN_DIR / "english_2026_dongcheng_real_golden.json",
        GOLDEN_DIR / "math_real_golden.json",
        GOLDEN_DIR / "physics_2026_real_golden.json",
    ]
    return [p for p in paths if p.exists()]


def test_golden_contract_version():
    """当前验收 golden 必须标记展示契约版本。"""
    for path in _real_golden_paths():
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("display_contract_version") == CONTRACT_VERSION, (
            f"{path.name} display_contract_version != {CONTRACT_VERSION}"
        )


def test_golden_questions_have_contract_fields():
    """每道题必须包含 DISPLAY_CONTRACT v0.4 要求的展示结构字段。"""
    for path in _real_golden_paths():
        data = json.loads(path.read_text(encoding="utf-8"))
        for q in data.get("questions", []):
            missing = REQUIRED_QUESTION_FIELDS - set(q)
            assert not missing, f"{path.name} Q{q.get('question_number')} missing: {sorted(missing)}"
            if q.get("is_composite"):
                assert q.get("sub_questions"), (
                    f"{path.name} Q{q.get('question_number')} is_composite but sub_questions empty"
                )
            for sub in q.get("sub_questions", []):
                sub_missing = REQUIRED_QUESTION_FIELDS - set(sub)
                assert not sub_missing, (
                    f"{path.name} Q{sub.get('question_number')} missing: {sorted(sub_missing)}"
                )
