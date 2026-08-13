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

from app.ai.gateway import LLMGateway
from app.domains.document.answer_matcher import match_answers
from app.domains.document.anchor_corrector import correct_anchors
from app.domains.document.content_slicer import slice_questions
from app.domains.document.l1_arbiter import arbitrate_lines, apply_arbitration
from app.domains.document.line_annotator import annotate_document
from app.domains.document.native_markdown import extract_l1_from_pdf
from app.domains.document.ppsv3_l1 import extract_l1_from_ocr
from app.domains.document.ocr.providers import build_ocr_chain
from app.domains.document.quality_gate import evaluate_quality
from app.domains.document.schemas_l1 import L1Document, L1Line, L1Page
from app.domains.document.schemas_l2 import L2DocumentAnnotation, SlicedQuestion

logger = logging.getLogger(__name__)


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
    from app.domains.document.l1_postprocessor import postprocess_l1

    # 后处理两个 L1
    native_processed = postprocess_l1(native_doc)
    ppsv3_processed = postprocess_l1(ppsv3_doc)

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

    # 构建 native line_id 索引（primary 匹配策略）
    nat_by_orig_line_id: dict[str, L1Line] = {}
    for orig_line in native_doc.lines:
        best_proc = None
        best_sim = 0.0
        for proc_line in native_processed.lines:
            if proc_line.page_no != orig_line.page_no:
                continue
            sim = _text_similarity(orig_line.text, proc_line.text)
            if sim > best_sim:
                best_sim = sim
                best_proc = proc_line
        # 只在相似度 > 0.3 时才匹配（避免不同内容被错误绑定）
        if best_proc and best_sim > 0.3:
            nat_by_orig_line_id[orig_line.line_id] = best_proc

    merged_lines: list[L1Line] = []
    for orig_pp_line in ppsv3_doc.lines:
        # 在 postprocessed PP lines 中找到对应的行
        line = None
        for proc_line in ppsv3_processed.lines:
            if proc_line.page_no == orig_pp_line.page_no and proc_line.text.strip() == orig_pp_line.text.strip():
                line = proc_line
                break
        if line is None:
            continue

        pp_type = _detect_line_type(line.text)

        # Primary 策略：按原始 line_id 精确匹配（两个源共享 line_id 时最优）
        # 但必须验证 PP 和 native 文本内容相似，避免不同切分的行被错误绑定
        nat_match = nat_by_orig_line_id.get(orig_pp_line.line_id)
        if nat_match and _text_similarity(line.text, nat_match.text) > 0.3:
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

        # 验证语义绑定
        if best_match and best_score > 0.3:
            if _validate_semantic_binding(line.text, best_match.text, pp_type):
                raw_sources = {"ppsv3": line.text, "native": best_match.text}
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
        if "native" in raw:
            nat_text = raw["native"]
            for nat_line in native_processed.lines:
                if nat_line.text.strip() == nat_text.strip():
                    merged_nat_ids.add(nat_line.line_id)
                    break
    native_only_count = sum(1 for l in native_processed.lines if l.line_id not in merged_nat_ids)
    if native_only_count > 0:
        logger.info("merge: %d native-only lines not in PP (not added to preserve line numbering)", native_only_count)

    return L1Document(
        filename=ppsv3_doc.filename, pages=ppsv3_processed.pages,
        lines=merged_lines, images=ppsv3_doc.images,
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


class PipelineResult:
    """管线执行结果。"""

    def __init__(self) -> None:
        self.stages: list[dict] = []
        self.l1_document: L1Document | None = None
        self.l2_annotation: L2DocumentAnnotation | None = None
        self.sliced_questions: list[SlicedQuestion] = []
        self.errors: list[str] = []
        self.total_time_ms: int = 0

    def add_stage(self, name: str, duration_ms: int, **info) -> None:
        self.stages.append({
            "name": name,
            "duration_ms": duration_ms,
            **info,
        })

    def to_dict(self) -> dict:
        return {
            "stages": self.stages,
            "total_time_ms": self.total_time_ms,
            "errors": self.errors,
            "question_count": len(self.sliced_questions),
            "questions": [
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
                    "answer_line_ids": sq.answer_line_ids,
                    "explanation_line_ids": sq.explanation_line_ids,
                    "answer_provenance": _provenance_to_dict(sq.answer_provenance),
                    "explanation_provenance": _provenance_to_dict(sq.explanation_provenance),
                    "corrected_anchors": [_anchor_to_dict(a) for a in sq.corrected_anchors],
                    "issues": sq.issues,
                }
                for sq in self.sliced_questions
            ],
        }


async def run_pipeline(
    pdf_path: Path | None = None,
    *,
    filename: str | None = None,
    gateway: LLMGateway,
    page_range: tuple[int, int] | None = None,
    ppsv3_doc: L1Document | None = None,
    native_doc: L1Document | None = None,
) -> PipelineResult:
    """执行完整的文档处理管线。

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
            ppsv3_doc = extract_l1_from_ocr(ocr_doc, filename=filename)
            duration = int((time.perf_counter() - ocr_start) * 1000)
            result.add_stage("ppsv3_l1", duration, lines=len(ppsv3_doc.lines))
        except Exception as exc:
            logger.warning("ppsv3_l1 failed: %s", exc)
    else:
        result.add_stage("ppsv3_l1", 0, note="pre-computed", lines=len(ppsv3_doc.lines))

    # 按 page_range 过滤（预计算文档可能包含全部页面）
    if native_doc and page_range:
        native_doc = _filter_by_page_range(native_doc, page_range)
    if ppsv3_doc and page_range:
        ppsv3_doc = _filter_by_page_range(ppsv3_doc, page_range)

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


def save_result(result: PipelineResult, output_path: Path) -> None:
    """保存管线结果到 JSON 文件。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("pipeline result saved to %s", output_path)
