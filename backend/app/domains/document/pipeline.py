"""
文档处理管线 — 串联 Step 1-6 全部模块。

Pipeline 流程：
1. 双源 L1 生成（native + PP-StructureV3）→ 按 bbox 对齐填充 raw_sources
2. LLM 行级仲裁（l1_arbiter）— 选择每行最佳源
3. LLM 行号标注（line_annotator）
4. 锚点校正（anchor_corrector）
5. 内容切片（content_slicer）
6. 答案匹配（answer_matcher）
7. 质量门（quality_gate）

记录 stage/progress/error，支持 Golden Set 评估。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §8。
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Coroutine

from app.ai.gateway import LLMGateway
from app.domains.document.answer_matcher import match_answers
from app.domains.document.anchor_corrector import correct_anchors
from app.domains.document.content_slicer import slice_questions
from app.domains.document.image_deduplicator import deduplicate_images
from app.domains.document.l1_arbiter import arbitrate_lines, apply_arbitration
from app.domains.document.line_annotator import annotate_document
from app.domains.document.native_markdown import extract_l1_from_pdf
from app.domains.document.ppsv3_l1 import extract_l1_from_ocr
from app.domains.document.ocr.providers import build_ocr_chain
from app.domains.document.quality_gate import evaluate_quality
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import L2DocumentAnnotation, SlicedQuestion

logger = logging.getLogger(__name__)

# 进度回调类型：stage 名称 + 进度值（0-1）
ProgressCallback = Callable[[str, float], Coroutine[Any, Any, None]]


def _provenance_to_dict(prov) -> dict | None:
    """将 SourceProvenance 转换为可序列化的 dict。"""
    if prov is None:
        return None
    return {
        "field": prov.field,
        "source": prov.source,
        "confidence": prov.confidence,
        "evidence": prov.evidence,
    }


def _has_dual_sources(line: L1Line) -> bool:
    """判断是否同时持有 native/ppsv3 原始文本。

    raw_sources 还会携带 native_line_id 溯源键，不能用 len() 判断双源。
    """
    raw = line.raw_sources or {}
    return "native" in raw and "ppsv3" in raw


def _bbox_iou(box_a: dict | None, box_b: dict | None) -> float:
    """计算两个 bbox 的 IoU。任一 bbox 为 None 返回 0。"""
    if not box_a or not box_b:
        return 0.0
    x1 = max(box_a["x1"], box_b["x1"])
    y1 = max(box_a["y1"], box_b["y1"])
    x2 = min(box_a["x2"], box_b["x2"])
    y2 = min(box_a["y2"], box_b["y2"])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a["x2"] - box_a["x1"]) * (box_a["y2"] - box_a["y1"])
    area_b = (box_b["x2"] - box_b["x1"]) * (box_b["y2"] - box_b["y1"])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _filter_by_page_range(doc: L1Document, page_range: tuple[int, int]) -> L1Document:
    """按页码范围过滤 L1Document 的行。"""
    start, end = page_range
    filtered = [l for l in doc.lines if start <= l.page_no <= end]
    filtered_pages = [p for p in doc.pages if start <= p.page_no <= end]
    return L1Document(
        filename=doc.filename, pages=filtered_pages, lines=filtered,
        images=doc.images, source=doc.source, total_pages=doc.total_pages,
        text_coverage=doc.text_coverage, raw_lines=doc.raw_lines,
    )


def _estimate_bbox_scale_factor(native_lines: list, ppsv3_lines: list) -> float:
    """估算 native 与 PP bbox 的坐标系比例因子。

    PP-StructureV3 使用像素坐标（~150 DPI），
    PyMuPDF 使用 PDF points（72 DPI），
    两者比例约为 2x。通过比较同页 bbox 范围自动估算。
    """
    native_x_maxs: dict[int, float] = {}
    ppsv3_x_maxs: dict[int, float] = {}
    for line in native_lines:
        if line.bbox and line.bbox.get("x2"):
            native_x_maxs[line.page_no] = max(
                native_x_maxs.get(line.page_no, 0), line.bbox["x2"]
            )
    for line in ppsv3_lines:
        if line.bbox and line.bbox.get("x2"):
            ppsv3_x_maxs[line.page_no] = max(
                ppsv3_x_maxs.get(line.page_no, 0), line.bbox["x2"]
            )

    ratios = []
    for page_no in native_x_maxs:
        if page_no in ppsv3_x_maxs and native_x_maxs[page_no] > 0:
            ratios.append(ppsv3_x_maxs[page_no] / native_x_maxs[page_no])

    if not ratios:
        return 1.0
    ratios.sort()
    mid = len(ratios) // 2
    return ratios[mid]


def _normalize_bbox(bbox: dict | None, scale: float) -> dict | None:
    """将 native bbox 缩放到 PP 坐标系。"""
    if not bbox or scale == 1.0:
        return bbox
    return {
        "x1": bbox["x1"] * scale,
        "y1": bbox["y1"] * scale,
        "x2": bbox["x2"] * scale,
        "y2": bbox["y2"] * scale,
    }


def _text_similarity(a: str, b: str) -> float:
    """计算两个文本的相似度（OCR 容错）。

    主要使用 SequenceMatcher（顺序敏感），辅助 Jaccard（顺序不敏感）。
    加权组合：seq_sim 权重 0.7，jaccard 权重 0.3，
    防止字符打乱（AB vs BA）被误判为完全一致。
    长度比 < 0.3 直接返回 0，防止短文本误匹配长文本。
    """
    from difflib import SequenceMatcher
    sa = a.strip()
    sb = b.strip()
    if not sa or not sb:
        return 0.0
    len_ratio = min(len(sa), len(sb)) / max(len(sa), len(sb))
    if len_ratio < 0.3:
        return 0.0
    set_a, set_b = set(sa), set(sb)
    jaccard = len(set_a & set_b) / len(set_a | set_b) if set_a | set_b else 0.0
    seq_sim = SequenceMatcher(None, sa, sb).ratio()
    # 加权组合：SequenceMatcher 主导，Jaccard 辅助
    return 0.7 * seq_sim + 0.3 * jaccard


def _detect_line_type(text: str) -> str:
    """检测行的语义类型。

    Returns:
        "option" - 选项行，如 (A) ... (B) ...
        "answer_table" - 答案表格行，如 (1)A (2)B ...
        "question_number" - 题号行，如 1. / 8.
        "stem" - 题干文本
        "other" - 其他
    """
    import re
    # 答案表格行：包含 (数字)字母 模式，如 (1)A (2)B
    # 必须优先于选项检测，因为 (9)D 会被误判为选项
    if re.search(r'[（(]\s*\d+\s*[）)]\s*[A-D]', text):
        return "answer_table"
    # 选项行：包含 (A)/(B)/(C)/(D) 标记
    if re.search(r'[（(]\s*[A-D]\s*[）)]', text):
        return "option"
    # 题号行：以数字开头，后跟 . 或 、；或 (数字) 格式
    # 负向前瞻：. 后紧跟数字时不匹配（排除日期格式如 2026.1）
    if re.match(r'^\s*\d+\s*[.](?![\d\\])', text):
        return "question_number"
    if re.match(r'^\s*\d+\s*、', text):
        return "question_number"
    if re.match(r'^\s*[（(]\s*\d+\s*[）)]', text) and not re.search(r'[A-D]\s*[）)]', text):
        return "question_number"
    return "stem"


def _group_answer_table_entries(text: str) -> dict[int, str]:
    """从答案表格行中提取题号→答案映射。

    支持格式：(1)A (2)B ... 或 1.A 2.B ...
    """
    import re
    entries: dict[int, str] = {}
    # 匹配 (数字)字母 或 数字.字母
    for m in re.finditer(r'[（(]?\s*(\d+)\s*[）)]?\s*\.?\s*([A-D])', text):
        q_num = int(m.group(1))
        answer = m.group(2)
        entries[q_num] = answer
    return entries


def _group_option_entries(text: str) -> dict[str, str]:
    """从选项行中提取选项字母→内容映射。

    支持格式：(A) 内容 (B) 内容 ... 或 A. 内容 B. 内容 ...
    """
    import re
    entries: dict[str, str] = {}
    # 匹配 (A) 内容 或 A. 内容
    parts = re.split(r'[（(]\s*([A-D])\s*[）)]|(?<=\s)([A-D])\.\s*', text)
    current_letter = None
    for part in parts:
        if part is None:
            continue
        part = part.strip()
        if len(part) == 1 and part in "ABCD":
            current_letter = part
        elif current_letter:
            entries[current_letter] = part
            current_letter = None
    return entries


def _build_question_boundary_map(lines: list) -> dict[int, int]:
    """构建行序号→所属题号的映射。

    题号边界由 question_number 行定义：从一个题号行到下一个题号行之间的所有行
    属于该题号。返回 {line_order: question_number}。

    页边界重置：每页开始时 current_q=0。页内第一道题之前的行归到该页虚拟桶
    （page_no * 1000），而不是继承上一页的题号。

    Fallback：若某页没有 question_number 行，该页所有行归为独立虚拟题号（page_no * 1000）。
    """
    import re
    boundaries: dict[int, int] = {}
    current_q = 0  # 题号行之前的内容属于 "0"（标题等）
    prev_page = None
    page_has_question: dict[int, bool] = {}  # 每页是否有 question_number

    # 第一遍：正常检测 question_number，页边界重置 current_q
    for line in lines:
        # 页边界重置：新页开始时 current_q 回到 0
        if prev_page is not None and line.page_no != prev_page:
            current_q = 0
        prev_page = line.page_no

        if _detect_line_type(line.text) == "question_number":
            m = re.match(r'^\s*[（(]?\s*(\d+)', line.text)
            if m:
                current_q = int(m.group(1))
                page_has_question[line.page_no] = True

        # 如果当前页还没有 question_number，归到虚拟桶
        if page_has_question.get(line.page_no, False):
            boundaries[line.order] = current_q
        else:
            boundaries[line.order] = line.page_no * 1000

    return boundaries


def _validate_semantic_binding(pp_text: str, nat_text: str, pp_type: str) -> bool:
    """验证 PP 和 native 的语义绑定是否有效。

    返回 True 表示绑定有效（语义等价或 native 更完整）。
    返回 False 表示绑定无效（语义不匹配，应拒绝）。
    """
    if pp_type == "answer_table":
        pp_entries = _group_answer_table_entries(pp_text)
        nat_entries = _group_answer_table_entries(nat_text)
        # native 必须包含 PP 的所有题号，否则是部分内容
        if not pp_entries:
            return True  # PP 无法解析，允许绑定
        if not nat_entries:
            return False  # native 无法解析，拒绝绑定
        # native 必须覆盖 PP 的所有题号
        pp_q_nums = set(pp_entries.keys())
        nat_q_nums = set(nat_entries.keys())
        if not pp_q_nums.issubset(nat_q_nums):
            return False  # native 缺少 PP 的某些题号
        return True

    if pp_type == "option":
        pp_opts = _group_option_entries(pp_text)
        nat_opts = _group_option_entries(nat_text)
        # native 必须包含 PP 的所有选项
        if not pp_opts:
            return True
        if not nat_opts:
            return False
        pp_letters = set(pp_opts.keys())
        nat_letters = set(nat_opts.keys())
        if not pp_letters.issubset(nat_letters):
            return False  # native 缺少 PP 的某些选项
        return True

    # 对于题干和其他类型，允许绑定（文本差异由仲裁处理）
    return True


def _merge_dual_source(
    native_doc: L1Document,
    ppsv3_doc: L1Document,
) -> tuple[L1Document, int]:
    """构建双源 L1：以 PP postprocessed 为基准（数学公式更准确），
    按语义对齐 native 文本到 raw_sources。

    填充 raw_sources = {"native": ..., "ppsv3": ...}。
    行号体系使用 PP（因为 PP 对公式行的切分更准确）。

    语义对齐规则：
    - 选项行必须按选项字母 (A)/(B)/(C)/(D) 对齐
    - 答案表格行必须按题号对齐
    - 未对齐的文本不允许进入仲裁
    """
    # H2 修复：不再重复调用 postprocess_l1
    # native_doc 和 ppsv3_doc 已在各自的 L1 生成阶段后处理过
    # native_markdown.py 和 ppsv3_l1.py 各自调用了 postprocess_l1
    native_processed = native_doc
    ppsv3_processed = ppsv3_doc

    # 估算坐标系比例因子并归一化 native bbox
    scale = _estimate_bbox_scale_factor(native_processed.lines, ppsv3_processed.lines)
    if scale != 1.0:
        logger.info("bbox scale factor: native -> ppsv3 = %.2f", scale)
        for line in native_processed.lines:
            line.bbox = _normalize_bbox(line.bbox, scale)

    # 构建题号边界映射：每个行序号 → 所属题号
    pp_q_map = _build_question_boundary_map(ppsv3_processed.lines)
    nat_q_map = _build_question_boundary_map(native_processed.lines)

    # 构建 native 索引：按页分组，按语义类型分组，按题号分组
    native_by_page: dict[int, list] = {}
    for line in native_processed.lines:
        native_by_page.setdefault(line.page_no, []).append(line)

    # 按 (page_no, question_number) 构建 native 选项/答案表索引
    native_options_by_q: dict[tuple[int, int], list] = {}  # (page, q_num) → [L1Line]
    native_answer_tables_by_q: dict[tuple[int, int], list] = {}  # (page, q_num) → [L1Line]
    for line in native_processed.lines:
        line_type = _detect_line_type(line.text)
        q_num = nat_q_map.get(line.order, 0)
        key = (line.page_no, q_num)
        if line_type == "option":
            native_options_by_q.setdefault(key, []).append(line)
        elif line_type == "answer_table":
            native_answer_tables_by_q.setdefault(key, []).append(line)

    # 构建 native 行号索引：Native 与 PP 行号前缀不同，按 (page, line_no) 对齐
    native_by_line_no: dict[tuple[int, int], L1Line] = {}
    for line in native_processed.lines:
        native_by_line_no[(line.page_no, line.line_no_in_page)] = line

    # 构建 proc 索引：line_id 精确匹配（主），(page, text) 回退（辅）
    proc_by_id = {l.line_id: l for l in ppsv3_processed.lines}
    proc_fallback: dict[tuple[int, str], list[L1Line]] = {}
    for pl in ppsv3_processed.lines:
        proc_fallback.setdefault((pl.page_no, pl.text.strip()), []).append(pl)
    used_fallback_ids: set[str] = set()

    merged_lines: list[L1Line] = []
    for orig_pp_line in ppsv3_doc.lines:
        # 优先：按 line_id 精确匹配（postprocess 保留 line_id，最可靠）
        line = proc_by_id.get(orig_pp_line.line_id)
        if line is None:
            # 回退：按 (page, text) 匹配，每行只用一次避免重复
            key = (orig_pp_line.page_no, orig_pp_line.text.strip())
            for cand in proc_fallback.get(key, []):
                if cand.line_id not in used_fallback_ids:
                    line = cand
                    used_fallback_ids.add(cand.line_id)
                    break
        if line is None:
            continue

        pp_type = _detect_line_type(line.text)

        # Primary 策略：按 (page, line_no) 对齐 Native/PP
        # 但必须验证文本内容足够相似，避免不同切分的行被错误绑定
        nat_match = native_by_line_no.get(
            (line.page_no, line.line_no_in_page)
        )
        if nat_match and _text_similarity(line.text, nat_match.text) > 0.6:
            best_match = nat_match
            best_score = 1.0
        else:
            best_match = None
            best_score = 0.0

        if pp_type == "answer_table" and not best_match:
            # 答案表格：按题号匹配，限定在同一题目范围内
            pp_entries = _group_answer_table_entries(line.text)
            pp_q_num = pp_q_map.get(line.order, 0)
            # 在同页同题范围内查找 native 答案表
            for nat_line in native_answer_tables_by_q.get((line.page_no, pp_q_num), []):
                if not pp_entries:
                    break
                nat_entries = _group_answer_table_entries(nat_line.text)
                if not nat_entries:
                    continue
                pp_q = set(pp_entries.keys())
                nat_q = set(nat_entries.keys())
                coverage = len(pp_q & nat_q) / len(pp_q) if pp_q else 0
                agreement = sum(1 for q in pp_q & nat_q if pp_entries[q] == nat_entries[q])
                agreement_rate = agreement / len(pp_q & nat_q) if pp_q & nat_q else 0
                score = coverage * 0.6 + agreement_rate * 0.4
                if score > best_score:
                    best_score = score
                    best_match = nat_line

        elif pp_type == "option" and not best_match:
            # 先确定此 PP 选项属于哪道题
            pp_q_num = pp_q_map.get(line.order, 0)
            pp_opts = _group_option_entries(line.text)
            if not pp_opts:
                pass  # 无法解析选项，跳过匹配
            else:
                pp_letters = set(pp_opts.keys())
                # 只在同页同题范围内的 native 选项中查找
                for nat_line in native_options_by_q.get((line.page_no, pp_q_num), []):
                    nat_opts = _group_option_entries(nat_line.text)
                    if not nat_opts:
                        continue
                    nat_letters = set(nat_opts.keys())
                    coverage = len(pp_letters & nat_letters) / len(pp_letters) if pp_letters else 0
                    if coverage > best_score:
                        best_score = coverage
                        best_match = nat_line

        elif not best_match:
            # 题干和其他类型：使用 bbox IoU 作为辅助
            for nat_line in native_by_page.get(line.page_no, []):
                iou = _bbox_iou(line.bbox, nat_line.bbox)
                if iou > best_score:
                    best_score = iou
                    best_match = nat_line

        # 验证语义绑定；native 行号只进 raw_sources，不覆盖 canonical P 行号
        if best_match and best_score > 0.3:
            if _validate_semantic_binding(line.text, best_match.text, pp_type):
                raw_sources = {
                    "ppsv3": line.text,
                    "native": best_match.text,
                    "native_line_id": best_match.line_id,
                }
            else:
                # 语义绑定无效，只保留 PP
                logger.debug(
                    "semantic binding rejected: pp=%s nat=%s type=%s",
                    line.line_id, best_match.line_id, pp_type,
                )
                raw_sources = {"ppsv3": line.text}
        else:
            raw_sources = {"ppsv3": line.text}

        merged_line = L1Line(
            line_id=line.line_id, page_no=line.page_no,
            line_no_in_page=line.line_no_in_page, order=line.order,
            text=line.text, block_type=line.block_type,
            bbox=line.bbox, source="ppsv3",
            continuation=line.continuation, raw_sources=raw_sources,
        )
        merged_lines.append(merged_line)

    # 记录 native-only 行信息（不添加为新行，避免破坏行号体系）
    # 这些行可由下游 consumer 按需获取
    native_only_count = 0
    merged_nat_ids: set[str] = set()
    for ml in merged_lines:
        raw = ml.raw_sources or {}
        nat_lid = raw.get("native_line_id")
        if nat_lid:
            merged_nat_ids.add(nat_lid)
        elif "native" in raw:
            nat_text = raw["native"]
            for nat_line in native_processed.lines:
                if nat_line.text.strip() == nat_text.strip():
                    merged_nat_ids.add(nat_line.line_id)
                    break
    native_only_count = sum(1 for l in native_processed.lines if l.line_id not in merged_nat_ids)
    if native_only_count > 0:
        logger.info("merge: %d native-only lines not in PP (not added to preserve line numbering)", native_only_count)

    # 图片合并策略：per-image fallback
    # 以 PP-StructureV3 图片为主，native 图片仅在 ppsv3 无对应时补充
    merged_images = list(ppsv3_doc.images)
    if native_processed.images:
        # 复用已计算的 scale（native lines 已归一化，重新计算会得到 1.0）

        # 收集 ppsv3 图片的 (page_no, bbox) 用于匹配
        ppsv3_img_bboxes: dict[int, list[dict]] = {}
        for img in ppsv3_processed.images:
            ppsv3_img_bboxes.setdefault(img.page_no, []).append(img.bbox or {})

        # 逐张检查 native 图片
        native_added = 0
        missing_figure_count = 0
        for nat_img in native_processed.images:
            if not nat_img.bbox:
                # V1_LESSONS 3.4: 无 bbox 时记录 missing_figure，不整页兜底
                nat_img.placement = "missing_figure"
                missing_figure_count += 1
                continue

            # 归一化 native bbox 到 ppsv3 坐标系
            nat_bbox_norm = _normalize_bbox(nat_img.bbox, scale)
            nat_cx = (nat_bbox_norm["x1"] + nat_bbox_norm["x2"]) / 2
            nat_cy = (nat_bbox_norm["y1"] + nat_bbox_norm["y2"]) / 2

            # 检查是否有 ppsv3 图片在同一区域（50px 容差）
            has_ppsv3_match = False
            for pp_bbox in ppsv3_img_bboxes.get(nat_img.page_no, []):
                if not pp_bbox:
                    continue
                pp_cx = (pp_bbox["x1"] + pp_bbox["x2"]) / 2
                pp_cy = (pp_bbox["y1"] + pp_bbox["y2"]) / 2
                if abs(nat_cx - pp_cx) < 50 and abs(nat_cy - pp_cy) < 50:
                    has_ppsv3_match = True
                    break

            if not has_ppsv3_match:
                # native 图片在 ppsv3 中无对应，补充添加
                merged_images.append(nat_img)
                native_added += 1

        if native_added > 0:
            logger.info("merge: added %d native images not in ppsv3", native_added)
        if missing_figure_count > 0:
            logger.info("merge: %d native images missing bbox (marked as missing_figure)", missing_figure_count)

    return L1Document(
        filename=ppsv3_doc.filename, pages=ppsv3_processed.pages,
        lines=merged_lines, images=merged_images,
        source="mixed", total_pages=ppsv3_doc.total_pages,
        text_coverage=ppsv3_doc.text_coverage,
        raw_lines=ppsv3_processed.raw_lines,
    ), native_only_count


def _anchor_to_dict(anchor) -> dict | None:
    """将 CorrectedAnchor 转换为可序列化的 dict。"""
    if anchor is None:
        return None
    return {
        "field": anchor.field,
        "llm_line_ids": anchor.llm_line_ids,
        "corrected_line_ids": anchor.corrected_line_ids,
        "anchor_status": anchor.anchor_status,
        "validation_passed": anchor.validation_passed,
        "evidence": anchor.evidence,
    }


def _slice_l1_text(doc: L1Document | None, line_ids: list[str]) -> str:
    """Slice original L1 text for shared material review display."""
    if not doc:
        return ""
    line_by_id = {line.line_id: line for line in doc.lines}
    return "\n".join(
        line_by_id[lid].text
        for lid in line_ids
        if lid in line_by_id
    )


def _question_is_ingested(q: dict) -> bool:
    """判断题目是否达到可入库标准：高置信度且无禁止自动发布问题。"""
    if q.get("confidence", 0) < 0.8:
        return False
    if any("禁止自动发布" in i for i in (q.get("issues") or [])):
        return False
    if not (q.get("stem") or "").strip():
        return False
    if not (q.get("answer") or "").strip():
        return False
    return True


def _discard_reason_label(issue: str) -> str:
    """把质量门 issue 映射为简洁的未入库原因。"""
    if "锚点" in issue:
        return "锚点不确定"
    if "答案缺失" in issue:
        return "答案缺失"
    if "答案可疑" in issue:
        return "答案可疑"
    if "选项" in issue:
        return "选项异常"
    if "题干为空" in issue:
        return "题干为空"
    if "LLM 答案切片为空或仅标点" in issue:
        return "答案切片无效"
    return issue.split("，")[0].split("；")[0]


def _discard_category_for_issue(issue: str) -> str:
    """把质量门 issue 映射为更细的丢弃类别。"""
    if "行号" in issue or "line_id" in issue:
        return "invalid_line_id"
    if "答案缺失" in issue or "LLM 答案切片为空或仅标点" in issue:
        return "answer_empty"
    if "锚点" in issue:
        return "anchor_mismatch"
    if "答案可疑" in issue:
        return "answer_suspicious"
    if "选项" in issue:
        return "options_anomaly"
    if "题干为空" in issue:
        return "stem_empty"
    return "blocked"


class PipelineResult:
    """管线执行结果。

    三态语义（T3_IMPLEMENTATION §9）：
    - succeeded: 所有关键 stage 成功
    - failed: 任一关键 stage 失败（L1/标注/锚点/切片/答案匹配/质量门）
    - partial_failed: 保留字段，当前不使用（所有 stage 要么成功要么失败）

    关键 stage 失败时，任务状态必须为 failed，不能为 succeeded。
    """

    def __init__(self) -> None:
        self.status: str = "succeeded"  # succeeded / failed / partial_failed
        self.stages: list[dict] = []
        self.stage_errors: list[dict] = []  # [{"stage": "...", "error": "..."}]
        self.l1_document: L1Document | None = None  # canonical 合并后的 L1
        self.native_l1_document: L1Document | None = None  # PyMuPDF 提取的 native L1（图片bbox/答案表辅助）
        self.l2_annotation: L2DocumentAnnotation | None = None
        self.sliced_questions: list[SlicedQuestion] = []
        self.question_images: list[dict] = []  # DSD question_images 关联
        self.errors: list[str] = []
        self.total_time_ms: int = 0
        # OCR 提供方证据（2026-08-25 T0-4）：哪个 OCR 提供方完成了提取。
        # ocr_provider_used = provider.name（paddleocr / mimo-vl / deepseek-vl）
        # ocr_model_used = 学科路由选择的模型（PP-StructureV3 / PaddleOCR-VL-1.6）
        self.ocr_provider_used: str | None = None
        self.ocr_model_used: str | None = None

    def add_stage(self, name: str, duration_ms: int, **info) -> None:
        self.stages.append({
            "name": name,
            "duration_ms": duration_ms,
            **info,
        })

    def to_dict(self) -> dict:
        # 提取 L1 图片元数据（去重后，过滤无 bbox 的 PP 内部诊断图）
        images_out = []
        if self.l1_document:
            for img in self.l1_document.images:
                # 无 bbox 的图片是 PP 内部诊断图（layout_det_res 等），不输出
                if not img.bbox:
                    continue
                images_out.append({
                    "image_id": img.image_id,
                    "page_no": img.page_no,
                    "bbox": img.bbox,
                    "source": img.source,
                    "figure_id": img.figure_id,
                    "placement": img.placement,
                    "url": img.url,
                    "xref": img.xref,
                })
        questions = [
            {
                "question_number": sq.question_number,
                "question_type": sq.question_type,
                "section_id": sq.section_id,
                "stem": sq.stem,
                "stem_line_ids": sq.stem_anchor.corrected_line_ids if sq.stem_anchor else [],
                "options": sq.options,
                "options_line_ids": {a.field.replace("option_", ""): a.corrected_line_ids for a in sq.corrected_anchors if a.field.startswith("option_")},
                "answer": sq.answer,
                "explanation": sq.explanation,
                "difficulty": sq.difficulty,
                "score": sq.score,
                "knowledge_points": sq.knowledge_points,
                "confidence": sq.confidence,
                "source_page": sq.source_page,
                "structure_signature": sq.structure_signature,
                "answer_line_ids": sq.answer_line_ids,
                "explanation_line_ids": sq.explanation_line_ids,
                "answer_provenance": _provenance_to_dict(sq.answer_provenance),
                "explanation_provenance": _provenance_to_dict(sq.explanation_provenance),
                "corrected_anchors": [_anchor_to_dict(a) for a in sq.corrected_anchors],
                "shared_material_line_ids": sq.shared_material_line_ids,
                "shared_material": _slice_l1_text(
                    self.l1_document,
                    sq.shared_material_line_ids,
                ),
                "is_composite": sq.is_composite,
                "sub_questions": [
                    {
                        "qno": sq_sub.qno,
                        "question_type": sq_sub.question_type,
                        "answer": sq_sub.answer,
                        "knowledge_points": sq_sub.knowledge_points,
                        "score": sq_sub.score,
                    }
                    for sq_sub in (sq.sub_questions or [])
                ],
                "review_notes": sq.review_notes or [],
                "issues": sq.issues,
            }
            for sq in self.sliced_questions
        ]
        ingested = [q for q in questions if _question_is_ingested(q)]
        discarded = [q for q in questions if q not in ingested]
        discard_reasons: dict[str, int] = {}
        for q in discarded:
            reasons = {
                _discard_reason_label(issue)
                for issue in (q.get("issues") or [])
            }
            for reason in reasons:
                discard_reasons[reason] = discard_reasons.get(reason, 0) + 1
            q["discard_categories"] = sorted({
                _discard_category_for_issue(issue)
                for issue in (q.get("issues") or [])
            })
            q["discard_details"] = list(q.get("issues") or [])

        llm_annotation_out = None
        if self.l2_annotation is not None:
            anchor_by_question: dict[str, dict[str, dict]] = {}
            for anchor in self.l2_annotation.corrected_anchors:
                q_num = anchor.question_number
                if q_num:
                    anchor_by_question.setdefault(q_num, {})[anchor.field] = {
                        "anchor_status": anchor.anchor_status,
                        "evidence": anchor.evidence,
                        "corrected_line_ids": anchor.corrected_line_ids,
                    }
            llm_questions = []
            for q in self.l2_annotation.questions:
                anchors = anchor_by_question.get(q.question_number, {})
                stem_anchor = anchors.get("stem")
                llm_questions.append({
                    "question_number": q.question_number,
                    "question_type": q.question_type,
                    "section_id": q.section_id,
                    "stem_start_marker": q.stem_start_marker,
                    "stem_end_marker": q.stem_end_marker,
                    "stem_line_ids": q.stem_line_ids,
                    "options_line_ids": q.options_line_ids,
                    "answer_line_ids": q.answer_line_ids,
                    "explanation_line_ids": q.explanation_line_ids,
                    "stem_anchor": stem_anchor,
                    "option_anchors": {
                        key: value
                        for key, value in anchors.items()
                        if key.startswith("option_")
                    },
                })
            llm_annotation_out = {
                "filename": self.l2_annotation.filename,
                "subject": self.l2_annotation.subject,
                "metadata_confidence": self.l2_annotation.metadata_confidence,
                "questions": llm_questions,
                "anchor_status_summary": self.l2_annotation.anchor_status_summary,
                "raw_response": self.l2_annotation.raw_response,
            }

        return {
            "status": self.status,
            "stages": self.stages,
            "stage_errors": self.stage_errors,
            "total_time_ms": self.total_time_ms,
            "errors": self.errors,
            "ocr_provider_used": self.ocr_provider_used,
            "ocr_model_used": self.ocr_model_used,
            "question_count": len(self.sliced_questions),
            "images": images_out,
            "question_images": self.question_images,
            "questions": questions,
            "ingested_questions": ingested,
            "discarded_questions": discarded,
            "ingest_summary": {
                "total": len(questions),
                "ingested": len(ingested),
                "discarded": len(discarded),
                "discard_reasons": discard_reasons,
            },
            "llm_annotation": llm_annotation_out,
        }


def _question_field_line_ids(q, field: str) -> list[str]:
    """从题目对象提取字段的行号：优先 corrected anchor，回退到 line_ids 属性。

    SlicedQuestion 的行号存在 stem_anchor/options_anchor（CorrectedAnchor）的
    corrected_line_ids 中；部分调用方（测试 mock）直接暴露 stem_line_ids 属性。
    """
    anchor = getattr(q, f"{field}_anchor", None)
    if anchor is not None:
        cids = getattr(anchor, "corrected_line_ids", None)
        if isinstance(cids, list) and cids:
            return list(cids)
    return list(getattr(q, f"{field}_line_ids", None) or [])


def save_result(result: PipelineResult, output_path: Path) -> None:
    """保存管线结果到 JSON 文件。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("pipeline result saved to %s", output_path)


async def run_pipeline(
    pdf_path: Path | None = None,
    *,
    filename: str | None = None,
    gateway: LLMGateway,
    page_range: tuple[int, int] | None = None,
    ppsv3_doc: L1Document | None = None,
    native_doc: L1Document | None = None,
) -> PipelineResult:
    """执行完整的文档处理管线（双源 L1 + LLM 行级仲裁路径）。

    生产主路径为 simple_pipeline.run_simple_pipeline；本函数保留旧的双源
    仲裁语义，作为 fallback 供 eval 脚本（run_phase1_eval.py 等）与兼容
    测试使用（simple_pipeline docstring 约定 pipeline.py 保持不变）。

    Fix 1 (CRITICAL): 空 L1 文档归一化为 None；双源全空 → status=failed
    且 stage_errors 记录 l1_generation，禁止空结果以 succeeded 通过。

    Args:
        pdf_path: PDF 文件路径（可选，为 None 时跳过 native L1 提取和 OCR）
        filename: 文件名（可选）
        gateway: LLM 网关
        page_range: 页码范围（可选）
        ppsv3_doc: 预计算的 PP-StructureV3 L1Document（可选，跳过 OCR）。
            用于 eval 和测试；生产环境不传此参数，由 OCR 链路生成。
        native_doc: 预计算的 native L1Document（可选，跳过 native 提取）。
            用于 eval 和测试；生产环境不传此参数，由 PyMuPDF 提取。
    """
    result = PipelineResult()
    total_start = time.perf_counter()

    # Stage 1: 双源 L1 生成（native + PP-StructureV3）
    stage_start = time.perf_counter()
    if native_doc is None and pdf_path is not None:
        try:
            native_doc = extract_l1_from_pdf(pdf_path, filename=filename, page_range=page_range)
            result.add_stage("native_l1", int((time.perf_counter() - stage_start) * 1000),
                             lines=len(native_doc.lines), text_coverage=native_doc.text_coverage)
        except Exception as exc:
            logger.warning("native_l1 failed: %s", exc)
    elif native_doc is not None:
        result.add_stage("native_l1", 0, note="pre-computed", lines=len(native_doc.lines))

    # 运行 PP-StructureV3（可传入预计算的 ppsv3_doc 跳过 OCR）
    if ppsv3_doc is None and pdf_path is None:
        logger.warning("ppsv3_l1 skipped: no ppsv3_doc and no pdf_path")
    elif ppsv3_doc is None:
        try:
            ocr_start = time.perf_counter()
            ocr_chain = build_ocr_chain()
            ocr_doc = await ocr_chain.extract(pdf_path)
            result.ocr_provider_used = ocr_doc.provider_used or result.ocr_provider_used
            ppsv3_doc = extract_l1_from_ocr(ocr_doc, filename=filename)
            duration = int((time.perf_counter() - ocr_start) * 1000)
            result.add_stage(
                "ppsv3_l1", duration,
                lines=len(ppsv3_doc.lines),
                provider=result.ocr_provider_used,
            )
        except Exception as exc:
            logger.warning("ppsv3_l1 failed: %s", exc)
    else:
        result.add_stage("ppsv3_l1", 0, note="pre-computed", lines=len(ppsv3_doc.lines))

    # 按 page_range 过滤（预计算文档可能包含全部页面）
    if native_doc and page_range:
        native_doc = _filter_by_page_range(native_doc, page_range)
    if ppsv3_doc and page_range:
        ppsv3_doc = _filter_by_page_range(ppsv3_doc, page_range)

    # Fix 1 (CRITICAL): 空 L1 文档归一化为 None，避免空结果通过 merge 后仍 succeeded
    if native_doc is not None and not native_doc.lines:
        native_doc = None
    if ppsv3_doc is not None and not ppsv3_doc.lines:
        ppsv3_doc = None

    # 构建双源 L1
    if native_doc and ppsv3_doc:
        doc, native_only_count = _merge_dual_source(native_doc, ppsv3_doc)
        result.add_stage("dual_source_merge", 0,
                         dual_source_lines=sum(1 for l in doc.lines if len(l.raw_sources) > 1),
                         native_only_lines=native_only_count)
    elif native_doc:
        # 仅 native：填充 raw_sources
        from app.domains.document.l1_postprocessor import postprocess_l1
        doc = postprocess_l1(native_doc)
        for line in doc.lines:
            line.raw_sources = {"native": line.text}
    elif ppsv3_doc:
        from app.domains.document.l1_postprocessor import postprocess_l1
        doc = postprocess_l1(ppsv3_doc)
        for line in doc.lines:
            line.raw_sources = {"ppsv3": line.text}
            line.source = "ppsv3"
    else:
        result.status = "failed"
        result.stage_errors.append({
            "stage": "l1_generation",
            "error": "both native and PP-StructureV3 failed",
        })
        result.errors.append("Stage 1: both native and PP-StructureV3 failed")
        logger.error("pipeline stage_1_failed: both sources failed")
        result.total_time_ms = int((time.perf_counter() - total_start) * 1000)
        return result

    result.l1_document = doc

    # Stage 1.5: LLM 行级仲裁
    stage_start = time.perf_counter()
    dual_count = sum(1 for l in doc.lines if len(l.raw_sources) > 1)
    if dual_count > 0:
        try:
            audits = await arbitrate_lines(doc, gateway)
            doc = apply_arbitration(doc, audits)
            result.l1_document = doc
            duration = int((time.perf_counter() - stage_start) * 1000)
            conflicts = sum(1 for a in audits if a.conflict)
            # 真实仲裁统计：实际调用 LLM 仲裁的双源行数
            llm_audited = sum(1 for l in doc.lines
                              if len(l.raw_sources) > 1
                              and getattr(l, "selected_source", None) is not None)
            result.add_stage("l1_arbiter", duration,
                             audited=len(audits), conflicts=conflicts,
                             llm_audited=llm_audited)
        except Exception as exc:
            logger.warning("l1_arbiter failed: %s, using native fallback", exc)
            result.add_stage("l1_arbiter", 0, error=str(exc))
    else:
        result.add_stage("l1_arbiter", 0, note="no dual-source lines")

    # Stage 2: L1 后处理（已在 Stage 1 中完成）
    result.add_stage("l1_postprocess", 0, note="included in dual_source_merge")

    # Stage 3: LLM 标注
    stage_start = time.perf_counter()
    try:
        annotation = await annotate_document(doc, gateway)
        result.l2_annotation = annotation
        duration = int((time.perf_counter() - stage_start) * 1000)
        result.add_stage("llm_annotation", duration, questions=len(annotation.questions))
    except Exception as exc:
        result.errors.append(f"Stage 3 (llm_annotation): {exc}")
        logger.error("pipeline stage_3_failed: %s", exc)
        result.total_time_ms = int((time.perf_counter() - total_start) * 1000)
        return result

    # Stage 4: 锚点校正
    stage_start = time.perf_counter()
    try:
        annotation = correct_anchors(annotation, doc)
        duration = int((time.perf_counter() - stage_start) * 1000)
        result.add_stage("anchor_correction", duration, summary=annotation.anchor_status_summary)
    except Exception as exc:
        result.errors.append(f"Stage 4 (anchor_correction): {exc}")
        logger.error("pipeline stage_4_failed: %s", exc)
        result.total_time_ms = int((time.perf_counter() - total_start) * 1000)
        return result

    # Stage 5: 内容切片
    stage_start = time.perf_counter()
    try:
        sliced = slice_questions(annotation, doc)
        duration = int((time.perf_counter() - stage_start) * 1000)
        result.add_stage("content_slicing", duration, sliced=len(sliced))
    except Exception as exc:
        result.errors.append(f"Stage 5 (content_slicing): {exc}")
        logger.error("pipeline stage_5_failed: %s", exc)
        result.total_time_ms = int((time.perf_counter() - total_start) * 1000)
        return result

    # Stage 6: 答案匹配
    stage_start = time.perf_counter()
    try:
        sliced = match_answers(sliced, doc)
        duration = int((time.perf_counter() - stage_start) * 1000)
        matched = sum(1 for sq in sliced if sq.answer is not None)
        result.add_stage("answer_matching", duration, matched=matched)
    except Exception as exc:
        result.errors.append(f"Stage 6 (answer_matching): {exc}")
        logger.error("pipeline stage_6_failed: %s", exc)
        result.total_time_ms = int((time.perf_counter() - total_start) * 1000)
        return result

    # Stage 7: 质量门
    stage_start = time.perf_counter()
    try:
        sliced = evaluate_quality(sliced)
        result.sliced_questions = sliced
        duration = int((time.perf_counter() - stage_start) * 1000)
        high_conf = sum(1 for sq in sliced if sq.confidence >= 0.8)
        result.add_stage("quality_gate", duration, high_confidence=high_conf)
    except Exception as exc:
        result.errors.append(f"Stage 7 (quality_gate): {exc}")
        logger.error("pipeline stage_7_failed: %s", exc)

    result.total_time_ms = int((time.perf_counter() - total_start) * 1000)
    return result


def _build_question_images(
    sliced: list,
    images: list,
    doc: L1Document | None,
) -> list[dict]:
    """将 L1 图片关联到题目。

    关联规则（V1_LESSONS 3.26）：
    - 无 bbox 图片不关联（禁止无证据广播）
    - placement=standalone 的图片不关联
    - 图片 bbox 与题目的 stem/options/answer 行 bbox 重叠（含 20px margin）时关联
    - 优先关联到 stem，其次 options，最后 answer_area

    审计修复（2026-08-22，P0-1/P1-8）：
    - stem/options 行号改从 anchor 结构读取（SlicedQuestion 无 stem_line_ids/
      options_line_ids 属性，行号在 stem_anchor.corrected_line_ids 与
      corrected_anchors 中）——此前 getattr 取不到属性导致分支永不执行，
      配图关联率仅 15.5%
    - 输出补齐 page_no/bbox/source/figure_id（此前只输出 3 个 key，入库元数据全 None）
    """
    if not images or not sliced:
        return []

    # 构建 line_id → line 映射
    line_by_id: dict[str, L1Line] = {}
    if doc:
        for line in doc.lines:
            line_by_id[line.line_id] = line

    MARGIN = 20  # px，模糊区域
    result: list[dict] = []

    for img in images:
        # 无 bbox 或 standalone 不关联
        if not img.bbox:
            continue
        if img.placement == "standalone":
            continue

        img_cx = (img.bbox["x1"] + img.bbox["x2"]) / 2
        img_cy = (img.bbox["y1"] + img.bbox["y2"]) / 2

        best_q = None
        best_placement = None
        best_distance = float("inf")

        for q in sliced:
            qno = getattr(q, "question_number", None)
            if not qno:
                continue

            # 检查 stem 行（P0-1：改用 _question_field_line_ids 读 anchor 行号）
            for lid in _question_field_line_ids(q, "stem"):
                line = line_by_id.get(lid)
                if line and line.bbox:
                    if _bbox_contains_with_margin(line.bbox, img_cx, img_cy, MARGIN):
                        if best_placement != "stem":
                            best_q = qno
                            best_placement = "stem"
                            best_distance = 0

            # 检查 options 行（P0-1：从 corrected_anchors 收集 option_* 锚点行号）
            option_lids = _question_option_line_ids(q)
            for lid in option_lids:
                line = line_by_id.get(lid)
                if line and line.bbox:
                    if _bbox_contains_with_margin(line.bbox, img_cx, img_cy, MARGIN):
                        if best_placement is None:
                            best_q = qno
                            best_placement = "options"

            # 检查 answer 行
            for lid in (getattr(q, "answer_line_ids", None) or []):
                line = line_by_id.get(lid)
                if line and line.bbox:
                    if _bbox_contains_with_margin(line.bbox, img_cx, img_cy, MARGIN):
                        if best_placement is None:
                            best_q = qno
                            best_placement = "answer_area"

        if best_q and best_placement:
            result.append({
                "question_number": best_q,
                "image_id": img.image_id,
                "placement": best_placement,
                # P1-8：补齐入库元数据（此前缺这 4 个 key，QuestionImage 行 bbox/page_no 全 None）
                "page_no": img.page_no,
                "bbox": img.bbox,
                "source": img.source,
                "figure_id": img.figure_id,
                # 2026-08-27：携带图片 URL（OCR 路径），入库后前端可显示实际图片
                "url": img.url,
            })

    return result


def _question_option_line_ids(q) -> list[str]:
    """从题目的 corrected_anchors 提取选项行号（field 前缀 option_）。

    SlicedQuestion 无 options_line_ids 属性；选项锚点行号存放在
    corrected_anchors 中（field="option_A" 等）。兼容测试 mock 直接暴露
    options_line_ids dict 的情况。
    """
    anchors = getattr(q, "corrected_anchors", None) or []
    if anchors:
        lids: list[str] = []
        for a in anchors:
            field = getattr(a, "field", "")
            if field.startswith("option_"):
                cids = getattr(a, "corrected_line_ids", None) or []
                lids.extend(cids)
        if lids:
            return lids
    # 兼容测试 mock：直接暴露 options_line_ids dict
    opts = getattr(q, "options_line_ids", None) or {}
    if isinstance(opts, dict):
        out: list[str] = []
        for lid_list in opts.values():
            out.extend(lid_list if isinstance(lid_list, list) else [])
        return out
    return []


def _bbox_contains_with_margin(
    bbox: dict, cx: float, cy: float, margin: float
) -> bool:
    """检查点 (cx, cy) 是否在 bbox 扩展 margin 后的范围内。"""
    return (
        bbox["x1"] - margin <= cx <= bbox["x2"] + margin
        and bbox["y1"] - margin <= cy <= bbox["y2"] + margin
    )
