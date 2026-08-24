#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""e2e 语义验收报告 v2：DB 与原始 L1/L2/管线产物逐题对齐。

与 v1 的差异：
- stem 不再只做全文宽匹配，增加“所在 section”和“越界/串题”检查。
- composite 材料验证：有 shared_material 的题，DB stem 必须包含材料内容。
- options 归属验证：每个选项必须在当前题 section 内，而不是只存在于全文某处。
- 被过滤题追踪：从 background_tasks.result_json 提取 discarded_questions 和 ingestion 缺口。

运行方式：
    python test/scripts/e2e_semantic_report.py --subject 语文
    python test/scripts/e2e_semantic_report.py --subject 英语
    python test/scripts/e2e_semantic_report.py --all

脚本只读 DB 和本地产物，不改业务代码。
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from answer_verifier import (  # noqa: E402
    MATCHED,
    UNVERIFIABLE,
    AnswerVerification,
    verify_document_answers,
)

if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:15432/aitutors",
)


# ---------- 文本工具 ----------


def compact_text(text: str | None) -> str:
    """去掉空白、全角转半角、统一常见引号，用于定位和包含判断。"""
    if not text:
        return ""
    out: list[str] = []
    for ch in str(text):
        code = ord(ch)
        if ch in "\u2018\u2019":
            out.append("'")
            continue
        if ch in "\u201c\u201d":
            out.append('"')
            continue
        if ch == "\u3000":
            continue
        if 0xFF01 <= code <= 0xFF5E:
            out.append(chr(code - 0xFEE0))
            continue
        if ch.isspace():
            continue
        out.append(ch)
    return "".join(out)


def line_coverage(needle: str | None, haystack_compact: str) -> float:
    """按 DB/产物中的原始行统计有多少行能落在目标文本里。"""
    lines = [
        compact_text(line)
        for line in (needle or "").splitlines()
        if compact_text(line)
    ]
    if not lines:
        return 1.0
    hits = sum(1 for line in lines if line in haystack_compact)
    return hits / len(lines)


def chunk_coverage(needle: str | None, haystack_compact: str, size: int = 40) -> float:
    """长文本覆盖：把 expected 切成连续片段，统计多少片段落在目标文本里。"""
    compact_needle = compact_text(needle)
    if not compact_needle:
        return 1.0
    chunks = [
        compact_needle[i : i + size]
        for i in range(0, max(1, len(compact_needle)), size)
    ]
    if not chunks:
        return 1.0
    hits = sum(1 for chunk in chunks if chunk in haystack_compact)
    return hits / len(chunks)


def find_marker(source_compact: str, marker: str | None, from_pos: int = 0) -> int:
    needle = compact_text(marker)
    if not needle:
        return -1
    candidates = [needle]
    if len(needle) > 12:
        candidates.append(needle[:12])
    for candidate in candidates:
        if len(candidate) < 4:
            continue
        pos = source_compact.find(candidate, from_pos)
        if pos >= 0:
            return pos
    return -1


def parse_json(value) -> dict | list | None:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None
    return None


def to_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def qn_num(qn: str | None) -> int:
    m = re.search(r"\d+", str(qn or ""))
    return int(m.group(0)) if m else 9999


def section_headers(text: str) -> list[str]:
    """识别大题/部分/节标题，用于串题检查。"""
    headers: list[str] = []
    patterns = [
        r"[一二三四五六七八九十]+、本大题",
        r"第[一二三四五六七八九十]+部分",
        r"第[一二三四五六七八九十]+节",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            value = compact_text(m.group(0))
            if value and value not in headers:
                headers.append(value)
    return headers


def extract_answer_section(text: str) -> str:
    if not text:
        return ""
    patterns = [
        "\u53c2\u8003\u7b54\u6848",
        "\u7b54\u6848[\uff1a:]",
        "Answer\\s*Key",
        "[\u3010]\u7b54\u6848[\u3011]",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return text[m.start() :]
    return ""


def find_answer_evidence(
    qn: str,
    expected: str | None,
    answer_compact: str,
    sub_qno: str | None = None,
) -> tuple[bool, str]:
    if not expected:
        return False, "无期望答案"
    exp = compact_text(expected)
    if not exp:
        return False, "期望答案为空"
    answer_norm = (
        answer_compact
        .replace("##", "/")
        .replace("#", "/")
    )
    exp_norm = (
        exp
        .replace("##", "/")
        .replace("#", "/")
        .replace("\uff0f", "/")
    )
    search_exp = re.sub(r"^[(（][0-9]+[)）]", "", exp_norm) or exp_norm
    qn = str(qn)
    sub = str(sub_qno) if sub_qno else None

    first_20 = search_exp[:20]
    patterns = [
        f"{qn}.{exp_norm}",
        f"{qn}.{first_20}",
        f"{qn}{exp_norm}",
        f"{qn}{first_20}",
        f"{qn}\u3010\u7b54\u6848\u3011{exp_norm}",
        f"{qn}\u3010\u7b54\u6848\u3011{first_20}",
        f"{qn} {exp_norm}",
        f"{qn} {first_20}",
    ]
    if sub:
        patterns.extend(
            [
                f"{qn}.{sub}.{exp_norm}",
                f"{qn}.{sub}.{first_20}",
                f"{sub}.{exp_norm}",
                f"{sub}.{first_20}",
                f"{qn}{sub}{exp_norm}",
            ]
        )
    for pattern in patterns:
        if pattern in answer_norm:
            return True, f"答案区模式命中: {pattern[:60]}"

    # 长答案：定位题号标记后检查下一段内容。
    qn_pos = -1
    for marker in (f"{qn}.", f"{qn}\u3010\u7b54\u6848\u3011", f"{qn} "):
        qn_pos = answer_norm.find(marker)
        if qn_pos >= 0:
            break
    if qn_pos >= 0:
        window = answer_norm[qn_pos : qn_pos + 900]
        if first_20 in window or search_exp[:12] in window:
            return True, f"题号附近窗口命中: {first_20}"

    # HTML 表格格式回退：答案无题号前缀（如 "B" 而非 "1.B"）。
    # 化学/政治/物理/生物的答案区是 HTML 表格，答案文本直接出现在表格单元格中。
    # 对于选择题（短答案 ≤5 字符），答案文本在答案区中出现即可视为命中。
    # 对于长答案（解答题），需要更严格的匹配。
    if len(exp_norm) <= 5:
        # 短答案（选择题 A/B/C/D 等）：答案文本在答案区中出现即命中
        if exp_norm in answer_norm:
            return True, f"答案区短答案直接命中: {exp_norm}"
    else:
        # 长答案：答案文本在答案区中出现即命中（答案区已从"参考答案"截取，误报率低）
        if first_20 in answer_norm:
            return True, f"答案区长答案片段命中: {first_20}"

    return False, f"答案区未找到: {first_20}"


# ---------- 数据结构 ----------


@dataclass
class Section:
    section_id: str
    qns: list[str]
    start_text: str = ""
    shared_text: str = ""
    has_shared_material: bool = False
    norm_start: int = -1
    norm_end: int = -1
    norm_text: str = ""
    # L1 行号区间（2026-08-25：选项归属校验用）。
    # id_min = 本 section 成员题 shared/stem/options 行号的最小 (page, line)；
    # id_max = 下一个 section 的 id_min（无下一个时为 None，即无上界）。
    id_min: tuple | None = None
    id_max: tuple | None = None


def _lid_key(lid: str | None) -> tuple[int, int] | None:
    """L1 行号 "P1L003" / "N1L003" → (page, line) 元组，可排序。"""
    m = re.match(r"^[PN](\d+)L(\d+)$", lid or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def _lid_within(lid: str | None, section: Section) -> bool:
    """判断行号是否落在 section 的 L1 行号区间 [id_min, id_max) 内。"""
    key = _lid_key(lid)
    if key is None or section.id_min is None:
        return True  # 行号无法解析或 section 无行号区间时不判失败
    if key < section.id_min:
        return False
    if section.id_max is not None and key >= section.id_max:
        return False
    return True


@dataclass
class QuestionResult:
    question_number: str
    subject: str
    is_composite: bool
    db_status: str = ""
    in_db: bool = True
    stem_hit: bool = False
    stem_location_hit: bool = False
    material_hit: bool = False
    options_hit: bool = False
    answer_hit: bool = False
    answer_status: str = UNVERIFIABLE
    answer_evidence_kind: str = ""
    answer_evidence_source: str = ""
    answer_unverifiable_reason: str = ""
    strict_pass: bool = False
    failure_stage: str = ""
    details: list[str] = field(default_factory=list)


@dataclass
class SubjectReport:
    subject: str
    doc_id: str
    filename: str
    l2_count: int = 0
    pipeline_count: int = 0
    db_count: int = 0
    results: list[QuestionResult] = field(default_factory=list)
    filtered: list[dict] = field(default_factory=list)
    merged: list[dict] = field(default_factory=list)
    missing_from_db: list[dict] = field(default_factory=list)
    ingest_summary: dict = field(default_factory=dict)

    @property
    def strict_pass_count(self) -> int:
        return sum(1 for r in self.results if r.strict_pass)

    @property
    def stem_hits(self) -> int:
        return sum(1 for r in self.results if r.stem_hit)

    @property
    def location_hits(self) -> int:
        return sum(1 for r in self.results if r.stem_location_hit)

    @property
    def material_hits(self) -> int:
        return sum(1 for r in self.results if r.material_hit)

    @property
    def options_hits(self) -> int:
        return sum(1 for r in self.results if r.options_hit)

    @property
    def answer_hits(self) -> int:
        return sum(1 for r in self.results if r.answer_hit)

    @property
    def answer_unverifiable_count(self) -> int:
        return sum(
            1
            for r in self.results
            if r.answer_status == UNVERIFIABLE
        )

    @property
    def answer_unverifiable_reasons(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.results:
            if r.answer_status == UNVERIFIABLE:
                reason = r.answer_unverifiable_reason or "unknown"
                counts[reason] = counts.get(reason, 0) + 1
        return counts

    @property
    def answer_mismatched_count(self) -> int:
        return sum(
            1
            for r in self.results
            if r.answer_status not in (MATCHED, UNVERIFIABLE)
        )


# ---------- 数据装载 ----------


def load_json_value(value):
    parsed = parse_json(value)
    return parsed if isinstance(parsed, dict) else {}


def _find_pdf_path(subject: str, filename: str) -> Path | None:
    pdf_root = PROJECT_ROOT / "test" / "pdf"
    if not pdf_root.exists():
        return None
    target = unquote(filename or "").replace(".pdf", "")
    normalized_target = re.sub(r"\s+", "", target)
    for path in pdf_root.glob("*.pdf"):
        normalized_stem = re.sub(r"\s+", "", path.stem)
        if normalized_target and normalized_target == normalized_stem:
            return path
    for path in pdf_root.glob("*.pdf"):
        if subject and subject in path.name:
            return path
    return None


def _extract_pdf_raw_text(subject: str, filename: str) -> str:
    path = _find_pdf_path(subject, filename)
    if path is None:
        return ""
    try:
        import fitz
        with fitz.open(path) as pdf:
            return "\n".join(page.get_text("text") for page in pdf)
    except Exception:
        return ""


async def load_document(conn, subject: str) -> SubjectReport | None:
    doc = await conn.fetchrow(
        """
        SELECT id, filename, subject, native_markdown, ocr_markdown, llm_annotated_markdown
        FROM documents
        WHERE subject = $1 AND processing_status = 'completed'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        subject,
    )
    if not doc:
        return None

    doc_id = str(doc["id"])
    task = await conn.fetchrow(
        """
        SELECT result_json
        FROM background_tasks
        WHERE payload_json->>'document_id' = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        doc_id,
    )
    task_result = load_json_value(task["result_json"] if task else None)

    l2_raw = doc["llm_annotated_markdown"] or "{}"
    try:
        l2_data = json.loads(l2_raw)
    except Exception:
        l2_data = {}
    l2_questions = to_list(l2_data.get("questions"))
    l2_by_qn = {str(q.get("question_number")): q for q in l2_questions if isinstance(q, dict)}

    db_rows = await conn.fetch(
        """
        SELECT qi.source_question_number, q.stem, q.options, q.answer,
               q.is_composite, q.sub_questions, q.status, q.confidence, q.review_reason
        FROM questions q
        JOIN question_instances qi ON qi.question_id = q.id
        WHERE qi.document_id = $1
        ORDER BY qi.source_question_number::int
        """,
        doc_id,
    )

    pipeline_questions = [
        q for q in to_list(task_result.get("questions")) if isinstance(q, dict)
    ]
    discarded_questions = [
        q for q in to_list(task_result.get("discarded_questions")) if isinstance(q, dict)
    ]
    pipeline_by_qn = {str(q.get("question_number")): q for q in pipeline_questions}
    discarded_by_qn = {str(q.get("question_number")): q for q in discarded_questions}

    line_map: dict[str, str] = {}
    for q in pipeline_questions:
        stem_ids = to_list(q.get("stem_line_ids"))
        stem_lines = (q.get("stem") or "").splitlines()
        if len(stem_ids) == len(stem_lines):
            for lid, text in zip(stem_ids, stem_lines):
                line_map[str(lid)] = str(text)
        shared_ids = to_list(q.get("shared_material_line_ids"))
        shared_lines = (q.get("shared_material") or "").splitlines()
        if len(shared_ids) == len(shared_lines):
            for lid, text in zip(shared_ids, shared_lines):
                line_map[str(lid)] = str(text)

    source = doc["ocr_markdown"] or doc["native_markdown"] or ""
    source_compact = compact_text(source)
    sections = build_sections(l2_questions, line_map, pipeline_by_qn)
    resolve_sections(sections, source_compact, l2_by_qn, line_map)
    headers_in_source = section_headers(source)

    report = SubjectReport(
        subject=subject,
        doc_id=doc_id,
        filename=doc["filename"] or "",
        l2_count=len(l2_questions),
        pipeline_count=len(pipeline_questions),
        db_count=len(db_rows),
        ingest_summary=task_result.get("ingest_summary") or {},
    )

    db_by_qn = {str(r["source_question_number"]): dict(r) for r in db_rows}
    db_qns = set(db_by_qn.keys())
    pipeline_qns = set(pipeline_by_qn.keys())
    raw_text = _extract_pdf_raw_text(subject, doc["filename"] or "")
    native_text = doc["native_markdown"] or ""
    ocr_text = doc["ocr_markdown"] or ""
    answer_verifications = verify_document_answers(
        [dict(r) for r in db_rows],
        raw_text,
        native_text,
        ocr_text,
    )

    all_qns = sorted(
        pipeline_qns | db_qns,
        key=qn_num,
    )

    for qn in all_qns:
        db_row = db_by_qn.get(qn)
        l2_q = l2_by_qn.get(qn) or {}
        pipeline_q = pipeline_by_qn.get(qn) or {}
        section = find_section_for_qn(sections, qn)
        result = verify_question(
            qn=qn,
            db_row=db_row,
            l2_q=l2_q,
            pipeline_q=pipeline_q,
            section=section,
            sections=sections,
            source=source,
            source_compact=source_compact,
            headers_in_source=headers_in_source,
            answer_verification=answer_verifications.get(qn),
        )
        report.results.append(result)

    # 被过滤/缺口追踪
    for q in discarded_questions:
        qn = str(q.get("question_number"))
        report.filtered.append(
            {
                "question_number": qn,
                "issues": q.get("issues") or [],
                "discard_details": q.get("discard_details") or [],
                "discard_categories": q.get("discard_categories") or [],
                "confidence": q.get("confidence"),
                "answer": q.get("answer"),
                "in_db": qn in db_qns,
            }
        )

    for qn in sorted(pipeline_qns - db_qns, key=qn_num):
        q = pipeline_by_qn.get(qn) or {}
        report.missing_from_db.append(
            {
                "question_number": qn,
                "issues": q.get("issues") or [],
                "stage": "ingestion_missing",
            }
        )

    for qn in sorted(set(l2_by_qn.keys()) - db_qns, key=qn_num):
        section = find_section_for_qn(sections, qn)
        if section and section.qns:
            first_qn = section.qns[0]
            if first_qn in db_qns and first_qn != qn:
                report.merged.append(
                    {
                        "question_number": qn,
                        "merged_into": first_qn,
                        "section_id": section.section_id,
                    }
                )
                continue
        report.filtered.append(
            {
                "question_number": qn,
                "issues": ["L2 存在但未单独入库"],
                "discard_details": [],
                "discard_categories": [],
                "confidence": None,
                "answer": None,
                "in_db": False,
            }
        )

    return report


def build_sections(
    l2_questions: list,
    line_map: dict[str, str],
    pipeline_by_qn: dict[str, dict],
) -> list[Section]:
    groups: dict[str, list[dict]] = {}
    for q in l2_questions:
        qn = str(q.get("question_number"))
        sid = q.get("section_id") or f"__q_{qn}"
        groups.setdefault(sid, []).append(q)

    sections: list[Section] = []
    for sid, questions in groups.items():
        questions.sort(key=lambda q: qn_num(q.get("question_number")))
        qns = [str(q.get("question_number")) for q in questions]
        shared_lines: list[str] = []
        for q in questions:
            for lid in to_list(q.get("shared_material_line_ids")):
                text = line_map.get(str(lid))
                if text:
                    shared_lines.append(str(text))

        has_shared = bool(shared_lines)
        start_text = ""
        if shared_lines:
            start_text = _choose_section_start(shared_lines)
        else:
            first = questions[0]
            start_text = first.get("stem_start_marker") or ""
            if not start_text:
                for lid in to_list(first.get("stem_line_ids")):
                    if line_map.get(str(lid)):
                        start_text = str(line_map.get(str(lid)))
                        break

        first_qn = qns[0]
        pipeline_q = pipeline_by_qn.get(first_qn) or {}
        shared_text = str(pipeline_q.get("shared_material") or "")
        if not shared_text and shared_lines:
            shared_text = "\n".join(shared_lines)

        # section 的 L1 行号区间：成员题 shared/stem/options 行号的最小值
        all_ids: list[str] = []
        for q in questions:
            all_ids.extend(str(lid) for lid in to_list(q.get("shared_material_line_ids")))
            all_ids.extend(str(lid) for lid in to_list(q.get("stem_line_ids")))
            for lids in (q.get("options_line_ids") or {}).values():
                all_ids.extend(str(lid) for lid in to_list(lids))
        id_keys = [k for k in (_lid_key(lid) for lid in all_ids) if k is not None]

        sections.append(
            Section(
                section_id=sid,
                qns=qns,
                start_text=start_text,
                shared_text=shared_text,
                has_shared_material=has_shared,
                id_min=min(id_keys) if id_keys else None,
            )
        )

    # 按文档顺序（行号区间）排序，无行号时按题号排序兜底
    sections.sort(
        key=lambda s: (s.id_min is None, s.id_min if s.id_min is not None else (0, 0), qn_num(s.qns[0]) if s.qns else 9999)
    )
    # 每个 section 的上界 = 下一个 section 的起点
    for index, section in enumerate(sections):
        if index + 1 < len(sections):
            section.id_max = sections[index + 1].id_min
    return sections


def _choose_section_start(shared_lines: list[str]) -> str:
    """选 section 起点：优先取最早一段可读材料，避免单字母 OCR 行。"""
    for line in shared_lines:
        compact_line = compact_text(line)
        if len(compact_line) >= 8 and compact_line not in {"A", "B", "C", "D"}:
            return line
    return max(shared_lines, key=lambda x: len(compact_text(x)))


def resolve_sections(
    sections: list[Section],
    source_compact: str,
    l2_by_qn: dict[str, dict],
    line_map: dict[str, str],
) -> None:
    for index, section in enumerate(sections):
        prev_end = sections[index - 1].norm_end if index > 0 else 0
        pos = find_marker(source_compact, section.start_text, max(0, prev_end - 1))
        if pos < 0:
            for qn in section.qns:
                q = l2_by_qn.get(qn) or {}
                marker = q.get("stem_start_marker") or ""
                if not marker:
                    for lid in to_list(q.get("stem_line_ids")):
                        if line_map.get(str(lid)):
                            marker = str(line_map.get(str(lid)))
                            break
                pos = find_marker(source_compact, marker, max(0, prev_end - 1))
                if pos >= 0:
                    break
        section.norm_start = pos if pos >= 0 else prev_end

        if index + 1 < len(sections):
            next_start = find_marker(
                source_compact,
                sections[index + 1].start_text,
                section.norm_start + 1,
            )
            if next_start > section.norm_start:
                section.norm_end = next_start
            else:
                last_qn = section.qns[-1]
                end_marker = (l2_by_qn.get(last_qn) or {}).get("stem_end_marker")
                end_pos = find_marker(source_compact, end_marker, section.norm_start + 1)
                section.norm_end = end_pos if end_pos > section.norm_start else len(source_compact)
        else:
            section.norm_end = len(source_compact)

        section.norm_text = source_compact[section.norm_start : section.norm_end]


def find_section_for_qn(sections: list[Section], qn: str) -> Section | None:
    for section in sections:
        if qn in section.qns:
            return section
    return None


# ---------- 验收逻辑 ----------


def verify_question(
    *,
    qn: str,
    db_row: dict | None,
    l2_q: dict,
    pipeline_q: dict,
    section: Section | None,
    sections: list[Section],
    source: str,
    source_compact: str,
    headers_in_source: list[str],
    answer_verification: AnswerVerification | None = None,
) -> QuestionResult:
    db_stem = (db_row or {}).get("stem") or ""
    db_options = (db_row or {}).get("options")
    db_answer = (db_row or {}).get("answer") or ""
    is_composite = bool((db_row or {}).get("is_composite") or l2_q.get("is_composite"))
    db_status = (db_row or {}).get("status") or ""

    result = QuestionResult(
        question_number=qn,
        subject="",
        is_composite=is_composite,
        db_status=db_status,
        in_db=db_row is not None,
    )

    verify_stem(result, db_stem, l2_q, pipeline_q, section, sections, source_compact, headers_in_source)
    verify_material(result, db_stem, section, pipeline_q, source_compact)
    verify_options(result, db_options, pipeline_q, section, l2_q=l2_q)
    if answer_verification is not None:
        result.answer_status = answer_verification.status
        result.answer_evidence_kind = answer_verification.evidence_kind
        result.answer_evidence_source = answer_verification.evidence_source
        result.answer_hit = answer_verification.status == MATCHED
        if not result.answer_hit:
            if answer_verification.reason:
                result.answer_unverifiable_reason = answer_verification.reason
                result.details.append(f"答案验收: {answer_verification.reason}")
            else:
                result.details.append(
                    f"答案验收: mismatched (DB={db_answer!r}, expected={answer_verification.expected!r})"
                )
    else:
        result.answer_status = UNVERIFIABLE
        result.answer_unverifiable_reason = (
            "missing_db_question" if db_row is None else "missing_answer_verification"
        )
        result.details.append(f"答案验收: {result.answer_unverifiable_reason}")

    result.strict_pass = bool(
        result.stem_hit
        and result.stem_location_hit
        and result.material_hit
        and result.options_hit
        and result.answer_hit
    )
    if not result.strict_pass:
        if not result.in_db:
            result.failure_stage = "ingestion"
        elif not result.stem_hit or not result.stem_location_hit or not result.material_hit or not result.options_hit:
            result.failure_stage = "content_slicer"
        elif not result.answer_hit:
            result.failure_stage = "answer_matcher"
    return result


def verify_stem(
    result: QuestionResult,
    db_stem: str,
    l2_q: dict,
    pipeline_q: dict,
    section: Section | None,
    sections: list[Section],
    source_compact: str,
    headers_in_source: list[str],
) -> None:
    db_compact = compact_text(db_stem)
    if not db_compact:
        result.details.append("stem 为空")
        return

    marker = l2_q.get("stem_start_marker") or ""
    if not marker:
        marker = str(pipeline_q.get("stem") or "")[:30]
    if not marker:
        marker = db_stem[:30]
    marker_compact = compact_text(marker)
    core_hit = bool(marker_compact and (
        marker_compact in db_compact or marker_compact[:12] in db_compact
    ))
    if not core_hit:
        result.details.append(f"题干起始标记未进入 DB stem: {marker_compact[:30]}")
        return
    result.stem_hit = True

    if not section:
        result.details.append("L2 无 section，无法校验位置")
        result.stem_location_hit = True
        return

    section_text = section.norm_text
    contained = bool(section_text and db_compact in section_text)
    coverage = line_coverage(db_stem, section_text) if section_text else 0.0
    in_section = bool(section_text and (contained or coverage >= 0.8))

    # 行号区间补充校验（比文本跨度可靠）：
    # - Q14-16 诗歌阅读：section 文本跨度从诗歌正文起，标题 `病橘[1]`/作者 `杜甫`
    #   行落在跨度外（行覆盖 67%），但行号在 section 区间内；
    # - Q22 语言基础运用：源文本题干行在材料之前（`…22.阅读文字…①《乡土中国》…`），
    #   材料优先合并后文本跨度不含题干行（行覆盖 50%），行号区间含之。
    # 两者 DB 数据均正确，纯文本包含检查产生误报（2026-08-25 语文位置 4 题）。
    # 越界/串题仍由下方 bleed 检查独立拦截（能抓到真实串题，如 Q17）。
    line_span_ok = False
    if section.id_min is not None and not in_section:
        q_ids: list[str] = []
        q_ids.extend(str(lid) for lid in to_list(pipeline_q.get("stem_line_ids")))
        q_ids.extend(str(lid) for lid in to_list(pipeline_q.get("shared_material_line_ids")))
        if q_ids:
            # _lid_within 对无法解析的行号采取 fail-open，不会误判失败
            line_span_ok = all(_lid_within(lid, section) for lid in q_ids)
    if line_span_ok:
        in_section = True

    # 逐题回退 section（__q_*：LLM 未给 section_id 的独立题，section 即题目
    # 本身）：section 文本范围解析常为空，in_section 包含检查会产生 0% 覆盖
    # 误报（2026-08-25 历史 Q38-43 stem 内容正确仍报位置 N）。此类题的位置
    # 校验退化为"不判失败"；越界/串题检查仍然保留（能抓到真实串题）。
    fallback_section = (
        not section.has_shared_material
        and str(section.section_id).startswith("__q_")
    )

    # 越界/串题：DB stem 里出现后续 section 的起始文本，或出现多个大题标题。
    bleed_headers: list[str] = []
    first_qn_marker_pos = find_marker(
        source_compact,
        l2_q.get("stem_start_marker") or section.start_text,
        0,
    )
    for header in headers_in_source:
        if compact_text(header) in db_compact:
            header_pos = source_compact.find(compact_text(header))
            if header_pos >= 0 and first_qn_marker_pos >= 0 and header_pos > first_qn_marker_pos:
                bleed_headers.append(header)

    # 用下一个 section 的 start_text 作为更可靠的越界标记。
    for later_sec in sections:
        if later_sec is section or not later_sec.qns:
            continue
        later_qn_num = qn_num(later_sec.qns[0])
        if later_qn_num > qn_num(section.qns[0]):
            if later_sec.start_text and compact_text(later_sec.start_text) in db_compact:
                bleed_headers.append(f"section:{later_sec.section_id}")

    bleed = bool(bleed_headers)
    if bleed:
        result.details.append(f"stem 越界/串题: {', '.join(sorted(set(bleed_headers))[:5])}")
    if not in_section and not fallback_section:
        result.details.append(f"stem 未完整落在 section {section.section_id} 内 (行覆盖 {coverage:.0%})")
    result.stem_location_hit = bool((in_section or fallback_section) and not bleed)


def verify_material(
    result: QuestionResult,
    db_stem: str,
    section: Section | None,
    pipeline_q: dict,
    source_compact: str,
) -> None:
    expected = ""
    if section and section.has_shared_material:
        expected = section.shared_text
    if not expected and pipeline_q.get("shared_material"):
        expected = str(pipeline_q["shared_material"])

    db_compact = compact_text(db_stem)
    if not expected:
        result.material_hit = True
        return
    coverage = chunk_coverage(expected, db_compact)
    source_coverage = chunk_coverage(expected, source_compact)
    result.material_hit = coverage >= 0.6
    if not result.material_hit:
        result.details.append(
            f"composite 材料未进入 DB stem (材料覆盖 {coverage:.0%}, 原文覆盖 {source_coverage:.0%})"
        )
    else:
        result.details.append(f"材料覆盖 {coverage:.0%}")


def verify_options(
    result: QuestionResult,
    db_options,
    pipeline_q: dict,
    section: Section | None,
    l2_q: dict | None = None,
) -> None:
    db_options_list = to_list(db_options)
    expected_options = to_list(pipeline_q.get("options"))

    if not expected_options:
        if db_options_list:
            result.options_hit = True
            result.details.append("无 L2/pipeline 选项期望，但 DB 有选项")
        else:
            result.options_hit = True
        return

    if not db_options_list:
        result.details.append(f"期望 {len(expected_options)} 个选项，DB options 为空")
        return

    expected_by_label = {
        str(opt.get("label", "")).upper(): compact_text(opt.get("text", ""))
        for opt in expected_options
        if isinstance(opt, dict)
    }
    db_by_label = {
        str(opt.get("label", "")).upper(): compact_text(opt.get("text", ""))
        for opt in db_options_list
        if isinstance(opt, dict)
    }

    section_text = section.norm_text if section else ""
    missing_in_db: list[str] = []
    for label, expected_text in expected_by_label.items():
        db_text = db_by_label.get(label, "")
        if not db_text or expected_text not in db_text and db_text not in expected_text:
            missing_in_db.append(label)
    if missing_in_db:
        result.details.append(f"DB 选项缺失: {','.join(missing_in_db)}")
        return

    wrong_location: list[str] = []
    # 归属校验优先用 L2 行号区间（2026-08-25）：
    # 综合题多子题选项会按 label 拼接成一段文本，拼接文本在 section 原文中
    # 不连续出现，纯文本包含判断会产生假阳性（英语 Q1/Q26/Q29/Q33 选项实际
    # 都在各自 section 内）。L2 options_line_ids 直接指向 L1 行号，精确判断。
    l2_opt_ids = (l2_q or {}).get("options_line_ids") or {}
    has_l2_option_ids = any(to_list(lids) for lids in l2_opt_ids.values())
    if has_l2_option_ids and section is not None and section.id_min is not None:
        for label in expected_by_label:
            lids = to_list(l2_opt_ids.get(label))
            if lids and not all(_lid_within(lid, section) for lid in lids):
                wrong_location.append(label)
        if wrong_location:
            result.details.append(f"选项行号越出当前 section: {','.join(wrong_location)}")
            return
    else:
        # 无 L2 行号或 section 无行号区间 → 文本包含判断兜底（单行选项/历史数据）
        for label, expected_text in expected_by_label.items():
            db_text = db_by_label.get(label, "")
            if section_text and compact_text(db_text) not in section_text:
                wrong_location.append(label)
        if wrong_location:
            result.details.append(f"选项未落在当前 section: {','.join(wrong_location)}")
            return

    extra_labels = sorted(set(db_by_label.keys()) - set(expected_by_label.keys()))
    if extra_labels:
        result.details.append(f"DB 含额外选项: {','.join(extra_labels)}")
    result.options_hit = True


def verify_answer(
    result: QuestionResult,
    db_answer: str,
    db_row: dict | None,
    l2_q: dict,
    pipeline_q: dict,
    source: str,
) -> None:
    answer_section = extract_answer_section(source)
    if not answer_section:
        result.details.append("未找到答案区")
        return
    answer_compact = compact_text(answer_section)
    qn = result.question_number

    db_sub_questions = to_list((db_row.get("sub_questions") if db_row else None) or [])
    pipeline_sub_questions = to_list((pipeline_q.get("sub_questions") or []))
    l2_sub_questions = to_list((l2_q.get("sub_questions") or []))
    all_subs = db_sub_questions or pipeline_sub_questions or l2_sub_questions

    expected_candidates: list[tuple[str | None, str]] = []
    if all_subs:
        for sub in all_subs:
            if isinstance(sub, dict) and sub.get("answer"):
                expected_candidates.append((str(sub.get("qno") or ""), str(sub["answer"])))
    if not expected_candidates:
        expected = db_answer or l2_q.get("answer") or pipeline_q.get("answer")
        if expected:
            expected_candidates.append((None, str(expected)))

    if not expected_candidates:
        result.details.append("无期望答案")
        return

    missing: list[str] = []
    hit_count = 0
    for sub_qno, answer in expected_candidates:
        found, detail = find_answer_evidence(qn, answer, answer_compact, sub_qno)
        if found:
            hit_count += 1
        else:
            missing.append(detail)
    result.answer_hit = hit_count == len(expected_candidates)
    if not result.answer_hit:
        result.details.append(f"答案未全部找到 ({hit_count}/{len(expected_candidates)}): {missing[:3]}")


# ---------- 输出 ----------


def print_report(report: SubjectReport) -> None:
    print(f"\n{'=' * 90}")
    print(f"  {report.subject} 验收报告")
    print(f"  文档: {report.filename}")
    print(f"  L2 标注 {report.l2_count} -> 管线 {report.pipeline_count} -> DB {report.db_count}")
    print(f"{'=' * 90}")
    print(
        f"{'题号':<5}{'类型':<6}{'状态':<10}{'stem':<6}{'位置':<6}{'材料':<6}"
        f"{'选项':<7}{'答案':<7}{'阶段':<12}"
    )
    print("-" * 90)
    for r in report.results:
        q_type = "综合" if r.is_composite else "独立"
        status = r.db_status or "缺库"
        stage = r.failure_stage or "-"
        answer_mark = "Y" if r.answer_hit else ("U" if r.answer_status == UNVERIFIABLE else "N")
        print(
            f"Q{r.question_number:<4}{q_type:<6}{status:<10}"
            f"{'Y' if r.stem_hit else 'N':<6}"
            f"{'Y' if r.stem_location_hit else 'N':<6}"
            f"{'Y' if r.material_hit else 'N':<6}"
            f"{'Y' if r.options_hit else 'N':<7}"
            f"{answer_mark:<7}"
            f"{stage:<12}"
        )

    total = len(report.results)
    if total:
        print(f"\n  严格通过: {report.strict_pass_count}/{total}")
        print(f"  stem 核心命中: {report.stem_hits}/{total}")
        print(f"  stem 位置正确: {report.location_hits}/{total}")
        print(f"  composite 材料: {report.material_hits}/{total}")
        print(f"  options 归属: {report.options_hits}/{total}")
        print(f"  answer 命中: {report.answer_hits}/{total}")
        unverifiable = report.answer_unverifiable_count
        if unverifiable:
            print(f"  answer 不可验证: {unverifiable}/{total}")
            for reason, count in sorted(
                report.answer_unverifiable_reasons.items(),
                key=lambda item: -item[1],
            ):
                print(f"    - {reason}: {count}")
        mismatched = report.answer_mismatched_count
        if mismatched:
            print(f"  answer 不匹配: {mismatched}/{total}")

    failures = [r for r in report.results if not r.strict_pass]
    if failures:
        print(f"\n  失败明细 ({len(failures)} 题):")
        for r in failures:
            print(f"    Q{r.question_number}: {r.failure_stage or '-'}")
            for detail in r.details:
                print(f"      - {detail}")

    if report.filtered:
        print(f"\n  被过滤/未入库 ({len(report.filtered)}):")
        for item in report.filtered:
            issues = " | ".join(item.get("issues") or item.get("discard_details") or [])
            marker = " (DB存在)" if item.get("in_db") else ""
            print(f"    Q{item.get('question_number')}{marker}: {issues or '无原因'}")

    if report.merged:
        print(f"\n  L2 子题合并 ({len(report.merged)}):")
        for item in report.merged:
            print(
                f"    Q{item['question_number']} -> Q{item['merged_into']} "
                f"[{item.get('section_id')}]"
            )

    if report.missing_from_db:
        print(f"\n  管线存在但 DB 缺失 ({len(report.missing_from_db)}):")
        for item in report.missing_from_db:
            print(f"    Q{item['question_number']}: {item.get('issues') or 'ingestion_missing'}")


def print_summary(reports: list[SubjectReport]) -> None:
    print(f"\n{'=' * 90}")
    print("  总汇总")
    print(f"{'=' * 90}")
    print(
        f"{'学科':<8}{'L2':<6}{'管线':<6}{'DB':<6}{'严格':<7}"
        f"{'stem':<6}{'位置':<6}{'材料':<6}{'选项':<7}{'答案':<7}{'答U':<7}{'答M':<7}"
    )
    for report in reports:
        total = len(report.results)
        print(
            f"{report.subject:<8}{report.l2_count:<6}{report.pipeline_count:<6}"
            f"{report.db_count:<6}{report.strict_pass_count:<7}"
            f"{report.stem_hits:<6}{report.location_hits:<6}{report.material_hits:<6}"
            f"{report.options_hits:<7}{report.answer_hits:<7}"
            f"{report.answer_unverifiable_count:<7}{report.answer_mismatched_count:<7}"
        )
    total_q = sum(len(r.results) for r in reports)
    if total_q:
        strict = sum(r.strict_pass_count for r in reports)
        stem = sum(r.stem_hits for r in reports)
        loc = sum(r.location_hits for r in reports)
        mat = sum(r.material_hits for r in reports)
        opt = sum(r.options_hits for r in reports)
        ans = sum(r.answer_hits for r in reports)
        ans_u = sum(r.answer_unverifiable_count for r in reports)
        ans_m = sum(r.answer_mismatched_count for r in reports)
        print("-" * 90)
        print(
            f"{'合计':<8}{sum(r.l2_count for r in reports):<6}"
            f"{sum(r.pipeline_count for r in reports):<6}{sum(r.db_count for r in reports):<6}"
            f"{strict:<7}{stem:<6}{loc:<6}{mat:<6}{opt:<7}{ans:<7}{ans_u:<7}{ans_m:<7}"
        )
        print(f"  严格通过率: {strict}/{total_q} ({strict/total_q*100:.0f}%)")


async def main() -> None:
    parser = argparse.ArgumentParser(description="e2e 语义验收报告 v2")
    parser.add_argument("--subject", type=str, help="指定学科")
    parser.add_argument("--all", action="store_true", help="验证全部已完成文档")
    parser.add_argument("--output", type=str, default="", help="文本报告输出路径")
    args = parser.parse_args()

    conn = await _connect()
    try:
        if args.all:
            rows = await conn.fetch(
                "SELECT DISTINCT subject FROM documents WHERE processing_status='completed'"
            )
            subjects = [str(r["subject"]) for r in rows if r["subject"]]
        elif args.subject:
            subjects = [args.subject]
        else:
            subjects = ["\u8bed\u6587", "\u82f1\u8bed"]

        print("=== e2e 语义验收报告 v2 ===")
        print(f"验证学科: {', '.join(subjects)}")
        reports: list[SubjectReport] = []
        for subject in subjects:
            report = await load_document(conn, subject)
            if report:
                print_report(report)
                reports.append(report)
        if reports:
            print_summary(reports)

        if args.output:
            out_path = Path(args.output)
            if not out_path.is_absolute():
                out_path = PROJECT_ROOT / out_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(_capture_print(reports), encoding="utf-8")
            print(f"\n报告已写入: {out_path}")
    finally:
        await conn.close()


async def _connect():
    import asyncpg
    return await asyncpg.connect(DSN)


def _capture_print(reports: list[SubjectReport]) -> str:
    import io as _io
    buffer = _io.StringIO()
    old = sys.stdout
    sys.stdout = buffer
    try:
        for report in reports:
            print_report(report)
        print_summary(reports)
    finally:
        sys.stdout = old
    return buffer.getvalue()


if __name__ == "__main__":
    asyncio.run(main())
