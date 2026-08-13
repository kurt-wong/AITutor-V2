#!/usr/bin/env python3
"""DEPRECATED: 此脚本使用自证逻辑（golden 复制结果再与 golden 比较）。

请使用 run_phase1_eval.py 作为唯一 eval 入口：
  python run_phase1_eval.py           # mock 模式
  python run_phase1_eval.py --live    # live 模式
"""
import json, re, sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = ROOT / "test" / "annotations" / "golden" / "math_real_golden.json"
FIXTURE_PATH = ROOT / "test" / "fixtures" / "l1_snapshot_math_real_ppsv3.json"
_Q_PREFIX_RE = re.compile(r"^[（(]\s*\d{1,3}\s*[）)]\s*")

def load_golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

def load_fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

def build_mock_questions(golden, fixture):
    line_map = {l["line_id"]: l for l in fixture["lines"]}
    questions = []
    for gq in golden["questions"]:
        q = {
            "question_number": gq["question_number"],
            "question_type": gq["question_type"],
            "section_id": gq.get("section_id"),
            "stem_line_ids": gq["stem_line_ids"],
            "options_line_ids": gq.get("options_line_ids", {}),
            "answer": gq["answer"],
            "answer_line_ids": gq.get("answer_line_ids", []),
            "explanation_line_ids": gq.get("explanation_line_ids", []),
            "difficulty": gq.get("difficulty"),
            "score": gq.get("score"),
            "knowledge_points": gq.get("knowledge_points", []),
        }
        stem_text = ""
        for lid in gq.get("stem_line_ids", []):
            if lid in line_map:
                stem_text += line_map[lid]["text"].strip() + " "
        q["stem"] = stem_text.strip()
        options = []
        for label, lids in gq.get("options_line_ids", {}).items():
            opt_text = ""
            for lid in lids:
                if lid in line_map:
                    opt_text += line_map[lid]["text"].strip() + " "
            options.append({"label": label, "text": opt_text.strip()})
        q["options"] = options
        q["answer_provenance"] = {"source": gq.get("answer_source", "unknown")}
        questions.append(q)
    return questions

def evaluate_accuracy(result_questions, golden):
    gmap = {q["question_number"]: q for q in golden["questions"]}
    fields = {
        "question_number": [0, 0], "question_type": [0, 0],
        "answer": [0, 0], "stem_line_ids": [0, 0],
        "options_line_ids": [0, 0], "answer_line_ids": [0, 0],
        "stem_content": [0, 0], "options_content": [0, 0],
    }
    for rq in result_questions:
        gq = gmap.get(rq.get("question_number", ""))
        if not gq:
            continue
        for f in ["question_number", "question_type", "answer",
                   "stem_line_ids", "options_line_ids", "answer_line_ids"]:
            fields[f][1] += 1
            a, e = rq.get(f), gq.get(f)
            if f == "answer":
                if (e or "").strip() == (a or "").strip():
                    fields[f][0] += 1
            elif f == "options_line_ids":
                if rq.get("question_type") == "fill_blank":
                    fields[f][0] += 1
                elif a and e and sorted(a) == sorted(e):
                    fields[f][0] += 1
            elif f.endswith("_line_ids"):
                if a and e and sorted(a) == sorted(e):
                    fields[f][0] += 1
            else:
                if a == e:
                    fields[f][0] += 1
        ec = gq.get("expected_content", {})
        if ec.get("stem"):
            fields["stem_content"][1] += 1
            rs = _Q_PREFIX_RE.sub("", rq.get("stem") or "").strip()
            gs = _Q_PREFIX_RE.sub("", ec["stem"] or "").strip()
            if gs in rs:
                fields["stem_content"][0] += 1
        if ec.get("options") and rq.get("options"):
            fields["options_content"][1] += 1
            ro = {o["label"]: o["text"] for o in rq["options"]}
            def _norm(s):
                # Normalize: form feed -> backslash, double backslash -> single backslash
                return s.replace(chr(12), chr(92)).replace(chr(92)+chr(92), chr(92)).strip()
            if all(_norm(ec["options"][k]) in _norm(ro.get(k, "")) for k in ec["options"]):
                fields["options_content"][0] += 1
    return fields

def main():
    golden = load_golden()
    fixture = load_fixture()
    valid_ids = {l["line_id"] for l in fixture["lines"]}
    line_errors = 0
    for q in golden["questions"]:
        for lid in q.get("stem_line_ids", []) + q.get("answer_line_ids", []):
            if lid not in valid_ids:
                line_errors += 1
                print("ERROR: Golden line ID %s not in PP fixture" % lid)
    result_questions = build_mock_questions(golden, fixture)
    acc = evaluate_accuracy(result_questions, golden)
    print("Phase 1 Eval (PP-based): %d questions" % len(result_questions))
    print("Line ID errors: %d" % line_errors)
    for f, (c, t) in acc.items():
        a = c / t if t else 0
        print("  %s: %d/%d = %.1f%%" % (f, c, t, a * 100))
    sources = Counter(r.get("answer_provenance", {}).get("source", "none") for r in result_questions)
    print("Sources: %s" % dict(sources))
    thresholds = {
        "question_number": 1.0, "question_type": 1.0, "answer": 0.95,
        "stem_line_ids": 1.0, "options_line_ids": 1.0, "answer_line_ids": 1.0,
        "stem_content": 0.95, "options_content": 1.0,
    }
    failed = []
    for f, th in thresholds.items():
        c, t = acc.get(f, [0, 0])
        a = c / t if t else 0
        if a < th:
            failed.append("%s %.1f%% < %.0f%%" % (f, a * 100, th * 100))
    expl_na = sum(1 for q in golden["questions"] if not q.get("explanation_line_ids"))
    if expl_na:
        print("NOTE: %d golden explanation_line_ids empty" % expl_na)
    ok = not line_errors and not failed
    if ok:
        print("PASS: Phase 1")
    else:
        print("FAIL: Phase 1")
        for f in failed:
            print("  FAIL: %s" % f)
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
