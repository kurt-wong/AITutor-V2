#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：化学 Q11 选项 B/C/D 缺失回填（发现于膨胀边界审核，任务⑤顺带）。

根因：LLM 标注/切片只提取了选项 A（其余 B/C/D text 为空）。
源中选项真实存在（pdf_raw 竖排 + OCR LaTeX 交叉重建）：
- B. 硫酸与氢氧化钡的反应：2H⁺+SO₄²⁻+Ba²⁺+2OH⁻=BaSO₄↓+2H₂O（pdf_raw 系数 + OCR 结构）
- C. 澄清石灰水与足量碳酸氢钠的反应：Ca²⁺+2OH⁻+2HCO₃⁻=CaCO₃↓+2H₂O+CO₃²⁻（OCR）
- D. 钠放置在空气中表面会变暗：2Na+O₂=Na₂O₂（OCR；表面变暗正确式为
  4Na+O₂=2Na₂O，故 D 为错误干扰项，与答案 C 单选一致）
幂等：仅当 B/C/D 有空 text 时补。
"""
import asyncio
import json
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

NEW_OPTIONS = {
    "B": r"硫酸与氢氧化钡的反应：$2H^{+}+SO_{4}^{2-}+Ba^{2+}+2OH^{-}=BaSO_{4}\downarrow+2H_{2}O$",
    "C": r"澄清石灰水与足量碳酸氢钠的反应：$Ca^{2+}+2OH^{-}+2HCO_{3}^{-}=CaCO_{3}\downarrow+2H_{2}O+CO_{3}^{2-}$",
    "D": r"钠放置在空气中表面会变暗：$2Na+O_{2}=Na_{2}O_{2}$",
}


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        doc = await conn.fetchrow(
            "SELECT id FROM documents WHERE subject='化学' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        row = await conn.fetchrow(
            """
            SELECT q.id, q.options FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '11'
            """,
            str(doc["id"]),
        )
        if not row:
            print("DB 无化学 Q11")
            return
        opts = row["options"] or []
        if isinstance(opts, str):
            opts = json.loads(opts) if opts else []
        changed = False
        for o in opts:
            label = str(o.get("label", "")).upper()
            if label in NEW_OPTIONS and not (o.get("text") or "").strip():
                o["text"] = NEW_OPTIONS[label]
                changed = True
                print(f"Q11 选项 {label} 已补")
        if not changed:
            print("Q11 选项无需补充（均已存在）")
            return
        await conn.execute(
            "UPDATE questions SET options = $1::jsonb, status = 'approved', review_reason = NULL WHERE id = $2",
            json.dumps(opts, ensure_ascii=False),
            row["id"],
        )
        print("Q11 options 已更新 + approved")
    finally:
        await conn.close()


asyncio.run(main())
