#!/usr/bin/env python3
"""WP4: 生成英语/物理 native L1 fixture + golden 草稿。

注意（TASK_2.5_REPAIR_PLAN WP4）：
  - golden 必须人工核对，禁止直接用 live 结果作为 golden。
  - 本脚本生成的 golden 是 **manual_review_draft**（status 字段标注）：
    * expected_content / expected_anchor / answer / answer_line_ids 从 native-only live 结果提取；
    * answer 为空的题标注 answer_needs_manual=true；
    * 待真实 PP L1 建立后，由人工核对替换（不得把本草稿当验收 golden）。
  - native L1 fixture 由 extract_l1_from_pdf 重新生成，保证 line_id 可校验。

用法:
  python build_golden_draft.py            # 生成英语/物理的 fixture + golden 草稿
  python build_golden_draft.py --english  # 只生成英语
  python build_golden_draft.py --physics  # 只生成物理
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

_backend_env = ROOT / "backend" / ".env"
if _backend_env.exists():
    for line in _backend_env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from app.domains.document.native_markdown import extract_l1_from_pdf  # noqa: E402

PDF_DIR = ROOT / "test" / "pdf"
RESULTS_DIR = ROOT / "test" / "results" / "live_validation"
FIXTURES_DIR = ROOT / "test" / "fixtures"
GOLDEN_DIR = ROOT / "test" / "annotations" / "golden"

SUBJECTS = {
    "english": {
        "pdf": "2026北京朝阳高一（上）期末英语（教师版）.pdf",
        "run": "english_run1.json",
        "golden_out": "english_2026_real_golden.json",
        "fixture_out": "l1_native_english_2026.json",
    },
    "physics": {
        "pdf": "2026北京朝阳高一（上）期末物理（教师版）.pdf",
        "run": "physics_run1.json",
        "golden_out": "physics_2026_real_golden.json",
        "fixture_out": "l1_native_physics_2026.json",
    },
}


def build_native_fixture(pdf_path: Path, out_path: Path, filename: str) -> int:
    doc = extract_l1_from_pdf(pdf_path, filename=filename)
    fixture = {
        "filename": filename,
        "source": "native",
        "total_pages": doc.total_pages,
        "text_coverage": doc.text_coverage,
        "lines": [
            {
                "line_id": l.line_id,
                "page_no": l.page_no,
                "line_no_in_page": l.line_no_in_page,
                "order": l.order,
                "text": l.text,
                "block_type": l.block_type,
                "source": l.source,
            }
            for l in doc.lines
        ],
    }
    out_path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(doc.lines)


def build_golden_draft(run_path: Path, out_path: Path, fixture_name: str, filename: str) -> int:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    questions = []
    for q in run.get("questions", []):
        options_line_ids = q.get("options_line_ids", {}) or {}
        # math golden 的 expected_anchor.options_line_ids 是 list of lists（按 label 排序）
        anchor_options = [
            options_line_ids[label]
            for label in sorted(options_line_ids.keys())
            if options_line_ids.get(label)
        ]
        answer = q.get("answer")
        needs_manual = not (answer or "").strip()
        gq = {
            "question_number": q.get("question_number"),
            "question_type": q.get("question_type"),
            "section_id": q.get("section_id"),
            "stem_line_ids": q.get("stem_line_ids", []),
            "options_line_ids": options_line_ids,
            "answer": answer,
            "answer_line_ids": q.get("answer_line_ids", []),
            "explanation_line_ids": q.get("explanation_line_ids", []),
            "answer_source": (q.get("answer_provenance") or {}).get("source"),
            "explanation_source": (q.get("explanation_provenance") or {}).get("source"),
            "expected_content": {
                "stem": q.get("stem"),
                "options": {
                    o.get("label"): o.get("text") for o in q.get("options", []) if o.get("label")
                } if q.get("options") else {},
                "answer": answer,
            },
            "expected_anchor": {
                "stem_line_ids": q.get("stem_line_ids", []),
                "options_line_ids": anchor_options,
                "answer_line_ids": q.get("answer_line_ids", []),
                "explanation_line_ids": q.get("explanation_line_ids", []),
            },
            "difficulty": q.get("difficulty"),
            "score": q.get("score"),
            "knowledge_points": q.get("knowledge_points", []),
            "confidence": q.get("confidence"),
            "source_page": q.get("source_page"),
            "status": "manual_review_draft_needs_pp",
            "answer_needs_manual": needs_manual,
        }
        questions.append(gq)

    golden = {
        "filename": filename,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "annotator": "dsh_draft_from_native_live",
        "version": "0.1-draft",
        "postprocessed": False,
        "l1_fixture": fixture_name,
        "source_note": (
            "草稿（非验收 golden）：由 native-only live 结果生成，未经人工核对。"
            "answer 为空的题标注 answer_needs_manual=true。"
            "待真实 PP L1 建立后必须由人工核对替换，不得直接用于 Task 2.5 验收。"
        ),
        "questions": questions,
    }
    out_path.write_text(json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(questions)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成英语/物理 golden 草稿 + native L1 fixture")
    parser.add_argument("--english", action="store_true")
    parser.add_argument("--physics", action="store_true")
    args = parser.parse_args()

    targets = []
    if args.english:
        targets = ["english"]
    elif args.physics:
        targets = ["physics"]
    else:
        targets = list(SUBJECTS.keys())

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    for subject in targets:
        info = SUBJECTS[subject]
        pdf_path = PDF_DIR / info["pdf"]
        run_path = RESULTS_DIR / info["run"]
        if not pdf_path.exists():
            print(f"[FAIL] {subject}: PDF 不存在 {pdf_path}")
            return 1
        if not run_path.exists():
            print(f"[WARN] {subject}: live run 不存在 {run_path}，跳过 golden 草稿")
            run_path = None

        fixture_path = FIXTURES_DIR / info["fixture_out"]
        n_lines = build_native_fixture(pdf_path, fixture_path, info["pdf"])
        print(f"[OK] {subject}: native L1 fixture {n_lines} 行 -> {fixture_path.name}")

        if run_path is not None:
            golden_path = GOLDEN_DIR / info["golden_out"]
            n_q = build_golden_draft(
                run_path, golden_path, info["fixture_out"], info["pdf"])
            print(f"[OK] {subject}: golden 草稿 {n_q} 题 -> {golden_path.name} "
                  f"(status=manual_review_draft_needs_pp)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
