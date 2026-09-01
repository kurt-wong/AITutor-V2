"""逐字段诊断 number_diff 和 mismatch 的详细分类。"""

import asyncio
import json
import re
import unicodedata
from pathlib import Path
from sqlalchemy import text as sql_text

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.core.database import engine


def normalize_format_only(text):
    if not text:
        return ''
    text = unicodedata.normalize('NFKC', str(text))
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('—', '-').replace('–', '-')
    text = re.sub(r'[\s　]+', ' ', text)
    text = re.sub(r'(\d)\s+([一-鿿])', r'\1\2', text)
    text = re.sub(r'([一-鿿])\s+(\d)', r'\1\2', text)
    text = re.sub(r'([A-Za-z])\s+([一-鿿])', r'\1\2', text)
    text = re.sub(r'([一-鿿])\s+([A-Za-z])', r'\1\2', text)
    text = re.sub(r'([。，；：）」】．])\s+', r'\1', text)
    text = re.sub(r'\s+([。，；：（「【．])', r'\1', text)
    text = text.replace('（', '(').replace('）', ')')
    text = text.replace('〔', '[').replace('〕', ']')
    text = text.strip()
    return text


def normalize_blank_markers(text):
    if not text:
        return ''
    text = normalize_format_only(text)
    # ____N____ → [N]
    text = re.sub(r'_+(\d+)_+', r'[\1]', text)
    # 〔N〕/ 【N】 → [N]
    text = re.sub(r'[〔【［](\d+)[〕】］]', r'[\1]', text)
    # CJK + [N] + CJK → CJK + N + CJK（OCR 方括号噪音）
    text = re.sub(r'([一-鿿])\[(\d+)\]([一-鿿])', r'\1\2\3', text)
    # 裸数字填空位：空格+数字+标点/空格 → [N]
    # 排除已在 [N] 中的数字
    def _replace_bare(m):
        num = m.group(1)
        # 检查前面是否有 [
        start = m.start()
        if start > 0 and text[start - 1] == '[':
            return m.group(0)  # 已在括号中，不替换
        return f'[{num}]'
    text = re.sub(r'(?<=\s)(\d{1,2})(?=[,.;:\]－）\s])', _replace_bare, text)
    return text


def normalize_shared(text_str):
    if not text_str:
        return ''
    text_str = unicodedata.normalize('NFKC', str(text_str))
    text_str = text_str.replace('“', '"').replace('”', '"')
    text_str = text_str.replace('‘', "'").replace('’', "'")
    text_str = text_str.replace('—', ' ').replace('–', ' ')
    text_str = re.sub(r'_+(\d+)_+', ' ', text_str)
    text_str = re.sub(r'_+', ' ', text_str)
    text_str = re.sub(r'[〔\[]\d+[〕\]]', ' ', text_str)
    text_str = re.sub(r'\d+(?=[A-Za-z])', ' ', text_str)
    text_str = re.sub(r'(?<=[A-Za-z])\d+', ' ', text_str)
    text_str = re.sub(r'\d+', ' ', text_str)
    text_str = re.sub(r'[^一-鿿A-Za-z]+', '', text_str)
    return text_str.lower()


def extract_numbers(text):
    return re.findall(r'\d+\.?\d*', str(text))


def classify_number_diff(golden_val, db_val):
    g_fmt = normalize_format_only(str(golden_val or ''))
    d_fmt = normalize_format_only(str(db_val or ''))
    g_blank = normalize_blank_markers(str(golden_val or ''))
    d_blank = normalize_blank_markers(str(db_val or ''))

    g_nums = extract_numbers(g_fmt)
    d_nums = extract_numbers(d_fmt)
    nums_match = (g_nums == d_nums)

    def strip_punct(t):
        return re.sub(r'[,.;:!?。，；：！？.\-]+', '', t)

    blank_no_punct = (strip_punct(g_blank) == strip_punct(d_blank))

    if nums_match and blank_no_punct:
        return 'format'
    elif nums_match:
        return 'blank_marker'
    elif not nums_match and blank_no_punct:
        return 'true_number_diff'
    else:
        return 'mixed'


async def diagnose():
    golden_path = Path(__file__).resolve().parents[2] / 'test' / 'annotations' / 'golden' / 'english_2026_dongcheng_real_golden.json'
    golden = json.loads(golden_path.read_text(encoding='utf-8'))
    golden_questions = golden['questions']

    async with engine.connect() as conn:
        result = await conn.execute(sql_text('''
            SELECT id, stem, options, answer, explanation, scoring_standard,
                   shared_material, stem_line_ids, answer_line_ids,
                   explanation_line_ids, shared_material_line_ids,
                   sub_questions, is_composite, section_id
            FROM questions
            WHERE source_document_name LIKE '%东城%英语%'
            ORDER BY created_at DESC
        '''))
        db_rows = result.fetchall()

    db_questions = []
    for row in db_rows:
        db_questions.append({
            'id': row[0], 'stem': row[1], 'options': row[2],
            'answer': row[3], 'explanation': row[4], 'scoring_standard': row[5],
            'shared_material': row[6], 'stem_line_ids': row[7],
            'answer_line_ids': row[8], 'explanation_line_ids': row[9],
            'shared_material_line_ids': row[10], 'sub_questions': row[11],
            'is_composite': row[12], 'section_id': row[13],
        })

    def build_key(q):
        sm = q.get('shared_material', '') or ''
        if not sm:
            sm = q.get('stem', '') or ''
        if not sm:
            return ''
        return normalize_shared(sm)[:80]

    db_by_key = {}
    for q in db_questions:
        k = build_key(q)
        if k:
            db_by_key[k] = q

    # ── 诊断输出 ──
    print('=' * 80)
    print('DETAILED DIAGNOSTIC')
    print('=' * 80)

    number_diff_count = 0
    mismatch_count = 0
    classifications = {'format': 0, 'blank_marker': 0, 'true_number_diff': 0, 'mixed': 0}
    mismatch_text_levels = {}

    for g_idx, g_q in enumerate(golden_questions):
        g_key = build_key(g_q)
        db_q = db_by_key.get(g_key)
        if not db_q:
            continue

        qnum = g_q.get('question_number', f'Q{g_idx+1}')

        # ── 文本字段诊断 ──
        for field in ['stem', 'shared_material', 'scoring_standard']:
            g_val = g_q.get(field)
            d_val = db_q.get(field)
            if g_val is None and d_val is None:
                continue

            g_raw = str(g_val or '')
            d_raw = str(d_val or '')

            if g_raw == d_raw:
                continue
            if normalize_format_only(g_raw) == normalize_format_only(d_raw):
                continue
            if normalize_blank_markers(g_raw) == normalize_blank_markers(d_raw):
                continue

            g_sem = normalize_shared(g_raw)
            d_sem = normalize_shared(d_raw)
            if g_sem != d_sem:
                continue

            # 这是 number_diff
            number_diff_count += 1
            sub = classify_number_diff(g_val, d_val)
            classifications[sub] += 1
            g_nums = extract_numbers(normalize_format_only(g_raw))
            d_nums = extract_numbers(normalize_format_only(d_raw))

            print(f'\n--- {qnum}.{field}: {sub} ---')
            print(f'  Golden nums: {g_nums}')
            print(f'  DB nums:     {d_nums}')
            print(f'  Golden fmt:  {repr(normalize_format_only(g_raw)[:120])}')
            print(f'  DB fmt:      {repr(normalize_format_only(d_raw)[:120])}')
            print(f'  Golden blank:{repr(normalize_blank_markers(g_raw)[:120])}')
            print(f'  DB blank:    {repr(normalize_blank_markers(d_raw)[:120])}')

        # ── 行号字段诊断 ──
        for line_field in ['stem_line_ids', 'shared_material_line_ids', 'answer_line_ids']:
            g_ids = g_q.get(line_field) or []
            d_ids = db_q.get(line_field) or []
            if len(g_ids) == len(d_ids):
                continue

            text_field = line_field.replace('_line_ids', '')
            g_text = g_q.get(text_field)
            d_text = db_q.get(text_field)

            g_tr = str(g_text or '')
            d_tr = str(d_text or '')

            if g_tr == d_tr:
                text_level = 'exact'
            elif normalize_format_only(g_tr) == normalize_format_only(d_tr):
                text_level = 'format'
            elif normalize_blank_markers(g_tr) == normalize_blank_markers(d_tr):
                text_level = 'blank_marker'
            elif normalize_shared(g_tr) == normalize_shared(d_tr):
                text_level = 'number_diff'
            else:
                text_level = 'text_mismatch'

            mismatch_count += 1
            mismatch_text_levels[text_level] = mismatch_text_levels.get(text_level, 0) + 1
            print(f'\n  {line_field}: {len(g_ids)} vs {len(d_ids)} lines')
            print(f'    text_level: {text_level}')

    print('\n' + '=' * 80)
    print('CLASSIFICATION SUMMARY')
    print('=' * 80)
    print(f'number_diff fields: {number_diff_count}')
    for k, v in classifications.items():
        print(f'  {k}: {v}')
    print(f'mismatch (line fields): {mismatch_count}')
    print(f'mismatch text_levels: {mismatch_text_levels}')
    print()
    print('true_number_diff: ' + str(classifications['true_number_diff']))
    print('If all number_diff are format/blank_marker, mismatch should be granularity.')

asyncio.run(diagnose())
