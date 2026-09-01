"""英语模块化 Prompt vs 旧 Prompt A/B 对比脚本。

对同一份 L1 输入，分别用模块化和旧 Prompt 的 L2 输出，
经 content_slicer 切片后与 golden 做内容级对比。

用法：
    python -X utf8 scripts/prompt_ab_golden_compare.py
"""

import asyncio
import json
import re
import unicodedata
from pathlib import Path
from sqlalchemy import text as sql_text

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import engine
from app.domains.document.content_slicer import slice_questions
from app.domains.document.schemas_l1 import L1Document, L1Line
from app.domains.document.schemas_l2 import L2DocumentAnnotation, L2QuestionAnnotation, L2SubQuestion


# ── 归一化函数（与 golden_field_comparison.py 保持一致）──

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
    text = re.sub(r'([。，；：）」］．])\s+', r'\1', text)
    text = re.sub(r'\s+([。，；：（「［．])', r'\1', text)
    text = text.replace('（', '(').replace('）', ')')
    text = text.replace('〔', '[').replace('〕', ']')
    text = text.strip()
    return text


def normalize_blank_markers(text):
    if not text:
        return ''
    text = normalize_format_only(text)
    text = re.sub(r'_+(\d+)_+', r'[\1]', text)
    text = re.sub(r'(\d+)_+(?=[,.;:)\]\s])', r'[\1]', text)
    text = re.sub(r'[〔【［](\d+)[〕】］]', r'[\1]', text)
    text = re.sub(r'([一-鿿])\[(\d+)\]([一-鿿])', r'\1\2\3', text)
    def _replace_bare(m):
        num = m.group(1)
        start = m.start()
        if start > 0 and text[start - 1] == '[':
            return m.group(0)
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


def classify_field(golden_val, db_val):
    """分类单个字段的匹配级别。"""
    g_raw = str(golden_val or '')
    d_raw = str(db_val or '')

    if g_raw == d_raw:
        return 'raw_exact'

    g_fmt = normalize_format_only(g_raw)
    d_fmt = normalize_format_only(d_raw)
    if g_fmt == d_fmt:
        return 'format'

    g_blank = normalize_blank_markers(g_raw)
    d_blank = normalize_blank_markers(d_raw)
    if g_blank == d_blank:
        return 'blank_marker'

    def _strip_punct(t):
        return re.sub(r'[,.;:!?。，；：！？.\-\s]+', '', t)
    if _strip_punct(g_blank) == _strip_punct(d_blank):
        return 'punct_diff'

    g_sem = normalize_shared(g_raw)
    d_sem = normalize_shared(d_raw)
    if g_sem == d_sem:
        g_nums = re.findall(r'\d+\.?\d*', g_fmt)
        d_nums = re.findall(r'\d+\.?\d*', d_fmt)
        if g_nums == d_nums:
            return 'format_diff'
        return 'number_diff'

    return 'mismatch'


def build_l2_from_json(data: dict) -> L2DocumentAnnotation:
    """从 JSON 构建 L2DocumentAnnotation 对象。"""
    questions = []
    for qd in data.get('questions', []):
        subs = []
        for sd in qd.get('sub_questions', []):
            subs.append(L2SubQuestion(
                qno=sd.get('qno', ''),
                question_type=sd.get('question_type', ''),
                answer=sd.get('answer'),
                stem_line_ids=sd.get('stem_line_ids', []),
                options_line_ids=sd.get('options_line_ids', {}),
                scoring_standard=sd.get('scoring_standard'),
                answer_images=sd.get('answer_images', []),
            ))
        questions.append(L2QuestionAnnotation(
            question_number=qd.get('question_number', ''),
            question_type=qd.get('question_type', ''),
            section_id=qd.get('section_id'),
            stem_line_ids=qd.get('stem_line_ids', []),
            shared_material_line_ids=qd.get('shared_material_line_ids', []),
            options_line_ids=qd.get('options_line_ids', {}),
            answer=qd.get('answer'),
            answer_line_ids=qd.get('answer_line_ids', []),
            explanation_line_ids=qd.get('explanation_line_ids', []),
            is_composite=qd.get('is_composite', False),
            sub_questions=subs if subs else None,
            stem_start_marker=qd.get('stem_start_marker'),
            stem_end_marker=qd.get('stem_end_marker'),
            confidence=qd.get('confidence', 0.5),
            word_bank=qd.get('word_bank'),
            scoring_standard=qd.get('scoring_standard'),
            original_question_type=qd.get('original_question_type'),
        ))
    return L2DocumentAnnotation(
        filename=data.get('filename', ''),
        questions=questions,
        annotation_version=data.get('annotation_version'),
    )


async def load_l1_fixture() -> L1Document:
    """从 DB 加载 PP-StructureV3 L1（与 golden_field_comparison.py 一致）。"""
    async with engine.connect() as conn:
        result = await conn.execute(sql_text("""
            SELECT native_markdown
            FROM documents
            WHERE filename LIKE '%东城%英语%'
            ORDER BY created_at DESC
            LIMIT 1
        """))
        row = result.fetchone()
        if not row or not row[0]:
            raise RuntimeError('东城英语文档的 native_markdown 未找到')

        lines = []
        for line in row[0].split('\n'):
            if line.startswith('[') and ']' in line:
                bracket_end = line.index(']')
                line_id = line[1:bracket_end]
                text_content = line[bracket_end+2:]
                lines.append(L1Line(
                    line_id=line_id,
                    text=text_content,
                    page_no=1,
                    line_no_in_page=len(lines) + 1,
                    order=len(lines) + 1,
                    block_type='text',
                ))
        return L1Document(filename='dongcheng_english.pdf', lines=lines)


async def load_legacy_l2() -> dict:
    """从 DB 加载 legacy L2。"""
    async with engine.connect() as conn:
        result = await conn.execute(sql_text("""
            SELECT llm_annotated_markdown::text
            FROM documents
            WHERE filename LIKE '%东城%'
            ORDER BY created_at DESC
            LIMIT 1
        """))
        row = result.fetchone()
        return json.loads(row[0])


def match_golden_questions(golden_qs, sliced_qs):
    """按 shared_material 归一化匹配 golden 和 sliced 题目。"""
    def build_key(q):
        sm = q.get('shared_material', '') if isinstance(q, dict) else (getattr(q, 'shared_material', '') or '')
        if not sm:
            sm = q.get('stem', '') if isinstance(q, dict) else (getattr(q, 'stem', '') or '')
        if not sm:
            return ''
        return normalize_shared(sm)[:80]

    db_by_key = {}
    for q in sliced_qs:
        k = build_key(q)
        if k:
            db_by_key[k] = q

    pairs = []
    for g_q in golden_qs:
        g_key = build_key(g_q)
        db_q = db_by_key.get(g_key)
        if db_q:
            pairs.append((g_q, db_q))
    return pairs


def compare_one_pair(g_q, db_q) -> dict:
    """对比一对题目，返回分类统计。"""
    stats = {'raw_exact': 0, 'format': 0, 'blank_marker': 0, 'punct_diff': 0,
             'format_diff': 0, 'number_diff': 0, 'mismatch': 0, 'granularity': 0}

    def get_val(obj, field):
        if isinstance(obj, dict):
            return obj.get(field)
        return getattr(obj, field, None)

    # 容器字段
    for field in ['stem', 'shared_material', 'scoring_standard']:
        g_val = get_val(g_q, field)
        d_val = get_val(db_q, field)
        if g_val is None and d_val is None:
            continue
        level = classify_field(g_val, d_val)
        stats[level] = stats.get(level, 0) + 1

    # 行号字段
    for field in ['stem_line_ids', 'shared_material_line_ids']:
        g_val = get_val(g_q, field)
        d_val = get_val(db_q, field)
        g_len = len(g_val) if g_val else 0
        d_len = len(d_val) if d_val else 0
        if g_len == d_len:
            stats['raw_exact'] += 1
        else:
            text_field = field.replace('_line_ids', '')
            g_text = get_val(g_q, text_field)
            d_text = get_val(db_q, text_field)
            text_level = classify_field(g_text, d_text)
            if text_level in ('raw_exact', 'format', 'blank_marker', 'punct_diff', 'format_diff'):
                stats['granularity'] += 1
            else:
                stats['mismatch'] += 1

    # 子题答案
    g_subs = get_val(g_q, 'sub_questions') or []
    d_subs = get_val(db_q, 'sub_questions') or []
    if g_subs and d_subs and len(g_subs) == len(d_subs):
        for g_sub, d_sub in zip(g_subs, d_subs):
            g_ans = get_val(g_sub, 'answer')
            d_ans = get_val(d_sub, 'answer')
            level = classify_field(g_ans, d_ans)
            stats[level] = stats.get(level, 0) + 1

    return stats


async def main():
    print('=' * 70)
    print('English A/B Golden Comparison: Modular vs Legacy')
    print('=' * 70)

    # 加载数据
    doc = await load_l1_fixture()
    golden_path = Path(__file__).resolve().parents[2] / 'test' / 'annotations' / 'golden' / 'english_2026_dongcheng_real_golden.json'
    golden = json.loads(golden_path.read_text(encoding='utf-8'))
    golden_qs = golden['questions']

    # 加载 modular L2
    modular_path = Path(__file__).resolve().parents[2] / 'backend' / 'reports' / 'modular_optimized_l2.json'
    modular_l2_data = json.loads(modular_path.read_text(encoding='utf-8'))
    modular_l2 = build_l2_from_json(modular_l2_data)
    modular_sliced = slice_questions(modular_l2, doc)

    # 加载 legacy L2
    legacy_data = await load_legacy_l2()
    legacy_l2 = build_l2_from_json(legacy_data)
    legacy_sliced = slice_questions(legacy_l2, doc)

    print(f'Golden: {len(golden_qs)} questions')
    print(f'Modular sliced: {len(modular_sliced)} questions (v{modular_l2_data.get("annotation_version", "?")})')
    print(f'Legacy sliced: {len(legacy_sliced)} questions (v{legacy_data.get("annotation_version", "?")})')
    print()

    # 匹配题目
    modular_pairs = match_golden_questions(golden_qs, modular_sliced)
    legacy_pairs = match_golden_questions(golden_qs, legacy_sliced)

    print(f'Modular matched: {len(modular_pairs)}/{len(golden_qs)} questions')
    print(f'Legacy matched: {len(legacy_pairs)}/{len(golden_qs)} questions')
    print()

    # 逐题对比
    modular_stats = {'raw_exact': 0, 'format': 0, 'blank_marker': 0, 'punct_diff': 0,
                     'format_diff': 0, 'number_diff': 0, 'mismatch': 0, 'granularity': 0}
    legacy_stats = {'raw_exact': 0, 'format': 0, 'blank_marker': 0, 'punct_diff': 0,
                    'format_diff': 0, 'number_diff': 0, 'mismatch': 0, 'granularity': 0}

    for g_q, db_q in modular_pairs:
        stats = compare_one_pair(g_q, db_q)
        for k, v in stats.items():
            modular_stats[k] += v

    for g_q, db_q in legacy_pairs:
        stats = compare_one_pair(g_q, db_q)
        for k, v in stats.items():
            legacy_stats[k] += v

    # 输出对比报告
    print('=' * 70)
    print('A/B Comparison Report')
    print('=' * 70)
    print()

    print(f'{"Category":<15} {"Modular":>10} {"Legacy":>10} {"Winner":>10}')
    print('-' * 50)
    for cat in ['raw_exact', 'format', 'blank_marker', 'punct_diff', 'format_diff', 'number_diff', 'mismatch', 'granularity']:
        m = modular_stats.get(cat, 0)
        l = legacy_stats.get(cat, 0)
        if cat in ('raw_exact', 'format', 'blank_marker', 'punct_diff', 'format_diff', 'granularity'):
            winner = 'Modular' if m > l else ('Legacy' if l > m else 'Tie')
        elif cat in ('mismatch', 'number_diff'):
            winner = 'Modular' if m < l else ('Legacy' if l < m else 'Tie')
        else:
            winner = '-'
        print(f'{cat:<15} {m:>10} {l:>10} {winner:>10}')

    print()
    m_total = sum(modular_stats.values())
    l_total = sum(legacy_stats.values())
    m_pass = modular_stats['raw_exact'] + modular_stats['format'] + modular_stats['blank_marker'] + modular_stats['punct_diff'] + modular_stats['format_diff'] + modular_stats['granularity']
    l_pass = legacy_stats['raw_exact'] + legacy_stats['format'] + legacy_stats['blank_marker'] + legacy_stats['punct_diff'] + legacy_stats['format_diff'] + legacy_stats['granularity']

    print(f'Modular pass rate: {m_pass}/{m_total} ({100*m_pass/m_total:.1f}%)')
    print(f'Legacy pass rate:  {l_pass}/{l_total} ({100*l_pass/l_total:.1f}%)')
    print()

    # 保存报告
    report = {
        'modular': {'stats': modular_stats, 'total': m_total, 'pass': m_pass, 'version': modular_l2_data.get('annotation_version')},
        'legacy': {'stats': legacy_stats, 'total': l_total, 'pass': l_pass, 'version': legacy_data.get('annotation_version')},
    }
    report_path = Path(__file__).resolve().parents[2] / 'backend' / 'reports' / 'prompt_ab_golden_compare.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Report saved to {report_path}')

    # 逐题详情
    print()
    print('=' * 70)
    print('Per-Question Details')
    print('=' * 70)
    for i, ((g_m, d_m), (g_l, d_l)) in enumerate(zip(modular_pairs, legacy_pairs)):
        qnum = g_m.get('question_number', f'Q{i+1}')
        m_stats = compare_one_pair(g_m, d_m)
        l_stats = compare_one_pair(g_l, d_l)
        m_mismatch = m_stats.get('mismatch', 0) + m_stats.get('number_diff', 0)
        l_mismatch = l_stats.get('mismatch', 0) + l_stats.get('number_diff', 0)
        m_pass_q = sum(v for k, v in m_stats.items() if k not in ('mismatch', 'number_diff'))
        l_pass_q = sum(v for k, v in l_stats.items() if k not in ('mismatch', 'number_diff'))
        status = 'SAME' if m_mismatch == l_mismatch else ('MODULAR_BETTER' if m_mismatch < l_mismatch else 'LEGACY_BETTER')
        print(f'Q{qnum}: modular={m_pass_q}pass/{m_mismatch}fail, legacy={l_pass_q}pass/{l_mismatch}fail -> {status}')


if __name__ == '__main__':
    asyncio.run(main())
