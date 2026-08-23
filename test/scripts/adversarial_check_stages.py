#!/usr/bin/env python3
"""对抗性审查辅助：检查 english/physics 的阶段数据。"""
import json
from pathlib import Path

LV = Path(__file__).resolve().parents[2] / "test" / "results" / "live_validation"

for subj in ("english", "physics"):
    d = json.loads((LV / f"{subj}_run1.json").read_text(encoding="utf-8"))
    stages = {s["name"]: s for s in d.get("stages", [])}
    arb = stages.get("l1_arbiter", {})
    merge = stages.get("dual_source_merge", {})
    qg = stages.get("quality_gate", {})
    am = stages.get("answer_matching", {})
    qs = d.get("questions", [])
    with_issues = sum(1 for q in qs if q.get("issues"))
    no_ans = sum(1 for q in qs if not (q.get("answer") or "").strip())
    print(f"{subj}: questions={d.get('question_count')} "
          f"conflicts={arb.get('conflicts')} llm_audited={arb.get('llm_audited')} "
          f"dual_source={merge.get('dual_source_lines')} native_only={merge.get('native_only_lines')} "
          f"answer_matched={am.get('matched')} high_conf={qg.get('high_confidence')} "
          f"issues={with_issues}/{len(qs)} answer_empty={no_ans}/{len(qs)}")
