"""Convert PP-StructureV3 markdown output to L1 snapshot format."""
import json
import os
import re
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "ppsv3_output")
L1_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "fixtures", "l1_snapshot_math_real_ppsv3.json")


def parse_markdown_to_lines(md_text, page_no):
    """Parse markdown text into L1Line-like structures."""
    lines = []
    line_no = 0
    order = 0

    for raw_line in md_text.split("\n"):
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        line_no += 1
        order += 1

        block_type = "text"
        if raw_line.startswith("#"):
            block_type = "title"
        elif "$" in raw_line and re.search(r'[\^_{}]|frac|sin|cos|log|alpha|beta|pi|theta', raw_line):
            block_type = "formula"
        elif raw_line.startswith("(A)") or raw_line.startswith("(B)") or raw_line.startswith("(C)") or raw_line.startswith("(D)"):
            block_type = "option"
        elif raw_line.startswith("##"):
            block_type = "section"

        line_id = "P%dL%03d" % (page_no, line_no)

        lines.append({
            "line_id": line_id,
            "page_no": page_no,
            "line_no_in_page": line_no,
            "order": order,
            "text": raw_line,
            "block_type": block_type,
            "source": "ppsv3",
            "continuation": False,
        })

    return lines


def main():
    all_lines = []
    page_no = 0

    for i in range(1, 10):
        md_file = os.path.join(OUTPUT_DIR, "page_%d.md" % i)
        if not os.path.exists(md_file):
            print("Missing:", md_file)
            continue

        with open(md_file, "r", encoding="utf-8") as f:
            md_text = f.read()

        page_no += 1
        page_lines = parse_markdown_to_lines(md_text, page_no)
        all_lines.extend(page_lines)
        print("Page %d: %d lines" % (page_no, len(page_lines)))

    snapshot = {
        "filename": "2026北京朝阳高一（上）期末数学（教师版）.pdf",
        "source": "ppsv3",
        "postprocessed": False,
        "pages": [{"page_no": i, "width": 595, "height": 842} for i in range(1, page_no + 1)],
        "lines": all_lines,
    }

    with open(L1_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    print("\nSaved %d lines to %s" % (len(all_lines), L1_OUTPUT))


if __name__ == "__main__":
    main()
