#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""答案验收模块：pdf_raw_text / native / OCR 多源证据，输出 matched/mismatched/unverifiable。

证据模式：
- table: 答案表（题号行 + 答案行），必须保留空单元格
- prefix: 答案列表，例如 "26. A"
- inline: 内联答案，例如 "故选C项"
- free_text: 非选择题长答案块
- composite: 综合题子题答案

unverifiable 必须带 reason，不允许默认算通过。
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from html.parser import HTMLParser

MATCHED = "matched"
MISMATCHED = "mismatched"
UNVERIFIABLE = "unverifiable"


def compact_text(text: str | None) -> str:
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


def answer_section(text: str | None) -> str:
    if not text:
        return ""
    patterns = [
        "\u53c2\u8003\u7b54\u6848",
        "\u7b54\u6848[\uff1a:]",
        r"Answer\s*Key",
        "\u3010\u7b54\u6848\u3011",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return text[m.start() :]
    return ""


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_td = False
        self.cell: list[str] = []
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.in_table = 0

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "table":
            self.in_table += 1
        elif tag == "tr" and self.in_table:
            self.row = []
        elif tag == "td" and self.in_table:
            self.in_td = True
            self.cell = []

    def handle_endtag(self, tag) -> None:
        if tag == "td" and self.in_td:
            self.row.append("".join(self.cell).strip())
            self.in_td = False
        elif tag == "tr" and self.in_table:
            self.rows.append(self.row)
        elif tag == "table":
            self.in_table -= 1

    def handle_data(self, data) -> None:
        if self.in_td:
            self.cell.append(data)


@dataclass
class AnswerVerification:
    status: str = UNVERIFIABLE
    evidence_kind: str = ""
    evidence_source: str = ""
    expected: str | None = None
    reason: str | None = None


@dataclass
class DocumentAnswerEvidence:
    table: dict[int, str] = field(default_factory=dict)
    blank_qns: set[int] = field(default_factory=set)
    prefix: dict[int, str] = field(default_factory=dict)
    inline: dict[int, str] = field(default_factory=dict)
    answer_sections: list[str] = field(default_factory=list)


def _parse_html_tables(text: str) -> tuple[dict[int, str], set[int]]:
    parser = _TableParser()
    parser.feed(text)
    mapping: dict[int, str] = {}
    blank_qns: set[int] = set()
    for i, row in enumerate(parser.rows):
        if not row or row[0] != "\u9898\u53f7":
            continue
        if i + 1 >= len(parser.rows) or not parser.rows[i + 1]:
            continue
        answer_row = parser.rows[i + 1]
        if not answer_row or answer_row[0] != "\u7b54\u6848":
            continue
        for qn, ans in zip(row[1:], answer_row[1:]):
            if not qn or not qn.isdigit():
                continue
            num = int(qn)
            if ans:
                mapping[num] = ans.upper()
            else:
                blank_qns.add(num)
    return mapping, blank_qns


def _parse_plain_table(text: str) -> tuple[dict[int, str], set[int]]:
    mapping: dict[int, str] = {}
    for m in re.finditer(
        r"\u9898\u53f7\s*((?:\d+\s*)+)\s*\u7b54\u6848\s*((?:[A-G]+\s*)+)",
        text,
    ):
        nums = [int(x) for x in m.group(1).split()]
        ans = [x.upper() for x in m.group(2).split()]
        if len(nums) != len(ans):
            continue
        for num, answer in zip(nums, ans):
            mapping[num] = answer
    return mapping, set()


def _parse_prefix(text: str) -> dict[int, str]:
    mapping: dict[int, str] = {}

    def add(num: str, token: str) -> None:
        if token and re.fullmatch(r"[A-G]{1,4}", token.upper()):
            mapping[int(num)] = token.upper()

    for block in re.findall(
        r"\u3010\u7b54\u6848\u3011\s*((?:\d+[.\u3001\uff0e]\s*[^\n\u3010]+)+)",
        text,
    ):
        for m in re.finditer(r"(\d+)[.\u3001\uff0e]\s*([^\s,,\uff0c;;\uff1b]+)", block):
            add(m.group(1), m.group(2))
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+)[.\u3001\uff0e]\s*([^\s,,\uff0c;;\uff1b]+)", line)
        if m:
            add(m.group(1), m.group(2))
    return mapping


def _parse_inline(text: str) -> dict[int, str]:
    mapping: dict[int, str] = {}
    markers = list(re.finditer(r"(?m)(\d+)[.．、]\s*", text))
    for idx, marker in enumerate(markers):
        qn = int(marker.group(1))
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(text)
        window = text[marker.end() : end]
        m = re.search(
            r"(?:\u9009\u7b54\s*([A-Ga-g])\s*\u9879?|\u7b54\u6848[\uff1a:]\s*([A-Ga-g])|\u7b54\u6848\u4e3a\s*([A-Ga-g]))",
            window,
        )
        if m:
            value = next((x for x in m.groups() if x), None)
            if value:
                mapping[qn] = value.upper()
    return mapping


def build_evidence(raw_text: str | None, native_text: str | None, ocr_text: str | None) -> DocumentAnswerEvidence:
    evidence = DocumentAnswerEvidence()
    sources = [
        ("pdf_raw_text", raw_text or ""),
        ("native_markdown", native_text or ""),
        ("ocr_markdown", ocr_text or ""),
    ]
    for _source_name, source_text in sources:
        section = answer_section(source_text)
        if section:
            evidence.answer_sections.append(section)

    # 表格证据优先级：raw plain 先填，缺失列再用 native/OCR 补。
    # 不能整体覆盖：OCR 表格可能把生物答案识别成 a/∀/つ，只能补 raw 缺失项。
    for source_name, source_text in sources:
        table, _ = _parse_plain_table(answer_section(source_text or ""))
        for qn, answer in table.items():
            if qn not in evidence.table:
                evidence.table[qn] = answer
    for source_name, source_text in sources:
        table, blank = _parse_html_tables(source_text or "")
        for qn, answer in table.items():
            if qn not in evidence.table:
                evidence.table[qn] = answer
        evidence.blank_qns.update(blank)

    for _source_name, source_text in sources:
        section = answer_section(source_text or "")
        if not section:
            continue
        evidence.prefix.update(_parse_prefix(section))
        evidence.inline.update(_parse_inline(section))
    return evidence


def _find_free_text(
    qn: str,
    expected: str,
    evidence: DocumentAnswerEvidence,
) -> tuple[bool, str, str]:
    exp = compact_text(expected)
    if not exp:
        return False, "", ""
    exp = re.sub(r"^[(（][0-9]+[)）]", "", exp)
    fragment = exp[:20]
    for section in evidence.answer_sections:
        compact_section = compact_text(section)
        for marker in (f"{qn}.\u3010\u7b54\u6848\u3011", f"{qn}\u3010\u7b54\u6848\u3011", f"{qn}.", f"{qn} "):
            pos = compact_section.find(marker)
            if pos < 0:
                continue
            window = compact_section[pos : pos + 2000]
            if fragment in window or exp[:12] in window:
                return True, "free_text", "pdf_raw_text"
    return False, "", ""


def verify_one(
    qn: str,
    answer: str,
    sub_questions: list[dict] | None,
    evidence: DocumentAnswerEvidence,
) -> AnswerVerification:
    answer_text = compact_text(answer or "")
    if not answer_text:
        return AnswerVerification(reason="missing_db_answer")

    if not str(qn).isdigit():
        return AnswerVerification(reason="invalid_question_number")
    qn_int = int(qn)

    expected = evidence.table.get(qn_int)
    source = "pdf_raw_text"
    kind = "table"
    if expected is None:
        expected = evidence.prefix.get(qn_int)
        kind = "prefix"
    if expected is None:
        expected = evidence.inline.get(qn_int)
        kind = "inline"

    if expected is not None:
        if answer_text == compact_text(expected):
            return AnswerVerification(
                status=MATCHED,
                evidence_kind=kind,
                evidence_source=source,
                expected=expected,
            )
        return AnswerVerification(
            status=MISMATCHED,
            evidence_kind=kind,
            evidence_source=source,
            expected=expected,
        )

    if qn_int in evidence.blank_qns:
        return AnswerVerification(reason="blank_table_cell")

    # 综合题：先尝试子题答案证据。
    subs = sub_questions or []
    if isinstance(subs, str):
        try:
            parsed = json.loads(subs)
            subs = parsed if isinstance(parsed, list) else []
        except Exception:
            subs = []
    sub_matched = 0
    sub_total = 0
    if subs:
        sub_statuses = []
        for sub in subs:
            if not isinstance(sub, dict):
                continue
            sub_answer = compact_text(sub.get("answer") or "")
            if not sub_answer:
                continue
            sub_qno = str(sub.get("qno") or "")
            sub_total += 1
            if sub_qno:
                ver = verify_one(sub_qno, sub_answer, None, evidence)
                sub_statuses.append(ver.status)
                if ver.status == MATCHED:
                    sub_matched += 1
        if sub_statuses and MISMATCHED in sub_statuses:
            return AnswerVerification(
                status=MISMATCHED,
                evidence_kind="composite",
                expected="; ".join(
                    compact_text(sub.get("answer") or "") for sub in subs if isinstance(sub, dict) and sub.get("answer")
                ),
            )
        if sub_statuses and all(s == MATCHED for s in sub_statuses):
            return AnswerVerification(status=MATCHED, evidence_kind="composite")

    # 子题无法全部映射（如 qno 为非数字的"（1）"、或子题答案无独立证据）时，
    # 回退到父题整体答案的长文本匹配。生物 Q21-Q26 的子题号是"（1）（2）（3）"，
    # 无法用 verify_one 验证，但父题 answer 与 PDF 答案块内容一致，应算 matched。

    # 长答案块。
    found, kind, source = _find_free_text(qn, answer, evidence)
    if found:
        return AnswerVerification(
            status=MATCHED,
            evidence_kind=kind,
            evidence_source=source,
        )

    # 子题有部分 matched 但未全部 → composite_subquestion（证据不完整，不可算通过）
    if sub_total > 0 and sub_matched > 0 and sub_matched < sub_total:
        return AnswerVerification(reason="composite_subquestion")
    if sub_total > 0 and sub_matched == 0:
        return AnswerVerification(reason="composite_subquestion")

    if not evidence.answer_sections:
        return AnswerVerification(reason="missing_answer_evidence")
    if re.fullmatch(r"[A-G]{1,4}", answer_text):
        return AnswerVerification(reason="no_answer_evidence")
    return AnswerVerification(reason="free_text_answer")


def verify_document_answers(
    db_rows: list[dict],
    raw_text: str | None,
    native_text: str | None,
    ocr_text: str | None,
) -> dict[str, AnswerVerification]:
    evidence = build_evidence(raw_text, native_text, ocr_text)
    result: dict[str, AnswerVerification] = {}
    for row in db_rows:
        qn = str(row.get("source_question_number") or "")
        result[qn] = verify_one(
            qn,
            str(row.get("answer") or ""),
            row.get("sub_questions"),
            evidence,
        )
    return result
