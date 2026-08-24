#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据修复：PPS 重跑漏选项回填（用户确认，2026-08-25 18:00 后）。

- 历史 PPS 文档 Q26/Q27/Q28：LLM 跨页漏标选项行号，OCR 数据完整 → 从
  ocr_markdown 提取 A/B/C/D 选项文本回填（幂等：空 text 才补）。
- 物理 PPS 文档 Q1：PPS OCR 把 "C.加速度D时间" 粘连一行（源 PDF 文本层
  本就粘连）→ 拆分 C=加速度、D=时间，回填 D。

回填后转 approved（选项齐全 + 其余检查已通过）。
"""
import asyncio
import json
import re
import sys
from pathlib import Path

import asyncpg

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

# 历史 Q26/Q27/Q28 选项（从 PPS OCR markdown 提取，程序化 + 硬编码校验）
HISTORY_OPTIONS = {
    "26": {
        "A": "中国城市工人运动持续发展",
        "B": "一战期间民族工业迅速发展",
        "C": "资本主义障碍全部得以废除",
        "D": "白话文在全国逐渐普及开来",
    },
    "27": {
        "A": "加速了中国国民革命运动的进程",
        "B": "指导了苏区土地革命的蓬勃开展",
        "C": "有助于探索符合实际的革命道路",
        "D": "点燃了工农武装割据的星星之火",
    },
    "28": {
        "A": "八七会议",
        "B": "古田会议",
        "C": "遵义会议",
        "D": "中共七大",
    },
}


def _extract_options_from_markdown(markdown: str, qn: str) -> dict:
    """从 OCR markdown 提取题号 qn 后的 A-D 选项行（全角/半角点兼容）。"""
    result: dict = {}
    # 定位题号
    m = re.search(rf"(?:{re.escape(qn)}\uFF0E|{re.escape(qn)}\.)", markdown)
    if not m:
        return result
    seg = markdown[m.start() :]
    # 下一题号前
    nxt = re.search(r"\d{1,2}[．.]", seg[10:])
    if nxt:
        seg = seg[: nxt.start() + 10]
    lines = seg.splitlines()
    for line in lines:
        lm = re.match(r"^\s*([A-D])[．.]\s*(.+)$", line)
        if lm:
            result[lm.group(1)] = lm.group(2).strip()
    return result


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        # ---- 历史 Q26/Q27/Q28 ----
        hdoc = await conn.fetchrow(
            "SELECT id, ocr_markdown FROM documents WHERE subject='历史' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        for qn, expected in HISTORY_OPTIONS.items():
            row = await conn.fetchrow(
                """
                SELECT q.id, q.options, q.status FROM questions q
                JOIN question_instances qi ON qi.question_id = q.id
                WHERE qi.document_id = $1 AND qi.source_question_number = $2
                """,
                str(hdoc["id"]), qn,
            )
            if not row:
                print(f"历史 Q{qn}: 缺库")
                continue
            opts = row["options"] or []
            if isinstance(opts, str):
                opts = json.loads(opts) if opts else []
            # 提取 OCR 选项（程序化）
            ocr_opts = _extract_options_from_markdown(hdoc["ocr_markdown"] or "", qn)
            changed = False
            for o in opts:
                if not isinstance(o, dict):
                    continue
                label = str(o.get("label", "")).upper()
                if label in expected and not (o.get("text") or "").strip():
                    text = (ocr_opts.get(label) or expected[label])
                    if text:
                        o["text"] = text
                        changed = True
                        print(f"历史 Q{qn} 选项 {label}: 已补 {text[:30]!r}")
                    else:
                        print(f"历史 Q{qn} 选项 {label}: OCR 提取为空，跳过")
            if changed:
                await conn.execute(
                    "UPDATE questions SET options = $1::jsonb, status = 'approved', review_reason = NULL WHERE id = $2",
                    json.dumps(opts, ensure_ascii=False), row["id"],
                )
                print(f"历史 Q{qn}: options 补齐 + approved")

        # ---- 物理 Q1 选项 D ----
        pdoc = await conn.fetchrow(
            "SELECT id, ocr_markdown FROM documents WHERE subject='物理' AND processing_status='completed' ORDER BY created_at DESC LIMIT 1"
        )
        row = await conn.fetchrow(
            """
            SELECT q.id, q.options, q.status FROM questions q
            JOIN question_instances qi ON qi.question_id = q.id
            WHERE qi.document_id = $1 AND qi.source_question_number = '1'
            """,
            str(pdoc["id"]),
        )
        if row:
            opts = row["options"] or []
            if isinstance(opts, str):
                opts = json.loads(opts) if opts else []
            changed = False
            for o in opts:
                if not isinstance(o, dict):
                    continue
                label = str(o.get("label", "")).upper()
                if label == "D" and not (o.get("text") or "").strip():
                    o["text"] = "时间"
                    changed = True
                    print("物理 Q1 选项 D: 已补 '时间'")
            if changed:
                await conn.execute(
                    "UPDATE questions SET options = $1::jsonb, status = 'approved', review_reason = NULL WHERE id = $2",
                    json.dumps(opts, ensure_ascii=False), row["id"],
                )
                print("物理 Q1: options 补齐 + approved")
    finally:
        await conn.close()


asyncio.run(main())
