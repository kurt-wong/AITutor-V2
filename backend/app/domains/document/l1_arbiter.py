"""
L1 dual-source arbiter - LLM line-level arbitration.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.ai.gateway import LLMGateway
from app.domains.document.schemas_l1 import L1Document, L1Line

logger = logging.getLogger(__name__)


@dataclass
class L1LineAudit:
    """LLM arbitration result for a single line."""
    line_id: str
    selected_source: str    # native / ppsv3
    conflict_type: str      # equivalent / partial / complementary / conflicting
    conflict: bool
    evidence: str
    confidence: float


_ARBITRATION_PROMPT = """You are a document parsing arbiter. Given two source texts for the same line, determine which is more accurate.

Rules:
1. Output ONLY JSON, never output question body text
2. PP-StructureV3 is the DEFAULT base — prefer PP unless Native is clearly more complete
3. Formula/symbol lines ALWAYS prefer PP-StructureV3 (visual recognition is more accurate)
4. Only choose Native when it contains strictly more content than PP (e.g., PP is truncated)
5. If both sources have same content, choose PP (default base)
6. If Native is partial (missing content that PP has), choose PP and set conflict_type="partial"
7. If Native has extra content but PP is complete, choose PP and set conflict_type="complementary"
8. If content genuinely conflicts, choose PP and set conflict_type="conflicting"
9. If content is identical, set conflict_type="equivalent"

Input format:
{"line_id": "P1L001", "native": "...", "ppsv3": "...", "block_type": "text"}

Output format (strict JSON only):
{"line_id": "P1L001", "selected_source": "ppsv3", "conflict_type": "equivalent", "conflict": false, "evidence": "...", "confidence": 0.9}

Forbidden:
- Output question body text or LaTeX
- Output anything other than JSON
- Modify, supplement, or rewrite input text"""


async def arbitrate_lines(doc: L1Document, gateway: LLMGateway) -> list[L1LineAudit]:
    """Arbitrate dual-source L1 lines to determine best source.

    降级策略：优先用确定性比较选择 PP / native，只有归一化后无法判定
    的真实冲突行才调用 LLM。避免对等价行、超集行做无意义的逐行 LLM 仲裁。
    """
    dual_lines = [l for l in doc.lines if _has_dual_sources(l)]

    if not dual_lines:
        audits: list[L1LineAudit] = []
        for line in doc.lines:
            audits.append(L1LineAudit(
                line_id=line.line_id, selected_source=line.source,
                conflict_type="equivalent", conflict=False,
                evidence="single source", confidence=1.0,
            ))
        return audits

    audits: list[L1LineAudit] = []
    llm_lines: list[L1Line] = []
    for line in dual_lines:
        deterministic = _deterministic_audit(line)
        if deterministic is not None:
            audits.append(deterministic)
        else:
            llm_lines.append(line)

    if llm_lines:
        logger.info(
            "l1_arbiter deterministic=%d llm=%d",
            len(dual_lines) - len(llm_lines),
            len(llm_lines),
        )
        batch_size = 20
        for i in range(0, len(llm_lines), batch_size):
            batch = llm_lines[i:i + batch_size]
            audits.extend(await _arbitrate_batch(batch, gateway))

    single_lines = [l for l in doc.lines if not _has_dual_sources(l)]
    for line in single_lines:
        audits.append(L1LineAudit(
            line_id=line.line_id, selected_source=line.source,
            conflict_type="equivalent", conflict=False,
            evidence="single source", confidence=1.0,
        ))

    return audits


def _has_dual_sources(line: L1Line) -> bool:
    """判断是否同时持有 native/ppsv3 原始文本。

    raw_sources 会额外携带 native_line_id 溯源键，不能用 len() 判断双源。
    """
    raw = line.raw_sources or {}
    return "native" in raw and "ppsv3" in raw


def _normalize_source_text(text: str | None) -> str:
    """去除全部空白后比较双源文本，避免纯排版差异触发 LLM。"""
    return re.sub(r"\s+", "", text or "")


def _is_structure_or_formula(text: str | None) -> bool:
    """判断行是否偏向 PP 结构化/公式识别（这类行默认信任 PP）。"""
    return bool(re.search(
        r"\\frac|\\sqrt|\\sum|\\int|\\sin|\\cos|\\tan|\\log|\\begin|"
        r"\\left|\\big|\\cup|\\cap|\\in|\\pi|<table>|<html>",
        text or "",
    ))


def _deterministic_audit(line: L1Line) -> L1LineAudit | None:
    """对可确定性判定的双源行直接生成 audit；无法判定返回 None。"""
    pp_text = line.raw_sources.get("ppsv3", "")
    native_text = line.raw_sources.get("native", "")
    pp_norm = _normalize_source_text(pp_text)
    native_norm = _normalize_source_text(native_text)

    if not pp_text.strip() and not native_text.strip():
        return L1LineAudit(
            line_id=line.line_id,
            selected_source="ppsv3",
            conflict_type="equivalent",
            conflict=False,
            evidence="双源均为空，默认采用 PP",
            confidence=1.0,
        )
    if not pp_text.strip():
        return L1LineAudit(
            line_id=line.line_id,
            selected_source="native",
            conflict_type="complementary",
            conflict=False,
            evidence="PP 为空，确定性采用 native",
            confidence=0.9,
        )
    if not native_text.strip():
        return L1LineAudit(
            line_id=line.line_id,
            selected_source="ppsv3",
            conflict_type="partial",
            conflict=False,
            evidence="native 为空，确定性采用 PP",
            confidence=0.95,
        )

    if pp_norm == native_norm:
        return L1LineAudit(
            line_id=line.line_id,
            selected_source="ppsv3",
            conflict_type="equivalent",
            conflict=False,
            evidence="归一化后等价，默认采用 PP",
            confidence=1.0,
        )

    structure_line = (
        "formula" in (line.block_type or "").lower()
        or "table" in (line.block_type or "").lower()
        or _is_structure_or_formula(pp_text)
        or _is_structure_or_formula(native_text)
    )
    if not structure_line and native_norm and pp_norm in native_norm:
        if _coverage_check(pp_text, native_text, "complementary"):
            return L1LineAudit(
                line_id=line.line_id,
                selected_source="native",
                conflict_type="complementary",
                conflict=False,
                evidence="native 确定性超集，采用 native",
                confidence=0.9,
            )

    if pp_norm and native_norm in pp_norm:
        return L1LineAudit(
            line_id=line.line_id,
            selected_source="ppsv3",
            conflict_type="partial",
            conflict=False,
            evidence="PP 确定性超集，采用 PP",
            confidence=0.95,
        )

    return None


async def _arbitrate_batch(lines: list[L1Line], gateway: LLMGateway) -> list[L1LineAudit]:
    inputs = []
    for line in lines:
        inputs.append({
            "line_id": line.line_id,
            "native": line.raw_sources.get("native", ""),
            "ppsv3": line.raw_sources.get("ppsv3", ""),
            "block_type": line.block_type,
        })

    prompt = _ARBITRATION_PROMPT + "\n\nInput:\n" + json.dumps(inputs, ensure_ascii=False)
    response = await gateway.complete(prompt)

    try:
        results = json.loads(response)
        if not isinstance(results, list):
            results = [results]
    except json.JSONDecodeError:
        logger.error("LLM arbitration response is not valid JSON")
        return [
            L1LineAudit(line_id=l.line_id, selected_source="ppsv3", conflict_type="equivalent",
                        conflict=False, evidence="LLM parse failed, fallback ppsv3", confidence=0.5)
            for l in lines
        ]

    audits = []
    for line in lines:
        result = next((r for r in results if r.get("line_id") == line.line_id), None)
        if result and not _contains_body_text(result):
            audits.append(L1LineAudit(
                line_id=line.line_id,
                selected_source=result.get("selected_source", "ppsv3"),
                conflict_type=result.get("conflict_type", "equivalent"),
                conflict=result.get("conflict", False),
                evidence=result.get("evidence", ""),
                confidence=result.get("confidence", 0.5),
            ))
        else:
            audits.append(L1LineAudit(
                line_id=line.line_id, selected_source="ppsv3", conflict_type="equivalent",
                conflict=False, evidence="LLM violation or missing, fallback ppsv3", confidence=0.5,
            ))

    return audits


def _contains_body_text(result: dict) -> bool:
    """Check if LLM response contains forbidden body text in any field.

    LLM should only output metadata (line_id, selected_source, conflict, confidence).
    Body text in evidence or any other field is a violation.
    """
    # Fields that should NEVER contain body text
    forbidden_keys = {
        "text", "content", "body", "stem", "latex", "formula",
        "question", "option", "answer_text", "explanation",
    }
    for key in forbidden_keys:
        if key in result and isinstance(result[key], str) and len(result[key]) > 20:
            return True

    # Evidence field: allow short justification, reject body text
    evidence = result.get("evidence", "")
    if isinstance(evidence, str) and len(evidence) > 200:
        return True

    # Check for LaTeX patterns in any string field (body text indicator)
    for key, val in result.items():
        if isinstance(val, str) and key != "line_id":
            if "\\frac" in val or "\\sqrt" in val or "\\sum" in val:
                return True
            if val.count("$") >= 2:  # Math delimiter pairs
                return True
            # Superscript/subscript patterns: ^{...}, _{...}
            if "^{" in val or "_{" in val:
                return True
            # Common math function names in evidence context
            math_funcs = ["\\sin", "\\cos", "\\tan", "\\log", "\\lg", "\\ln",
                          "\\forall", "\\exists", "\\geq", "\\leq", "\\neq"]
            if any(fn in val for fn in math_funcs):
                return True

    return False


def _coverage_check(pp_text: str, selected_text: str, conflict_type: str) -> bool:
    """检查选定文本是否覆盖了 PP 的所有内容。

    如果 selected_text 缺少 PP 已有的题号、选项签名或答案条目，返回 False。
    无论 conflict_type 如何，只要 selected_source == native，都必须执行覆盖校验。
    """
    import re

    # partial 类型：native 是部分内容，直接拒绝
    if conflict_type == "partial":
        return False

    # 检查选项签名：(A)/(B)/(C)/(D)
    pp_opts = set(re.findall(r'[（(]\s*([A-D])\s*[）)]', pp_text))
    sel_opts = set(re.findall(r'[（(]\s*([A-D])\s*[）)]', selected_text))
    if pp_opts and not pp_opts.issubset(sel_opts):
        return False  # 选定文本缺少 PP 的选项

    # 检查答案条目：(数字)字母
    pp_answers = set(re.findall(r'[（(]\s*(\d+)\s*[）)]\s*[A-D]', pp_text))
    sel_answers = set(re.findall(r'[（(]\s*(\d+)\s*[）)]\s*[A-D]', selected_text))
    if pp_answers and not pp_answers.issubset(sel_answers):
        return False  # 选定文本缺少 PP 的答案条目

    # 检查题号：数字. 或 数字、
    pp_qnums = set(re.findall(r'^\s*(\d+)\s*[.、]', pp_text, re.MULTILINE))
    sel_qnums = set(re.findall(r'^\s*(\d+)\s*[.、]', selected_text, re.MULTILINE))
    if pp_qnums and not pp_qnums.issubset(sel_qnums):
        return False  # 选定文本缺少 PP 的题号

    return True


def apply_arbitration(doc: L1Document, audits: list[L1LineAudit]) -> L1Document:
    audit_map = {a.line_id: a for a in audits}
    new_lines = []
    for line in doc.lines:
        audit = audit_map.get(line.line_id)
        if audit:
            selected_text = line.raw_sources.get(audit.selected_source, line.text)

            # 覆盖校验：如果选定文本不覆盖 PP，回退到 PP
            pp_text = line.raw_sources.get("ppsv3", line.text)
            if audit.selected_source == "native" and not _coverage_check(pp_text, selected_text, audit.conflict_type):
                logger.debug(
                    "coverage check failed: line=%s source=native conflict_type=%s, fallback to ppsv3",
                    line.line_id, audit.conflict_type,
                )
                selected_text = pp_text
                audit.selected_source = "ppsv3"
                audit.confidence = max(0.3, audit.confidence - 0.2)  # 降级置信度

            new_line = L1Line(
                line_id=line.line_id, page_no=line.page_no,
                line_no_in_page=line.line_no_in_page, order=line.order,
                text=selected_text, block_type=line.block_type,
                bbox=line.bbox, source=audit.selected_source,
                continuation=line.continuation, raw_sources=line.raw_sources,
                selected_source=audit.selected_source, evidence=audit.evidence,
                confidence=audit.confidence,
            )
        else:
            new_line = line
        new_lines.append(new_line)

    return L1Document(
        filename=doc.filename, pages=doc.pages, lines=new_lines,
        images=doc.images, source="mixed", total_pages=doc.total_pages,
        text_coverage=doc.text_coverage, raw_lines=doc.raw_lines,
    )
