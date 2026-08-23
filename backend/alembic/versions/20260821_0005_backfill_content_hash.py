"""Phase 2A Step 5: backfill content_hash for existing questions

Revision ID: 20260821_0005
Revises: 20260821_0003
Create Date: 2026-08-21

Step 5 changes:
- Backfill questions.content_hash from normalized stem + options + question_type
- No schema change (content_hash column already added in 20260821_0003)

规范化规则与 backend/app/domains/document/content_hash.py 保持一致：
NFKC + 全角转半角 + 去空白/标点 + 小写 → SHA256(规范stem + 规范options + 规范type)。
子题（is_composite）的 qno+type+answer 参与 hash。
"""

from alembic import op
import sqlalchemy as sa
import hashlib
import json
import re
import unicodedata

# revision identifiers
revision = "20260821_0005"
down_revision = "20260821_0003"
branch_labels = None
depends_on = None

_PUNCTUATION = set(
    " \t\n\r\u3000　，。！？；：、（）()【】[]《》〈〉「」『』“”‘’\"'…—–-·•.,!?;:"
)


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", text)
    chars = []
    for ch in s:
        if ch in _PUNCTUATION or ch.isspace():
            continue
        chars.append(ch.lower())
    return "".join(chars)


def _normalize_options(options) -> str:
    if not options:
        return ""
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except Exception:
            return _normalize(options)
    if not isinstance(options, list):
        return ""
    items = []
    for opt in options:
        if isinstance(opt, dict):
            label = _normalize(str(opt.get("label", "")))
            text = _normalize(str(opt.get("text", "")))
            items.append(f"{label}:{text}")
        else:
            items.append(_normalize(str(opt)))
    return "|".join(sorted(items))


def _normalize_sub_questions(sub_questions) -> str:
    if not sub_questions:
        return ""
    if isinstance(sub_questions, str):
        try:
            sub_questions = json.loads(sub_questions)
        except Exception:
            return _normalize(sub_questions)
    if not isinstance(sub_questions, list):
        return ""
    items = []
    for sub in sub_questions:
        if isinstance(sub, dict):
            qno = _normalize(str(sub.get("qno", "")))
            qtype = _normalize(str(sub.get("question_type", "")))
            answer = _normalize(str(sub.get("answer", "")))
            items.append(f"{qno}:{qtype}:{answer}")
    return "|".join(sorted(items))


def _compute_hash(row) -> str:
    stem = _normalize(row.get("stem"))
    options = _normalize_options(row.get("options"))
    qtype = _normalize(row.get("question_type"))
    subs = _normalize_sub_questions(row.get("sub_questions"))
    canonical = "\x00".join([stem, options, qtype, subs])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upgrade() -> None:
    """回填 content_hash：所有 content_hash 为 NULL 的 questions。"""
    conn = op.get_bind()
    # question_type 通过 question_type_id → question_types.code 获取
    rows = conn.execute(sa.text("""
        SELECT q.id, q.stem, q.options, q.sub_questions,
               qt.code AS question_type
        FROM questions q
        LEFT JOIN question_types qt ON qt.id = q.question_type_id
        WHERE q.content_hash IS NULL
    """)).fetchall()
    updated = 0
    for row in rows:
        data = {
            "stem": row.stem,
            "options": row.options,
            "question_type": row.question_type,
            "sub_questions": row.sub_questions,
        }
        h = _compute_hash(data)
        conn.execute(
            sa.text("UPDATE questions SET content_hash = :h WHERE id = :id"),
            {"h": h, "id": row.id},
        )
        updated += 1
    # 兜底：任何剩余 NULL（如无法归一化的极端数据）用 stem 兜底 hash，保证无 NULL
    conn.execute(sa.text("""
        UPDATE questions SET content_hash = encode(sha256(stem::bytea), 'hex')
        WHERE content_hash IS NULL AND stem IS NOT NULL
    """))
    remaining = conn.execute(sa.text(
        "SELECT count(*) FROM questions WHERE content_hash IS NULL"
    )).scalar()
    print(f"[20260821_0005] backfilled content_hash for {updated} questions, remaining NULL: {remaining}")


def downgrade() -> None:
    """降级：content_hash 列由 20260821_0003 管理，本步不回填逻辑，置空即可。"""
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE questions SET content_hash = NULL"))
    print("[20260821_0005] content_hash cleared (downgrade)")
