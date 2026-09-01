"""批量更新 Golden 文件：清空综合题容器的答案类字段。

按 DISPLAY_CONTRACT.md v0.5 标准：
- 容器应该保存：question_number, question_type, is_composite, stem, stem_line_ids,
  shared_material, shared_material_line_ids, shared_material_notes, scoring_standard, images, sub_questions
- 容器不应该保存：answer, answer_line_ids, answer_region, answer_images,
  explanation, explanation_line_ids, explanation_region, options, options_line_ids
"""

import json
from pathlib import Path

# 需要清空的容器字段
CONTAINER_FIELDS_TO_CLEAR = [
    "answer",
    "answer_line_ids",
    "answer_region",
    "answer_images",
    "explanation",
    "explanation_line_ids",
    "explanation_region",
    "options",
    "options_line_ids",
]


def clear_container_fields(question: dict) -> dict:
    """清空综合题容器的答案类字段。"""
    if not question.get("is_composite"):
        return question

    for field in CONTAINER_FIELDS_TO_CLEAR:
        if field in question:
            # 设为 null 或 []，取决于字段类型
            if field.endswith("_ids") or field.endswith("_images"):
                question[field] = []
            else:
                question[field] = None

    return question


def update_golden_file(filepath: Path) -> bool:
    """更新单个 golden 文件。"""
    data = json.loads(filepath.read_text(encoding="utf-8"))
    questions = data.get("questions", [])

    changed = False
    for q in questions:
        if q.get("is_composite"):
            old_answer = q.get("answer")
            if old_answer is not None and old_answer != "":
                print(f"  {filepath.name} Q{q.get('question_number')}: answer {old_answer!r} -> null")
                changed = True
            q = clear_container_fields(q)

    if changed:
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return changed


def main():
    """主函数。"""
    golden_dir = Path(__file__).parent.parent.parent / "test" / "annotations" / "golden"

    print("Updating Golden files: clear composite container answer fields")
    print("=" * 70)
    print(f"Golden dir: {golden_dir}")
    print()

    updated_count = 0
    for filepath in sorted(golden_dir.glob("*.json")):
        if "exercise" in filepath.name:
            continue  # 跳过 exercise 文件

        data = json.loads(filepath.read_text(encoding="utf-8"))
        has_composites = any(q.get("is_composite") for q in data.get("questions", []))

        if has_composites:
            print(f"Checking {filepath.name}...")
            if update_golden_file(filepath):
                updated_count += 1
                print(f"  UPDATED")
            else:
                print(f"  No changes needed")
            print()

    print("=" * 70)
    print(f"Updated {updated_count} golden files")


if __name__ == "__main__":
    main()
