import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\Project\AITutors-v2\backend')

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

# 检查所有主观题的答案切片
print('=== 主观题答案提取验证 ===')
print()
for q in questions:
    qn = q.get('question_number')
    qtype = q.get('question_type')
    if qtype != 'short_answer':
        continue

    ans_ids = q.get('answer_line_ids', [])
    if not ans_ids:
        print(f'Q{qn}: 无 answer_line_ids')
        continue

    answer_ids = _filter_answer_section_titles(
        [lid for lid in ans_ids if lid in line_by_id], line_by_id
    )
    answer_ids = _filter_diagram_labels(answer_ids, line_by_id)

    if answer_ids:
        answer_text = _clean_llm_sliced_answer(
            qn,
            _slice_llm_answer_lines(answer_ids, qn, line_by_id, skip_wrong_marker_lines=True, is_short_answer=True),
        )
        is_suspicious = _is_suspicious_llm_answer_text(answer_text, q.get('stem', ''))
        # 修复后：short_answer 不做可疑检查
        would_be_cleared = is_suspicious and qtype != 'short_answer'
        print(f'Q{qn} ({qtype}): len={len(answer_text)} is_suspicious={is_suspicious} would_cleared={would_be_cleared}')
        print(f'  answer: {answer_text[:80]}...')
    print()
