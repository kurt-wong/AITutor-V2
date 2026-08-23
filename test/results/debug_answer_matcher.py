import json, sys, re, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\Project\AITutors-v2\backend')

# 模拟 answer_matcher 的逻辑
from app.domains.document.answer_matcher import (
    _slice_llm_answer_lines,
    _clean_llm_sliced_answer,
    _is_suspicious_llm_answer_text,
    _filter_answer_section_titles,
    _filter_diagram_labels,
)
from app.domains.document.schemas_l1 import L1Line

# OCR markdown
with open(r'D:\Project\AITutors-v2\test\ocr_markdown\2025北京东城高一（上）期末历史（教师版）_numbered.md', 'r', encoding='utf-8') as f:
    ocr_lines = f.readlines()

# 构建 line_by_id
line_by_id = {}
for line_text in ocr_lines:
    parts = line_text.strip().split(' ', 1)
    if len(parts) == 2:
        lid = parts[0]
        text = parts[1]
        # 提取 page_no 和 line_no
        m = re.match(r'P(\d+)L(\d+)', lid)
        if m:
            page_no = int(m.group(1))
            line_no = int(m.group(2))
            line_by_id[lid] = L1Line(
                line_id=lid, page_no=page_no, line_no_in_page=line_no,
                order=len(line_by_id), text=text, block_type="text"
            )

# LLM 标注
with open(r'D:\Project\AITutors-v2\test\results\9subject_validation\2025北京东城高一（上）期末历史（教师版）_run1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

ann = data.get('llm_annotation', {})
questions = ann.get('questions', [])

# 检查 Q42 的答案切片过程
for q in questions:
    qn = q.get('question_number')
    if qn not in ('42', '43'):
        continue

    print(f'=== Q{qn} ===')
    ans_ids = q.get('answer_line_ids', [])
    print(f'answer_line_ids: {ans_ids}')
    print(f'q.answer: {q.get("answer")}')
    print()

    # 模拟 _apply_llm_annotation_answers 的逻辑
    answer_ids = _filter_answer_section_titles(
        [lid for lid in ans_ids if lid in line_by_id],
        line_by_id,
    )
    answer_ids = _filter_diagram_labels(answer_ids, line_by_id)
    print(f'filtered answer_ids: {answer_ids}')

    if answer_ids:
        answer_text = _clean_llm_sliced_answer(
            qn,
            _slice_llm_answer_lines(answer_ids, qn, line_by_id, skip_wrong_marker_lines=True, is_short_answer=True),
        )
        print(f'sliced answer_text ({len(answer_text)} chars): {answer_text[:200]}...')
        print(f'is_suspicious: {_is_suspicious_llm_answer_text(answer_text, q.get("stem", ""))}')
    print()
