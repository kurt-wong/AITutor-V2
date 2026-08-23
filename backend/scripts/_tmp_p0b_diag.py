"""P0-B 对抗性验证：当 stem 全部在下一题之后时，截断是否生效。"""
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.domains.document.anchor_corrector import _truncate_stem_at_next_question
from app.domains.document.schemas_l1 import L1Line

def line(lid, text, order):
    return L1Line(line_id=lid, page_no=1, line_no_in_page=order, order=order,
                  text=text, block_type="text", bbox={"x1":0,"y1":0,"x2":100,"y2":20}, source="ppsv3")

async def main():
    # 场景：Q1 stem 只包含 Q2 的起始行（LLM 完全标错）
    lines = [
        line("P1L001", "1. Q1 stem", 1),
        line("P1L002", "2. Q2 stem", 2),
    ]
    line_by_id = {l.line_id: l for l in lines}
    qmap = {1: "P1L001", 2: "P1L002"}

    # Q1 的 stem 被标为只有 P1L002（Q2 的行）
    stem_ids = ["P1L002"]

    result = _truncate_stem_at_next_question(stem_ids, line_by_id, qmap, "1", float("inf"))

    print(f"输入: stem_ids={stem_ids}")
    print(f"输出: {result}")
    print(f"边界: Q2 起始于 order=2")
    print()

    if result == ["P1L002"]:
        print("[BUG] 截断未生效！P1L002 (Q2 start) 仍在 stem 中")
        print("根因: L304 `return truncated if truncated else stem_line_ids`")
        print("      当 truncated 为空时，返回原始列表——修复被静默撤销")
    elif result == []:
        print("[OK] 截断生效：stem 被清空（LLM 完全标错时应清空）")
    else:
        print(f"[?] 未预期结果: {result}")

    # 场景 2：stem 部分在边界之后（正常截断）
    print()
    stem_ids2 = ["P1L001", "P1L002"]
    result2 = _truncate_stem_at_next_question(stem_ids2, line_by_id, qmap, "1", float("inf"))
    print(f"输入: stem_ids={stem_ids2}")
    print(f"输出: {result2}")
    if result2 == ["P1L001"]:
        print("[OK] 部分截断生效")
    else:
        print(f"[?] 未预期: {result2}")

asyncio.run(main())
