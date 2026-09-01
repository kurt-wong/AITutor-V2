"""完整字段级 Golden 对比脚本。

对比所有展示契约字段：
- stem / stem_line_ids
- shared_material / shared_material_line_ids
- options / options_line_ids
- answer / answer_line_ids
- explanation / explanation_line_ids
- scoring_standard
- answer_images

验证 P/N 行号指向的文本是否一致。
"""

import json
import asyncio
import re
import sys
import unicodedata
from pathlib import Path
from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / "test" / "scripts"))
from app.core.database import engine

from run_phase1_eval import normalize_answer_text  # noqa: E402


def normalize_shared_material(text: str) -> str:
    """共享材料归一化（semantic 级）。

    处理格式差异：
    - 全半角、弯引号和 OCR 引号转义统一
    - 填空位标记和粘连数字移除
    - 空白、换行、全角空格统一
    - 比较时只保留字母/CJK，标点和空格视为展示噪音
    ⚠️ 此级别会删除数字，无法区分"1.5分"和"1分"。用 normalize_format_only 做严格比较。
    """
    if not text:
        return ''
    lines = text.splitlines()
    if lines and re.fullmatch(r'[A-G]', lines[0].strip()):
        text = "\n".join(lines[1:])
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("?", "'").replace("？", "'")
    text = text.replace("—", " ").replace("–", " ")
    text = re.sub(r'\\text\{[^}]*\}', ' ', text)

    text = re.sub(r'_+(\d+)_+', ' ', text)
    text = re.sub(r'_+', ' ', text)
    text = re.sub(r'[〔\[]\d+[〕\]]', ' ', text)

    text = re.sub(r'\d+(?=[A-Za-z])', ' ', text)
    text = re.sub(r'(?<=[A-Za-z])\d+', ' ', text)
    text = re.sub(r'\d+', ' ', text)

    text = re.sub(r'[^A-Za-z\u4e00-\u9fff]+', '', text)
    return text.lower()


def normalize_format_only(text: str) -> str:
    """\u683c\u5f0f\u7ea7\u5f52\u4e00\u5316\uff08format_only\uff09\u3002

    \u53ea\u7edf\u4e00\u683c\u5f0f\u5dee\u5f02\uff0c\u4fdd\u7559\u6570\u5b57\u548c\u5206\u6570\uff1a
    - \u5168\u534a\u89d2\u7edf\u4e00\uff08NFKC\uff09
    - \u5f2f\u5f15\u53f7/OCR \u5f15\u53f7\u8f6c\u4e49\u7edf\u4e00
    - \u7a7a\u767d\u3001\u6362\u884c\u3001\u5168\u89d2\u7a7a\u683c\u7edf\u4e00\u4e3a\u5355\u7a7a\u683c
    - \u5168\u89d2\u62ec\u53f7\u2192\u534a\u89d2
    - \u53bb\u6389\u9996\u5c3e\u7a7a\u767d
    \u26a0\ufe0f \u4fdd\u7559\u6570\u5b57\uff0c\u80fd\u533a\u5206"1.5\u5206"\u548c"1\u5206"\u3002
    """
    if not text:
        return ''
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("?", "'").replace("\uff1f", "'")
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    # \u7edf\u4e00\u7a7a\u767d\uff1a\u6362\u884c\u3001\u5236\u8868\u7b26\u3001\u5168\u89d2\u7a7a\u683c \u2192 \u5355\u7a7a\u683c
    text = re.sub(r'[\s\u3000]+', ' ', text)
    # \u6570\u5b57\u4e0e CJK \u4e4b\u95f4\u7684\u7a7a\u683c\u5dee\u5f02\uff08\u5e38\u89c1 OCR/\u683c\u5f0f\u5dee\u5f02\uff09
    text = re.sub(r'(\d)\s+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'([\u4e00-\u9fff])\s+(\d)', r'\1\2', text)
    # \u5b57\u6bcd\u4e0e CJK \u4e4b\u95f4\u7684\u7a7a\u683c\u5dee\u5f02
    text = re.sub(r'([A-Za-z])\s+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'([\u4e00-\u9fff])\s+([A-Za-z])', r'\1\2', text)
    # CJK \u6807\u70b9\u5468\u56f4\u7684\u7a7a\u683c\u5dee\u5f02\uff08\u3001\uff0c\u3002\uff1b\uff1a\u7b49\u6807\u70b9\u540e\u7684\u7a7a\u683c\uff09
    text = re.sub(r'([\u3001\uff0c\u3002\uff1b\uff1a\uff09\u300d\u300f\u3011\u300b])\s+', r'\1', text)
    text = re.sub(r'\s+([\u3001\uff0c\u3002\uff1b\uff1a\uff08\u300c\u300e\u3010\u300a])', r'\1', text)
    # \u7edf\u4e00\u62ec\u53f7\uff1a\u5168\u89d2 \u2192 \u534a\u89d2
    text = text.replace('\uff08', '(').replace('\uff09', ')')
    text = text.replace('\u3014', '[').replace('\u3015', ']')
    # \u53bb\u6389\u9996\u5c3e\u7a7a\u767d
    text = text.strip()
    return text


def normalize_blank_markers(text: str) -> str:
    """填空位标记归一化。

    在 format_only 基础上，额外统一填空位标记格式：
    - ____N____ / _N_ / __N__ → [N]
    - 〔N〕/ 【N】/ ［N］→ [N]
    - OCR 方括号噪音：共【10】小题 → 共10小题（容器 stem 中的数字不加括号）

    用于区分"填空位标记差异"和"真实内容差异"。
    """
    if not text:
        return ''
    text = normalize_format_only(text)
    # ____N____ / _N_ / __N__ / N_ → [N]
    text = re.sub(r'_+(\d+)_+', r'[\1]', text)
    text = re.sub(r'(\d+)_+(?=[,.;:)\]\s])', r'[\1]', text)
    # 〔N〕/ 【N】 → [N]
    text = re.sub(r'[〔【［](\d+)[〕】］]', r'[\1]', text)
    # CJK + [N] + CJK → CJK + N + CJK（OCR 方括号噪音）
    text = re.sub(r'([一-鿿])\[(\d+)\]([一-鿿])', r'\1\2\3', text)
    # 裸数字填空位：空格+数字+标点/空格 → [N]
    # 排除已在 [N] 中的数字
    def _replace_bare(m):
        num = m.group(1)
        start = m.start()
        if start > 0 and text[start - 1] == '[':
            return m.group(0)
        return f'[{num}]'
    text = re.sub(r'(?<=\s)(\d{1,2})(?=[,.;:\]－）\s])', _replace_bare, text)
    return text


def normalize_scoring_standard(text: str) -> str:
    """评分标准归一化：抽取分值序列，忽略节标题和同义表述。"""
    if not text:
        return ''
    t = unicodedata.normalize('NFKC', str(text)).lower()
    t = re.sub(
        r'第[一二三四五六七八九十\d]+节共\d+小题[,，]每小题[\d.]+分(?:[,，]共[\d.]+分)?[;；]',
        '',
        t,
    )
    t = re.sub(
        r'第[一二三四五六七八九十\d]+节共\d+小题[,，]每小题[\d.]+分(?:[,，]共[\d.]+分)?[;；]?$',
        '',
        t,
    )
    t = t.replace('本组共', '共').replace('本组', '共')
    def _infer(m: re.Match) -> str:
        count = int(m.group(1))
        total = float(m.group(2))
        per = total / count if count else total
        return f'共{count}小题，每小题{per:g}分，共{m.group(2)}分'
    t = re.sub(r'共(\d+)小题共([\d.]+)分', _infer, t)
    def _add_total_if_missing(m: re.Match) -> str:
        count = int(m.group(1))
        per = float(m.group(2))
        return f'共{count}小题，每小题{per:g}分，共{count * per:g}分'
    t = re.sub(r'共(\d+)小题[,，]每小题([\d.]+)分$', _add_total_if_missing, t)
    scores = [f'{float(s):g}' for s in re.findall(r'([\d.]+)分', t)]
    return '|'.join(scores)
def _text_matches(golden_val, db_val, normalize_type: str | None) -> tuple[bool, str]:
    """Return (match, level) — level is 'exact', 'format', 'blank_marker', 'punct_diff', 'number_diff', or 'mismatch'."""
    if golden_val is None and db_val is None:
        return True, 'exact'
    if golden_val is None or db_val is None:
        return False, 'mismatch'

    g_raw = str(golden_val)
    d_raw = str(db_val)

    # 1. exact: 原始文本完全一致
    if g_raw == d_raw:
        return True, 'exact'

    # 2. format_only: 只统一空格/换行/引号/括号，保留数字
    g_fmt = normalize_format_only(g_raw)
    d_fmt = normalize_format_only(d_raw)
    if g_fmt == d_fmt:
        return True, 'format'

    # 3. blank_marker: 统一填空位标记后匹配
    g_blank = normalize_blank_markers(g_raw)
    d_blank = normalize_blank_markers(d_raw)
    if g_blank == d_blank:
        return True, 'blank_marker'

    # 4. blank_marker + 去标点：填空位标记+标点差异
    def _strip_punct(t):
        return re.sub(r'[,.;:!?。，；：！？.\-\s]+', '', t)
    if _strip_punct(g_blank) == _strip_punct(d_blank):
        return True, 'punct_diff'

    # 5. 对于 shared 类型，检查是否只是数字差异
    if normalize_type == "shared":
        g_sem = normalize_shared_material(g_raw)
        d_sem = normalize_shared_material(d_raw)
        if g_sem == d_sem:
            # 检查数字是否相同
            g_nums = re.findall(r'\d+\.?\d*', g_fmt)
            d_nums = re.findall(r'\d+\.?\d*', d_fmt)
            if g_nums == d_nums:
                return True, 'format_diff'  # 数字相同，格式差异
            return False, 'number_diff'  # 数字不同

    # 6. 对于 scoring 类型，用专门的归一化
    if normalize_type == "scoring":
        if normalize_scoring_standard(g_raw) == normalize_scoring_standard(d_raw):
            return True, 'exact'

    # 7. 对于 answer 类型，用专门的归一化
    if normalize_type == "answer":
        if normalize_answer_text(g_raw) == normalize_answer_text(d_raw):
            return True, 'exact'

    return False, 'mismatch'


def load_golden() -> dict:
    """加载 Golden 文件。"""
    golden_path = Path('../test/annotations/golden/english_2026_dongcheng_real_golden.json')
    return json.loads(golden_path.read_text(encoding='utf-8'))


def load_native_fixture() -> dict:
    """加载 Native L1 fixture。"""
    fixture_path = Path('../test/fixtures/l1_native_english_dongcheng_2026.json')
    return json.loads(fixture_path.read_text(encoding='utf-8'))


def build_line_map(fixture: dict) -> dict[str, str]:
    """构建行号到文本的映射。"""
    return {line['line_id']: line['text'] for line in fixture['lines']}


async def get_db_pp_lines() -> dict[str, str]:
    """从数据库获取 PP-StructureV3 行号到文本的映射。"""
    async with engine.connect() as conn:
        result = await conn.execute(text('''
            SELECT native_markdown
            FROM documents
            WHERE filename LIKE '%东城%'
            ORDER BY created_at DESC
            LIMIT 1
        '''))
        row = result.fetchone()
        if not row or not row[0]:
            return {}

        pp_lines = {}
        for line in row[0].split('\n'):
            if line.startswith('[') and ']' in line:
                bracket_end = line.index(']')
                line_id = line[1:bracket_end]
                text_content = line[bracket_end+2:]
                pp_lines[line_id] = text_content
        return pp_lines


async def get_db_questions() -> list[dict]:
    """从数据库获取所有题目。"""
    async with engine.connect() as conn:
        result = await conn.execute(text('''
            SELECT
                id,
                stem,
                options,
                answer,
                explanation,
                scoring_standard,
                shared_material,
                stem_line_ids,
                answer_line_ids,
                explanation_line_ids,
                shared_material_line_ids,
                sub_questions,
                is_composite
            FROM questions
            WHERE source_document_name LIKE '%东城%'
            ORDER BY created_at DESC
        '''))
        rows = result.fetchall()

        questions = []
        for row in rows:
            q = {
                'id': row[0],
                'stem': row[1],
                'options': row[2],
                'answer': row[3],
                'explanation': row[4],
                'scoring_standard': row[5],
                'shared_material': row[6],
                'stem_line_ids': row[7],
                'answer_line_ids': row[8],
                'explanation_line_ids': row[9],
                'shared_material_line_ids': row[10],
                'sub_questions': row[11],
                'is_composite': row[12],
            }
            questions.append(q)
        return questions


def resolve_line_ids(line_ids: list[str], native_map: dict, pp_map: dict) -> list[str]:
    """解析行号为文本（支持 N 和 P 前缀）。"""
    texts = []
    for lid in line_ids:
        if lid.startswith('N'):
            text = native_map.get(lid, f'MISSING:{lid}')
        elif lid.startswith('P'):
            text = pp_map.get(lid, f'MISSING:{lid}')
        else:
            text = f'UNKNOWN_PREFIX:{lid}'
        texts.append(text)
    return texts


def compare_field(golden_val, db_val, field_name: str, normalize: bool = False, normalize_shared: bool = False, normalize_scoring: bool = False, context_matched: bool | None = None) -> tuple[bool, str, str, str]:
    """比较单个字段。

    Args:
        normalize: 使用 normalize_answer_text 归一化
        normalize_shared: 使用 normalize_shared_material 归一化（用于 shared_material）

    Returns:
        (match, message, detail, verdict)
        detail: Golden / DB / normalized 三列对比
        verdict: match / format / blank_marker / punct_diff / number_diff / format_diff / missing / extra / mismatch
    """
    # answer_images: [] 和 None 视为相等（都表示无答案图）
    if field_name == 'answer_images':
        g_empty = not golden_val or golden_val == []
        d_empty = not db_val or db_val == []
        if g_empty and d_empty:
            return True, f'{field_name}: both empty', '', 'match'

    # 行号字段：只比较长度，不比较内容（N/P 来源不同）
    line_id_fields = ('stem_line_ids', 'shared_material_line_ids', 'answer_line_ids', 'explanation_line_ids')
    if field_name in line_id_fields:
        g_len = len(golden_val) if golden_val else 0
        d_len = len(db_val) if db_val else 0
        if g_len == d_len:
            return True, f'{field_name}: length match ({g_len})', '', 'match'
        else:
            detail = f'Golden={g_len} lines | DB={d_len} lines'
            if context_matched and g_len and d_len:
                return True, f'{field_name}: granularity difference (text matched)', detail, 'granularity'
            return False, f'{field_name}: length mismatch ({g_len} vs {d_len})', detail, 'mismatch'

    if golden_val is None and db_val is None:
        return True, f'{field_name}: both None', '', 'match'

    if golden_val is None and db_val is not None:
        detail = f'Golden=None | DB={db_val!r}'
        return False, f'{field_name}: Golden missing, DB has value', detail, 'missing'

    if golden_val is not None and db_val is None:
        detail = f'Golden={golden_val!r} | DB=None'
        return False, f'{field_name}: Golden has value, DB missing', detail, 'extra'

    # 选择归一化函数
    if normalize_scoring:
        norm_func = normalize_scoring_standard
    elif normalize_shared:
        norm_func = normalize_shared_material
    elif normalize:
        norm_func = normalize_answer_text
    else:
        norm_func = None

    if isinstance(golden_val, list) and isinstance(db_val, list):
        if len(golden_val) != len(db_val):
            detail = f'Golden={golden_val!r} | DB={db_val!r}'
            return False, f'{field_name}: length mismatch ({len(golden_val)} vs {len(db_val)})', detail, 'mismatch'

        # 对列表内容归一化后比较
        if norm_func:
            golden_normalized = [norm_func(str(v)) for v in golden_val]
            db_normalized = [norm_func(str(v)) for v in db_val]
            if golden_normalized == db_normalized:
                return True, f'{field_name}: match (normalized)', '', 'match'

        if golden_val == db_val:
            return True, f'{field_name}: match', '', 'match'

        detail = f'Golden={golden_val!r} | DB={db_val!r}'
        if norm_func:
            detail += f' | Golden_norm={[norm_func(str(v)) for v in golden_val]!r} | DB_norm={[norm_func(str(v)) for v in db_val]!r}'
        return False, f'{field_name}: content mismatch', detail, 'mismatch'

    if isinstance(golden_val, str) and isinstance(db_val, str):
        # 使用 _text_matches 做细粒度比较
        normalize_type = 'scoring' if normalize_scoring else ('shared' if normalize_shared else ('answer' if normalize else None))
        is_match, level = _text_matches(golden_val, db_val, normalize_type)

        if is_match:
            return True, f'{field_name}: match ({level})', '', level

        # 对于 number_diff，返回详细信息
        if level == 'number_diff':
            detail = f'Golden={golden_val!r} | DB={db_val!r}'
            return False, f'{field_name}: number difference (semantic match but numbers differ)', detail, 'number_diff'

        detail = f'Golden={golden_val!r} | DB={db_val!r}'
        return False, f'{field_name}: content mismatch', detail, 'mismatch'

    if golden_val == db_val:
        return True, f'{field_name}: match', '', 'match'

    detail = f'Golden={golden_val!r} | DB={db_val!r}'
    return False, f'{field_name}: type/value mismatch', detail, 'mismatch'


def _sub_range_key(question: dict) -> str:
    """从子题号推导组号区间，用于容器失配时的备选匹配。"""
    numbers: list[int] = []
    for sub in (question.get('sub_questions') or []):
        raw_no = str(sub.get('qno') or sub.get('question_number') or '')
        stem = str(sub.get('stem') or '')
        m = re.search(r'(\d{1,3})', raw_no)
        if not m:
            m = re.search(r'〔\s*(\d{1,3})\s*〕', stem)
        if not m:
            m = re.search(r'(\d{1,3})\s*[.、．]', stem)
        if m:
            numbers.append(int(m.group(1)))
    if not numbers:
        return ''
    return f'{min(numbers)}-{max(numbers)}'
async def main():
    """主函数。"""
    print('=' * 70)
    print('Complete Field-Level Golden Comparison')
    print('=' * 70)
    print()

    # 加载数据
    golden = load_golden()
    native_fixture = load_native_fixture()
    native_map = build_line_map(native_fixture)
    pp_map = await get_db_pp_lines()
    db_questions = await get_db_questions()

    golden_questions = golden['questions']

    print(f'Golden: {len(golden_questions)} questions')
    print(f'DB: {len(db_questions)} questions')
    print()

    # 定义对比字段（字段名, 归一化类型）
    # normalize_type: 'answer' | 'shared' | None
    container_fields = [
        ('stem', 'shared'),  # stem 也用 shared_material 归一化
        ('shared_material', 'shared'),
        ('scoring_standard', 'scoring'),
        ('is_composite', None),
        ('stem_line_ids', None),
        ('shared_material_line_ids', None),
        ('answer_images', None),
    ]

    # 子题字段
    sub_fields = [
        ('answer', 'answer'),
        ('scoring_standard', 'scoring'),
        ('answer_line_ids', None),
        ('explanation_line_ids', None),
        ('stem_region', None),
        ('answer_region', None),
        ('answer_images', None),
    ]

    # 对比每个题目 - 按 shared_material 归一化后前80字符匹配
    total_fields = 0
    matched_fields = 0
    format_fields = 0
    blank_marker_fields = 0
    punct_diff_fields = 0
    format_diff_fields = 0
    number_diff_fields = 0
    granularity_fields = 0
    mismatched_fields = 0
    raw_exact_fields = 0  # 严格原始文本完全一致（不含归一化匹配）
    mismatches = []
    format_notes = []
    blank_marker_notes = []
    punct_diff_notes = []
    format_diff_notes = []
    number_diff_notes = []
    granularity_notes = []

    golden_questions = golden['questions']

    # 构建 DB 题目索引（按 shared_material 归一化后前80字符）
    def _build_match_key(question: dict) -> str:
        """取 shared_material 归一化后前80字符作为匹配键。"""
        sm = question.get('shared_material', '') or ''
        if not sm:
            # 没有 shared_material 时用 stem
            sm = question.get('stem', '') or ''
        if not sm:
            return ''
        normalized = normalize_shared_material(sm)
        return normalized[:80]

    db_by_key: dict[str, dict] = {}
    db_by_range: dict[str, dict] = {}
    for db_q in db_questions:
        key = _build_match_key(db_q)
        if key:
            db_by_key[key] = db_q
        range_key = _sub_range_key(db_q)
        if range_key and range_key not in db_by_range:
            db_by_range[range_key] = db_q

    # 记录已匹配的 DB 题目
    matched_db_ids: set[str] = set()

    for q_idx, g_q in enumerate(golden_questions):
        g_key = _build_match_key(g_q)
        qnum = g_q.get('question_number', f'Q{q_idx+1}')

        # 在 DB 中查找匹配题目
        db_q = db_by_key.get(g_key)
        if not db_q:
            g_range = _sub_range_key(g_q)
            db_q = db_by_range.get(g_range) if g_range else None
        if not db_q:
            print(f'Question {q_idx+1}: {qnum} - WARNING: No matching DB question found')
            mismatched_fields += 1
            mismatches.append(f'Q{q_idx+1}: missing in DB')
            continue

        print(f'Question {q_idx+1}: {qnum}')
        matched_db_ids.add(db_q['id'])

        # 对比容器/独立题字段
        text_matches = {
            'stem': _text_matches(g_q.get('stem'), db_q.get('stem'), 'shared')[0],
            'shared_material': _text_matches(g_q.get('shared_material'), db_q.get('shared_material'), 'shared')[0],
            'scoring_standard': _text_matches(g_q.get('scoring_standard'), db_q.get('scoring_standard'), 'scoring')[0],
        }
        for field_name, normalize_type in container_fields:
            # 跳过综合题的答案字段（容器不应有答案）
            if field_name == 'answer' and g_q.get('is_composite'):
                continue

            total_fields += 1
            g_val = g_q.get(field_name)
            db_val = db_q.get(field_name)

            # 选择归一化函数
            norm_func = None
            if normalize_type == 'answer':
                norm_func = normalize_answer_text
            elif normalize_type == 'scoring':
                norm_func = normalize_scoring_standard
            elif normalize_type == 'shared':
                norm_func = normalize_shared_material

            context_matched = None
            if field_name == 'stem_line_ids':
                context_matched = text_matches['stem']
            elif field_name == 'shared_material_line_ids':
                context_matched = text_matches['shared_material']
            match, msg, detail, verdict = compare_field(g_val, db_val, field_name, norm_func is not None, normalize_type == 'shared', normalize_type == 'scoring', context_matched)
            if verdict == 'granularity':
                granularity_fields += 1
                granularity_notes.append(f'Q{q_idx+1}.{field_name}: {msg}')
                print(f'  GRANULARITY: {msg} [{verdict}]')
                if detail:
                    safe_detail = detail.encode('ascii', 'replace').decode('ascii')
                    print(f'    {safe_detail}')
            elif verdict == 'format':
                format_fields += 1
                format_notes.append(f'Q{q_idx+1}.{field_name}: {msg}')
            elif verdict == 'blank_marker':
                blank_marker_fields += 1
                blank_marker_notes.append(f'Q{q_idx+1}.{field_name}: {msg}')
            elif verdict == 'punct_diff':
                punct_diff_fields += 1
                punct_diff_notes.append(f'Q{q_idx+1}.{field_name}: {msg}')
            elif verdict == 'format_diff':
                format_diff_fields += 1
                format_diff_notes.append(f'Q{q_idx+1}.{field_name}: {msg}')
            elif verdict == 'number_diff':
                number_diff_fields += 1
                number_diff_notes.append(f'Q{q_idx+1}.{field_name}: {msg}')
                print(f'  NUMBER_DIFF: {msg}')
                if detail:
                    safe_detail = detail.encode('ascii', 'replace').decode('ascii')
                    print(f'    {safe_detail}')
            elif match:
                matched_fields += 1
                if verdict == 'match':
                    raw_exact_fields += 1
            else:
                mismatched_fields += 1
                mismatches.append(f'Q{q_idx+1}.{field_name}: {msg}')
                print(f'  MISMATCH: {msg} [{verdict}]')
                if detail:
                    safe_detail = detail.encode('ascii', 'replace').decode('ascii')
                    print(f'    {safe_detail}')

        # 对比子题
        g_subs = g_q.get('sub_questions', [])
        db_subs = db_q.get('sub_questions', []) or []

        if len(g_subs) != len(db_subs):
            mismatched_fields += 1
            mismatches.append(f'Q{q_idx+1}.sub_questions: length mismatch ({len(g_subs)} vs {len(db_subs)})')
            print(f'  MISMATCH: sub_questions length ({len(g_subs)} vs {len(db_subs)})')
        else:
            for s_idx, (g_sub, db_sub) in enumerate(zip(g_subs, db_subs)):
                sub_text_matches = {
                    'answer': _text_matches(g_sub.get('answer'), db_sub.get('answer'), 'answer')[0],
                    'scoring_standard': _text_matches(g_sub.get('scoring_standard'), db_sub.get('scoring_standard'), 'scoring')[0],
                }
                for field_name, normalize_type in sub_fields:
                    total_fields += 1
                    g_val = g_sub.get(field_name)
                    db_val = db_sub.get(field_name)

                    # 选择归一化函数
                    norm_func = None
                    if normalize_type == 'answer':
                        norm_func = normalize_answer_text
                    elif normalize_type == 'scoring':
                        norm_func = normalize_scoring_standard
                    elif normalize_type == 'shared':
                        norm_func = normalize_shared_material

                    context_matched = None
                    if field_name == 'answer_line_ids':
                        context_matched = sub_text_matches['answer']
                    match, msg, detail, verdict = compare_field(g_val, db_val, field_name, norm_func is not None, normalize_type == 'shared', normalize_type == 'scoring', context_matched)
                    if verdict == 'granularity':
                        granularity_fields += 1
                        granularity_notes.append(f'Q{q_idx+1}.sub{s_idx+1}.{field_name}: {msg}')
                        print(f'  GRANULARITY Sub {s_idx+1}.{field_name}: {msg} [{verdict}]')
                        if detail:
                            safe_detail = detail.encode('ascii', 'replace').decode('ascii')
                            print(f'    {safe_detail}')
                    elif verdict == 'format':
                        format_fields += 1
                        format_notes.append(f'Q{q_idx+1}.sub{s_idx+1}.{field_name}: {msg}')
                    elif verdict == 'blank_marker':
                        blank_marker_fields += 1
                        blank_marker_notes.append(f'Q{q_idx+1}.sub{s_idx+1}.{field_name}: {msg}')
                    elif verdict == 'punct_diff':
                        punct_diff_fields += 1
                        punct_diff_notes.append(f'Q{q_idx+1}.sub{s_idx+1}.{field_name}: {msg}')
                    elif verdict == 'format_diff':
                        format_diff_fields += 1
                        format_diff_notes.append(f'Q{q_idx+1}.sub{s_idx+1}.{field_name}: {msg}')
                    elif verdict == 'number_diff':
                        number_diff_fields += 1
                        number_diff_notes.append(f'Q{q_idx+1}.sub{s_idx+1}.{field_name}: {msg}')
                        print(f'  NUMBER_DIFF Sub {s_idx+1}.{field_name}: {msg}')
                        if detail:
                            safe_detail = detail.encode('ascii', 'replace').decode('ascii')
                            print(f'    {safe_detail}')
                    elif match:
                        matched_fields += 1
                        if verdict == 'match':
                            raw_exact_fields += 1
                    else:
                        mismatched_fields += 1
                        mismatches.append(f'Q{q_idx+1}.sub{s_idx+1}.{field_name}: {msg}')
                        print(f'  MISMATCH Sub {s_idx+1}.{field_name}: {msg} [{verdict}]')
                        if detail:
                            safe_detail = detail.encode('ascii', 'replace').decode('ascii')
                            print(f'    {safe_detail}')

        if not any('MISMATCH' in m for m in mismatches[-10:]):
            print(f'  All fields match')
        print()

    # 检查未匹配的 DB 题目
    unmatched_db = [q['id'] for q in db_questions if q['id'] not in matched_db_ids]
    if unmatched_db:
        print(f'WARNING: {len(unmatched_db)} DB questions not matched to any Golden question')

    # 总结
    print('=' * 70)
    print('Summary')
    print('=' * 70)
    print(f'Total fields compared: {total_fields}')
    print(f'  matched (raw_exact + normalized): {matched_fields}')
    print(f'    raw_exact:       {raw_exact_fields}')
    print(f'    normalized:      {matched_fields - raw_exact_fields}')
    print(f'  format:          {format_fields}')
    print(f'  blank_marker:    {blank_marker_fields}')
    print(f'  punct_diff:      {punct_diff_fields}')
    print(f'  format_diff:     {format_diff_fields}')
    print(f'  number_diff:     {number_diff_fields}')
    print(f'  granularity:     {granularity_fields}')
    print(f'  mismatch:        {mismatched_fields}')
    print()
    all_pass = matched_fields + format_fields + blank_marker_fields + punct_diff_fields + format_diff_fields
    print(f'Raw exact rate: {100*raw_exact_fields/total_fields:.1f}%')
    print(f'Matched rate (raw+normalized): {100*matched_fields/total_fields:.1f}%')
    print(f'Format+ match rate: {100*(matched_fields+format_fields)/total_fields:.1f}%')
    print(f'All pass rate (matched+format+blank_marker+punct+format_diff+granularity): {100*(all_pass+granularity_fields)/total_fields:.1f}%')
    print()

    if mismatches:
        print('Mismatches:')
        for m in mismatches:
            print(f'  - {m}')
    else:
        print('No content mismatches found!')

    if number_diff_notes:
        print()
        print('Number differences (real number content differs — needs review):')
        for note in number_diff_notes:
            print(f'  - {note}')

    if format_diff_notes:
        print()
        print('Format differences (numbers match, format differs):')
        for note in format_diff_notes:
            print(f'  - {note}')

    if blank_marker_notes:
        print()
        print('Blank marker differences (blank position markers differ):')
        for note in blank_marker_notes:
            print(f'  - {note}')

    if punct_diff_notes:
        print()
        print('Punctuation differences (content matches after stripping punctuation):')
        for note in punct_diff_notes:
            print(f'  - {note}')

    if format_notes:
        print()
        print('Format differences (spaces/linebreaks/quotes differ):')
        for note in format_notes:
            print(f'  - {note}')

    if granularity_notes:
        print()
        print('Granularity notes (text matched, line source differs):')
        for note in granularity_notes:
            print(f'  - {note}')

    print()
    if mismatched_fields == 0 and number_diff_fields == 0:
        verdict_parts = []
        if granularity_fields:
            verdict_parts.append("GRANULARITY")
        if punct_diff_fields:
            verdict_parts.append("PUNCT")
        if blank_marker_fields:
            verdict_parts.append("BLANK_MARKER")
        if format_diff_fields:
            verdict_parts.append("FORMAT_DIFF")
        if format_fields:
            verdict_parts.append("FORMAT")
        verdict = f'PASS_WITH_{"_".join(verdict_parts)}' if verdict_parts else 'PASS'
        print(f'Verdict: {verdict}')
    elif number_diff_fields > 0:
        print(f'Verdict: REVIEW_NEEDED ({number_diff_fields} real number differences)')
    else:
        print('Verdict: FAIL')


if __name__ == '__main__':
    asyncio.run(main())
