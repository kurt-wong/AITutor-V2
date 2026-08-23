#!/usr/bin/env python3
"""本地复现 question_number 子题规范化。

用真实 physics PP fixture + 当前 golden 结构生成两种 mock 标注：
- run1：LLM 把 15-20 号多小问拆成 15(1)/15(2)/...（33 题结构）
- run2：LLM 输出母题（20 题结构）

规范化后两者都应收敛为 20 题，且复现性差异为 0。该脚本仅做本地 mock
全链路验证，不替代真实 live_pp；Task 2.5 仍需真实 OCR/LLM 重跑验收。
"""

import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.gateway import LLMGateway
from app.ai.providers import MockLLMProvider
from app.domains.document.pipeline import run_pipeline
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page

FIXTURE_PATH = ROOT / "test" / "fixtures" / "l1_ppsv3_physics_2026.json"
GOLDEN_PATH = ROOT / "test" / "annotations" / "golden" / "physics_2026_real_golden.json"
OUTPUT_DIR = ROOT / "test" / "results" / "live_validation"

_SUB_START_RE = re.compile(r"^\s*[（(]\s*(\d{1,3})\s*[）)]")


def _build_doc() -> L1Document:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    lines = [
        L1Line(
            line_id=l["line_id"],
            page_no=l["page_no"],
            line_no_in_page=l["line_no_in_page"],
            order=l["order"],
            text=l["text"],
            block_type=l.get("block_type", "text"),
            source="ppsv3",
            continuation=l.get("continuation", False),
            bbox=l.get("bbox"),
        )
        for l in fixture["lines"]
    ]
    pages = [
        L1Page(page_no=p, lines=[])
        for p in range(1, fixture.get("total_pages", max(l.page_no for l in lines)) + 1)
    ]
    return L1Document(
        filename=fixture["filename"],
        pages=pages,
        lines=lines,
        source="ppsv3",
        total_pages=fixture.get("total_pages", len(pages)),
        text_coverage=fixture.get("text_coverage", 1.0),
    )


def _question_payload(q: dict) -> dict:
    return {
        "question_number": q["question_number"],
        "question_type": q["question_type"],
        "section_id": q.get("section_id"),
        "stem_line_ids": q.get("stem_line_ids", []),
        "options_line_ids": q.get("options_line_ids", {}),
        "difficulty": q.get("difficulty"),
        "score": q.get("score"),
        "knowledge_points": q.get("knowledge_points", []),
    }


def _split_subquestions(q: dict, line_by_id: dict[str, str]) -> list[dict] | None:
    """把 15-20 号的母题 stem 按（1）（2）... 拆成 mock 子题标注。"""
    stem_ids = q.get("stem_line_ids", [])
    starts = [
        i for i, lid in enumerate(stem_ids)
        if _SUB_START_RE.match(line_by_id.get(lid, ""))
    ]
    if len(starts) < 2:
        return None

    result = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(stem_ids)
        sub_q = dict(_question_payload(q))
        sub_q["question_number"] = f"{q['question_number']}({idx + 1})"
        sub_q["stem_line_ids"] = stem_ids[start:end]
        sub_q["options_line_ids"] = {}
        if q.get("section_id"):
            sub_q["section_id"] = f"{q['section_id']}_{q['question_number']}"
        result.append(sub_q)
    return result


def _mock_response(split_subquestions: bool) -> str:
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    line_by_id = {l["line_id"]: l["text"] for l in fixture["lines"]}

    questions: list[dict] = []
    for q in golden["questions"]:
        if split_subquestions:
            subs = _split_subquestions(q, line_by_id)
            if subs is not None:
                questions.extend(subs)
                continue
        questions.append(_question_payload(q))

    return json.dumps({
        "filename": fixture["filename"],
        "subject": "physics",
        "questions": questions,
        "metadata_confidence": 0.9,
        "warnings": [],
    }, ensure_ascii=False)


async def _run_one(response: str) -> dict:
    gateway = LLMGateway(
        mode="live",
        providers=[MockLLMProvider(response=response)],
    )
    result = await run_pipeline(ppsv3_doc=_build_doc(), gateway=gateway)
    return result.to_dict()


async def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run1 = await _run_one(_mock_response(split_subquestions=True))
    run2 = await _run_one(_mock_response(split_subquestions=False))

    for name, data in [("physics_local_sim_run1.json", run1),
                       ("physics_local_sim_run2.json", run2)]:
        (OUTPUT_DIR / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    sys.path.insert(0, str(ROOT / "test" / "scripts"))
    import run_live_validation as rlv

    diffs = rlv.check_reproducibility(run1, run2)
    quality = rlv.compute_quality_stats(run1)
    print(f"run1 question_count={run1['question_count']} "
          f"run2 question_count={run2['question_count']}")
    print(f"reproducibility_differences={len(diffs)}")
    for diff in diffs:
        print(f"  - {diff}")
    print(f"answer_matched={quality['answer_matched']} "
          f"answer_empty={quality['answer_empty']} "
          f"answer_empty_ratio={quality['answer_empty_ratio']}")
    q15 = next(q for q in run1["questions"] if q["question_number"] == "15")
    print(f"Q15_stem_last={q15['stem_line_ids'][-1]} "
          f"Q15_has_P6L010={'P6L010' in q15['stem_line_ids']}")

    return 0 if run1["question_count"] == 20 and run2["question_count"] == 20 and not diffs else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
