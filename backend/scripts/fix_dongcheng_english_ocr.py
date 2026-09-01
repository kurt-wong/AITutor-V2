"""受控回填：修复东城英语3个 OCR 拼写错误。

错误来源：PP-StructureV3 OCR 识别错误，内容切片时原样保留。
正确来源：l1_native_english_dongcheng_2026.json 中的正确文本。

修复项：
1. Q5: athlte → athlete (c157fd6c-ef28-465d-a202-3cf7ed3fd220)
2. Q7: wil → will (4a830e87-0609-4f55-8cb1-2dcc61f57c2f)
3. Q8: eforts → efforts (965ed614-4dc6-4f47-8eb8-459a76c06645)
"""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine


# Fixes: (question_id, field, old_value, new_value)
FIXES = [
    (
        "c157fd6c-ef28-465d-a202-3cf7ed3fd220",
        "shared_material",
        "athlte",
        "athlete",
    ),
    (
        "c157fd6c-ef28-465d-a202-3cf7ed3fd220",
        "stem",
        "athlte",
        "athlete",
    ),
    (
        "4a830e87-0609-4f55-8cb1-2dcc61f57c2f",
        "shared_material",
        "wil ",
        "will ",
    ),
    (
        "4a830e87-0609-4f55-8cb1-2dcc61f57c2f",
        "stem",
        "wil ",
        "will ",
    ),
    (
        "965ed614-4dc6-4f47-8eb8-459a76c06645",
        "shared_material",
        "eforts",
        "efforts",
    ),
    (
        "965ed614-4dc6-4f47-8eb8-459a76c06645",
        "stem",
        "eforts",
        "efforts",
    ),
]


async def verify_fixes(dry_run: bool = True) -> None:
    """验证修复前后的状态。"""
    async with engine.connect() as conn:
        for qid, field, old_val, new_val in FIXES:
            result = await conn.execute(
                text(f"SELECT {field} FROM questions WHERE id = :qid"),
                {"qid": qid},
            )
            row = result.fetchone()
            if not row:
                print(f"ERROR: Question {qid} not found")
                continue

            current_val = row[0] or ""
            if old_val not in current_val:
                print(f"SKIP: '{old_val}' not found in {field} of {qid}")
                continue

            if dry_run:
                # Show context around the error
                idx = current_val.find(old_val)
                context_before = current_val[max(0, idx - 30) : idx]
                context_after = current_val[idx + len(old_val) : idx + len(old_val) + 30]
                print(f"WOULD FIX {qid}.{field}:")
                print(f"  ...{context_before}[{old_val}→{new_val}]{context_after}...")
            else:
                new_material = current_val.replace(old_val, new_val)
                await conn.execute(
                    text(f"UPDATE questions SET {field} = :val WHERE id = :qid"),
                    {"val": new_material, "qid": qid},
                )
                print(f"FIXED {qid}.{field}: '{old_val}' → '{new_val}'")

        if not dry_run:
            await conn.commit()
            print("\nAll fixes committed.")


async def main() -> None:
    dry_run = "--apply" not in sys.argv

    if dry_run:
        print("=== DRY RUN (add --apply to execute) ===\n")
    else:
        print("=== APPLYING FIXES ===\n")

    await verify_fixes(dry_run=dry_run)

    if dry_run:
        print("\nRun with --apply to execute the fixes.")


if __name__ == "__main__":
    asyncio.run(main())
