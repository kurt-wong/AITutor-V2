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

# 长自由文本答案（作文/长解答题）的判定阈值（compact 后字符数）：
# 超过该长度且无法通过答案区标记自动验证 → 标记"需人工审核"
# （essay_manual_review），区别于短答案找不到证据（free_text_answer）。
# 2026-08-25：英语 Q46 作文答案 713 字符，仅能人工核对。
_ESSAY_MIN_LENGTH = 100


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


# LaTeX 圈号映射：DB 答案用 ①/②，OCR 答案区用 \textcircled{1}/\textcircled{i}。
_CIRCLED_MAP = {
    "1": "\u2460",
    "2": "\u2461",
    "3": "\u2462",
    "4": "\u2463",
    "5": "\u2464",
    "i": "\u2460",
    "ii": "\u2461",
    "iii": "\u2462",
    "iv": "\u2463",
    "v": "\u2464",
}


def _latex_frac(text: str) -> str:
    r"""\frac/\dfrac/\tfrac{a}{b} → a/b，迭代处理嵌套（内层先转）。"""
    pattern = re.compile(r"\\(?:dfrac|tfrac|frac)\{([^{}]*)\}\{([^{}]*)\}")
    for _ in range(4):
        new = pattern.sub(lambda m: f"{m.group(1)}/{m.group(2)}", text)
        if new == text:
            break
        text = new
    return text


def normalize_math(text: str | None) -> str:
    """LaTeX 数学答案 → 纯文本归一化（仅在含 `$` 或 `\\` 时生效，否则原样返回）。

    2026-08-25 数学二中卷 7 题答U 的三路表示差异：
    - 圈号：DB `②.` vs OCR `\\textcircled{2}.`
    - 公式定界符：`$...$` / `\\(...\\)` / `\\[...\\]`
    - 分数：`\\frac{4}{3}`（DB/OCR）vs PDF 竖排 `4\\n3`（提取即损坏，无法恢复）
    - 间距/括号命令：`\\quad` `\\,` `\\;` `\\left` `\\right` `\\big` 等
    - 常见符号：`\\pi`→π、`\\mid`→|、`\\{`→{、`\\in`→in（两侧同样处理）
    - 纯分组花括号 `{}` 移除
    归一化是确定性函数：两侧同规后做包含/相等比对。
    """
    if not text:
        return ""
    out = str(text)
    if "$" not in out and "\\" not in out:
        return out
    out = re.sub(r"\$\$", "", out).replace("$", "")
    out = out.replace(r"\(", "").replace(r"\)", "").replace(r"\[", "").replace(r"\]", "")
    out = re.sub(
        r"\\textcircled\s*\{([^{}]*)\}",
        lambda m: _CIRCLED_MAP.get(m.group(1).strip().lower(), m.group(0)),
        out,
    )
    out = _latex_frac(out)
    out = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt(\1)", out)
    out = re.sub(
        r"\\(?:left|right|big|Big|bigg|Bigg|bigl|bigr|Bigl|Bigr|quad|qquad|;|,|!| )",
        "",
        out,
    )
    out = out.replace(r"\{", "{").replace(r"\}", "}")
    out = out.replace(r"\mid", "|").replace(r"\pi", "\u03c0")
    # \text{...} 是文本/单位标记（如 \text{s}、\text{m/s}）→ 直接取内容。
    # 2026-08-25 物理 PPS 版 Q20：DB "4.5s"（纯文本）vs 答案区 "$4.5\text{s}$"
    # 原归一化 \text → "text" 得 "4.5texts" 与 "4.5s" 不匹配；此处 \text{s} → "s"。
    out = re.sub(r"\\text\s*\{([^{}]*)\}", r"\1", out)
    out = re.sub(r"\\([a-zA-Z]+)", r"\1", out)
    out = out.replace("{", "").replace("}", "")
    return out


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


def _row_cells(lines: list[str], row_idx: int, end_idx: int, marker: str) -> list[str]:
    """提取表格一行的单元格（"题号"/"答案"标记行）。

    同行空格分隔优先；否则后续每行一个单元格（空行 = 空单元格），
    遇到下一个"题号/答案"标记或大题标题行停止。
    """
    head = lines[row_idx].split(marker, 1)[1]
    head_cells = head.split()
    if head_cells:
        return head_cells
    cells: list[str] = []
    for ln in lines[row_idx + 1 : end_idx]:
        stripped = ln.strip()
        if re.match(r"^[一二三四五六七八九十]+、", stripped) or re.match(r"^(?:题号|答案)\b", stripped):
            break
        cells.append(stripped)
    return cells


def _parse_plain_table(text: str) -> tuple[dict[int, str], set[int]]:
    mapping: dict[int, str] = {}
    blank_qns: set[int] = set()
    for m in re.finditer(
        r"\u9898\u53f7\s*((?:\d+\s*)+)\s*\u7b54\u6848\s*((?:[A-G]+\s*)+)",
        text,
    ):
        nums = [int(x) for x in m.group(1).split()]
        ans = [x.upper() for x in m.group(2).split()]
        if len(nums) == len(ans):
            for num, answer in zip(nums, ans):
                mapping[num] = answer
            continue
        # 长度不等：答案行存在空单元格（如物理八十中单选题表 Q4/Q7 空白，
        # 其答案在文末"自主命制试题答案"单独给出），(?:[A-G]+\s*)+ 无法
        # 捕获占位导致整行被丢弃 → Q3/Q9/Q10 失去答案证据（2026-08-25）。
        # 改按原始行结构重排：竖排每格一行，空行 = 空单元格，位置对齐。
        raw = m.group(0)
        lines = raw.splitlines()
        ti = next((i for i, ln in enumerate(lines) if "\u9898\u53f7" in ln), -1)
        ai = next((i for i, ln in enumerate(lines) if "\u7b54\u6848" in ln), -1)
        if ti < 0 or ai < 0:
            continue
        num_cells = _row_cells(lines, ti, ai, "\u9898\u53f7")
        ans_cells = _row_cells(lines, ai, len(lines), "\u7b54\u6848")
        if len(num_cells) != len(ans_cells):
            continue  # 仍无法对齐，保守跳过（同旧行为）
        for num_cell, ans_cell in zip(num_cells, ans_cells):
            if not num_cell.isdigit():
                continue
            if ans_cell:
                mapping[int(num_cell)] = ans_cell.upper()
            else:
                blank_qns.add(int(num_cell))
    return mapping, blank_qns


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

    # 三源答案表收集（plain + html），冲突投票（2026-08-25 化学锚定消歧）。
    # 原逻辑"raw 先填、native/OCR 只补缺失"在二附中化学卷失效：pdf_raw
    # （PyMuPDF 文本层）答案表错位（Q2=D），native+OCR（视觉/表格引擎）
    # 一致为 B → 被 raw 占位压制 → 验证器误判 mismatch（化学 17 题）。
    # 改为：同题多源冲突时取多数一致（独立引擎一致优先）；全不同回退
    # pdf_raw（兼容基线行为）。
    per_source: dict[str, dict[int, str]] = {}
    blanks: set[int] = set()
    for name, source_text in sources:
        tbl, blank = _parse_plain_table(answer_section(source_text or ""))
        per_source[name] = dict(tbl)
        blanks |= blank
    for name, source_text in sources:
        tbl, blank = _parse_html_tables(source_text or "")
        for qn, answer in tbl.items():
            per_source[name].setdefault(qn, answer)
        blanks |= blank
    evidence.blank_qns.update(blanks)

    all_qns: set[int] = set()
    for tbl in per_source.values():
        all_qns.update(tbl.keys())
    for qn in all_qns:
        groups: dict[str, list[str]] = {}
        for tbl in per_source.values():
            value = tbl.get(qn)
            if value is None:
                continue
            groups.setdefault(compact_text(value), []).append(value)
        if not groups:
            continue
        if len(groups) == 1:
            evidence.table[qn] = next(iter(groups.values()))[0]
        else:
            best = max(groups.values(), key=len)
            if len(best) > 1:
                evidence.table[qn] = best[0]  # 多数一致优先
            elif qn in per_source["pdf_raw_text"]:
                evidence.table[qn] = per_source["pdf_raw_text"][qn]  # 全不同回退 raw
            else:
                evidence.table[qn] = next(iter(groups.values()))[0]

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
    # LaTeX 归一化（两侧同规）：DB `①. $0$ ②. $\frac{4}{3}$` 与
    # OCR `①.$0\quad\textcircled{2}.\;\frac{4}{3}$` 归一后都是 `①.0②.4/3`。
    if "$" in exp or "\\" in exp:
        exp = compact_text(normalize_math(expected))
        exp = re.sub(r"^[(（][0-9]+[)）]", "", exp)
    fragment = exp[:20]
    for section in evidence.answer_sections:
        compact_section = compact_text(section)
        if "$" in compact_section or "\\" in compact_section:
            compact_section = compact_text(normalize_math(section))
        for marker in (f"{qn}.\u3010\u7b54\u6848\u3011", f"{qn}\u3010\u7b54\u6848\u3011", f"{qn}.", f"{qn} "):
            pos = compact_section.find(marker)
            if pos < 0:
                continue
            window = compact_section[pos : pos + 2000]
            if fragment in window or exp[:12] in window:
                return True, "free_text", "pdf_raw_text"
    return False, "", ""


def _strip_score_annotations(s: str) -> str:
    """去掉分值注记（"（2分）"、"（2分公式1分结果1分）"）与分隔符。

    2026-08-25：答案区内联解答穿插分值注记，如物理 Q17
    "(1)a=0.2m/s²(2分公式1分结果1分)(2)…"，须剥掉才能连续比对。
    """
    s = re.sub(r"[（(]\s*\d+\s*分[^（(]*[)）]", "", s)
    s = s.replace("\uff1b", "").replace(";", "")
    return s


def _find_sub_answer(
    qn: str,
    sub_qno: str,
    sub_answer: str,
    evidence: DocumentAnswerEvidence,
) -> tuple[bool, str, str]:
    """综合题子题答案的内联搜索（父题标记 → 子题标记 → 窗口宽松包含）。

    2026-08-25 物理八十中 Q15/Q16：答案区内联给出子题答案
    （"15.（1）1.50（2分）（2）不能（2分）…"），但子题号是"（1）"非数字，
    verify_one 数字路径走不了；父题整体答案又因全角/半角与分值注记插缝
    无法整段命中。这里按子题逐个搜索：
    - 先定位父题号标记（"15."等），
    - 在窗口内定位子题标记（"(1)"/"（1）"），
    - 子题窗口做宽松归一（去分值注记、分隔符）后做包含比对。
    仅在父题整体匹配失败后启用，不改变"父题整体即命中"学科（如生物）的行为。
    """
    exp = compact_text(sub_answer)
    if not exp:
        return False, "", ""
    exp = re.sub(r"^[(（][0-9]+[)）]", "", exp)

    def tolerant(s: str) -> str:
        return _strip_score_annotations(compact_text(s))

    fragment = tolerant(exp)
    if not fragment:
        return False, "", ""
    inner = str(sub_qno or "").strip("\uff08\uff09()")
    sub_markers: list[str] = []
    if inner:
        sub_markers = [f"({inner})", f"\uff08{inner}\uff09", inner]
    for section in evidence.answer_sections:
        compact_section = compact_text(section)
        if "$" in compact_section or "\\" in compact_section:
            compact_section = compact_text(normalize_math(section))
        for qm in (f"{qn}.\u3010\u7b54\u6848\u3011", f"{qn}\u3010\u7b54\u6848\u3011", f"{qn}.", f"{qn} "):
            pos = compact_section.find(qm)
            if pos < 0:
                continue
            window = compact_section[pos : pos + 2000]
            paren_hit = False
            for sm in sub_markers:
                if not sm.startswith("(") and not sm.startswith("\uff08"):
                    continue
                spos = window.find(sm)
                if spos < 0:
                    continue
                paren_hit = True
                sub_window = tolerant(window[spos : spos + 2000])
                if fragment in sub_window:
                    return True, "composite", "pdf_raw_text"
            if not paren_hit:
                for sm in sub_markers:
                    spos = window.find(sm)
                    if spos < 0:
                        continue
                    sub_window = tolerant(window[spos : spos + 2000])
                    if fragment in sub_window:
                        return True, "composite", "pdf_raw_text"
    return False, "", ""


_CIRCLED_SUB = {
    "\u2460": "1", "\u2461": "2", "\u2462": "3", "\u2463": "4",
    "\u2464": "5", "\u2465": "6", "\u2466": "7", "\u2467": "8",
    "\u2468": "9", "\u2469": "10",
}


def _split_structured(answer: str) -> list[tuple[str, str]]:
    """拆分（1）…；（2）… 或 ①…②… 结构化答案 → [(子号, 子答案文本)]。

    2026-08-31 数学 Q15：DB 答案用圈号 "①. $6$ ②. $-\frac{7}{3}$"
    （无括号子号），原正则只认（N）→ parts 为空 → 退化为 free_text 失败。
    此处同时支持圈号 ①-⑩，按标记位置切分（子答案 = 本标记到下一标记间）。
    """
    pattern = re.compile(r"[（(]\s*(\d+)\s*[)）]|([\u2460-\u2469])")
    spans: list[tuple[int, str]] = []
    for m in pattern.finditer(answer or ""):
        if m.group(1) is not None:
            spans.append((m.start(), m.group(1)))
        else:
            spans.append((m.start(), _CIRCLED_SUB[m.group(2)]))
    parts: list[tuple[str, str]] = []
    for i, (pos, sub_no) in enumerate(spans):
        end = spans[i + 1][0] if i + 1 < len(spans) else len(answer or "")
        text = (answer or "")[pos:end]
        # 去掉子号标记本身与紧随的句点分隔（"①. " → ""），再清内部残留子号。
        # 注意只能用 ^ 锚定的开头清洗，通用空白/句点 regex 会误删公式小数
        # 点（"0.2"→"02"、"1.5N"→"15N"，2026-08-31 实测）。
        text = re.sub(r"^[（(]\s*\d+\s*[)）]|^[\u2460-\u2469]", "", text)
        text = re.sub(r"^[.．\uff0e\u3000\s]+", "", text)
        text = re.sub(r"[（(]\s*\d+\s*[)）]|[\u2460-\u2469]", "", text)
        parts.append((sub_no, text.strip()))
    return parts


def _greek_to_latex(s: str) -> str:
    """Unicode 希腊字母 → LaTeX 名（两侧同规）。

    2026-08-25 物理 PPS 版 Q20：DB 答案用 Unicode `θ`（PPS 提取纯文本
    "f=F sinθ"），答案区 OCR 用 LaTeX `\\theta`（归一化后 `theta`）——
    θ vs theta 不匹配导致 structured_partial。此处把 Unicode 希腊字母统一
    为 LaTeX 名，使两侧可比较。
    """
    for uni, name in (
        ("\u03b8", "theta"),    # θ
        ("\u1d703", "theta"),   # 𝜃（数学斜体）
        ("\u03c6", "varphi"),   # φ
        ("\u1d711", "varphi"),  # 𝜑（数学斜体）
        ("\u03b1", "alpha"),    # α
        ("\u03b2", "beta"),     # β
        ("\u03b3", "gamma"),    # γ
        ("\u03bc", "mu"),       # μ
        ("\u03c0", "pi"),       # π（normalize_math 已处理，这里兜底）
        ("\u03c9", "omega"),    # ω
        ("\u0394", "Delta"),    # Δ
    ):
        s = s.replace(uni, name)
    return s


def _find_structured_answer(
    qn: str,
    answer: str,
    evidence: DocumentAnswerEvidence,
) -> tuple[bool, int]:
    """（1）…；（2）… 结构化精简答案的分部核对。

    2026-08-25 物理 Q17/Q20 类：DB 答案为精简版
    （"（1）$a=0.2\\text{m/s}^2$；（2）$m=70\\text{kg}$；…"），答案区是完整
    解答（含中间步骤与分值注记），整段/首 20 字符无法命中。按子部分拆：
    每部分 LaTeX 归一化后取 "=" 后核心值，在题号标记 + 子题标记锚定的
    答案区窗口内逐一核对；全部命中才 matched（部分命中 → 保持 unverifiable）。
    返回 (全部命中, 命中数)。
    """
    parts = _split_structured(answer)
    # 2026-08-31 物理 Q18（1）：答案在受力分析图中，DB 用"见解析"占位
    # （答案区该子部分无文本答案，只有分值注记）。"见解析/见详解"语义 =
    # 答案在解析/图中，无文本可比对——从核对清单剔除（不要求匹配、不计缺失），
    # 但其余子部分仍须全部命中才 matched。
    parts = [p for p in parts if not re.search(r"见\s*(解析|详解)", p[1])]
    if len(parts) < 2:
        return False, 0
    found = 0
    for sub_no, part_text in parts:
        norm = compact_text(normalize_math(part_text))
        if not norm:
            continue
        # 2026-08-31 物理 Q20（3）：DB 答案含等价表述 "（或f2/f1=1/cosθ）"，
        # 答案区只给主式 `\cos\theta`。须在 split("=") 前剥离，否则内层 "="
        # 会把 fragment 拆成 "或" 分支的值（"1/costheta)"）。
        norm = re.sub(r"[（(]或[^（(]*[)）]", "", norm)
        fragment = norm.split("=")[-1].strip() if "=" in norm else norm.strip()
        fragment = _strip_score_annotations(fragment)
        fragment = _greek_to_latex(fragment)
        if not fragment:
            continue
        short = len(fragment) < 3
        matched = False
        for section in evidence.answer_sections:
            compact_section = compact_text(section)
            if "$" in compact_section or "\\" in compact_section:
                compact_section = compact_text(normalize_math(section))
            compact_section = _greek_to_latex(compact_section)
            for qm in (f"{qn}.\u3010\u7b54\u6848\u3011", f"{qn}\u3010\u7b54\u6848\u3011", f"{qn}.", f"{qn} "):
                pos = compact_section.find(qm)
                if pos < 0:
                    continue
                window = compact_section[pos : pos + 2000]
                for sm in (f"({sub_no})", f"\uff08{sub_no}\uff09"):
                    spos = window.find(sm)
                    if spos < 0:
                        continue
                    sub_window = _strip_score_annotations(window[spos : spos + 2000])
                    # 短片段（纯数字值如 "6"）只查子题标记紧邻区（数学 Q15 ①.$6$），
                    # 避免窗口越界命中后续题号/详解中的无关数字。
                    probe = sub_window[:80] if short else sub_window
                    if fragment in probe:
                        matched = True
                        break
                # 2026-08-31 数学 Q15（2）：负号值在答案行 OCR 丢失（"~7/3"），
                # 但题号窗口内详解含正确值（"取最小值-7/3"）——窗口级再搜一次。
                if not matched and fragment.startswith("-") and len(fragment) >= 3:
                    if fragment in window:
                        matched = True
                if matched:
                    break
            if matched:
                break
        if matched:
            found += 1
    return found == len(parts), found


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
        expected_text = compact_text(expected)
        if answer_text == expected_text:
            return AnswerVerification(
                status=MATCHED,
                evidence_kind=kind,
                evidence_source=source,
                expected=expected,
            )
        # LaTeX 归一化后相等也算 matched（如 DB `$0$` vs 答案区 `0`、`\frac{4}{3}` vs `4/3`）。
        if "$" in answer_text or "\\" in answer_text or "$" in expected_text or "\\" in expected_text:
            norm_a = compact_text(normalize_math(answer))
            norm_e = compact_text(normalize_math(expected))
            if norm_a and norm_e and norm_a == norm_e:
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

    # （1）…；（2）… 结构化精简答案：分部核对（仅非综合题）。
    # 2026-08-25 物理 Q17/Q20 类：DB 为精简版（"（1）a=0.2m/s²；…"），
    # 答案区为完整解答（含中间步骤与分值注记），整段无法命中。按子部分拆，
    # 每部分取 "=" 后核心值在题号+子题标记锚定窗口内核对；全部命中才 matched。
    # 综合题（有 sub_questions）走 composite 子题路径，不在此处理（Q15/Q16）。
    if not subs:
        structured_all, structured_found = _find_structured_answer(qn, answer, evidence)
        if structured_all:
            return AnswerVerification(status=MATCHED, evidence_kind="structured")
        if structured_found > 0:
            return AnswerVerification(reason="structured_partial")

    # 综合题：父题整体匹配失败后，按子题逐个搜索内联答案。
    # 2026-08-25 物理 Q15/Q16：子题号为"（1）"非数字，verify_one 数字路径
    # 无法验证；父题整体又因全角/半角+分值注记整段命不中。此处若全部子题
    # 在父题号附近的答案区内找到 → matched；部分找到 → composite_subquestion。
    if sub_total > 0:
        sub_found = 0
        for sub in subs:
            if not isinstance(sub, dict):
                continue
            sub_answer_text = compact_text(sub.get("answer") or "")
            if not sub_answer_text:
                continue
            sub_qno_text = str(sub.get("qno") or "")
            ok, _k, _s = _find_sub_answer(qn, sub_qno_text, sub_answer_text, evidence)
            if ok:
                sub_found += 1
        if sub_found == sub_total:
            return AnswerVerification(status=MATCHED, evidence_kind="composite")
        if sub_found > 0:
            return AnswerVerification(reason="composite_subquestion")

    # 子题有部分 matched 但未全部 → composite_subquestion（证据不完整，不可算通过）
    if sub_total > 0 and sub_matched > 0 and sub_matched < sub_total:
        return AnswerVerification(reason="composite_subquestion")
    if sub_total > 0 and sub_matched == 0:
        return AnswerVerification(reason="composite_subquestion")

    if not evidence.answer_sections:
        return AnswerVerification(reason="missing_answer_evidence")
    if re.fullmatch(r"[A-G]{1,4}", answer_text):
        return AnswerVerification(reason="no_answer_evidence")
    # 长自由文本答案（作文/长解答题）：答案区无题号标记时（如英语 Q46
    # 作文区是"第二节(20分) One possible version: Dear Jim, …"，无 "46."
    # 锚点），_find_free_text 无法命中。若答案前 40 字符在答案区逐字出现，
    # 视为答案与参考答案一致（有证据）→ matched；否则需人工审核
    # （essay_manual_review，2026-08-25）。
    if len(answer_text) >= _ESSAY_MIN_LENGTH:
        fragment = answer_text[:40]
        if fragment:
            for section in evidence.answer_sections:
                if fragment in compact_text(section):
                    return AnswerVerification(status=MATCHED, evidence_kind="essay")
        return AnswerVerification(reason="essay_manual_review")
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
