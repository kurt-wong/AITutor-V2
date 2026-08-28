"""PP 主路径实验管线 — 不做逐行双源 LLM 仲裁。

设计目标：
- PP markdown 是 canonical 正文源
- native 只作证据补充（图片 bbox、答案表定位、PP 空行兜底）
- LLM 只做一次语义提取，输出题目/答案/详解的行号 refs
- 代码从 PP/native 原文切片，不依赖 LLM 抄写内容

当前实现仍复用现有 annotate/correct/slice/answer/quality 资产，
但跳过 l1_arbiter 和双源逐行合并仲裁，作为可回滚的实验路径。
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path

from app.domains.document.anchor_corrector import (
    _build_question_start_map,
    correct_anchors,
)
from app.domains.document.answer_matcher import match_answers
from app.domains.document.content_slicer import slice_questions
from app.domains.document.image_deduplicator import deduplicate_images
from app.domains.document.line_annotator import annotate_document
from app.domains.document.native_markdown import (
    extract_l1_from_docx,
    extract_l1_from_pdf,
)
from app.domains.document.ocr.providers import build_ocr_chain
from app.domains.document.pipeline_shared import (
    PipelineResult,
    _build_question_images,
    _filter_by_page_range,
)
from app.domains.document.ppsv3_l1 import extract_l1_from_ocr
from app.domains.document.quality_gate import evaluate_quality
from app.domains.document.schemas_l1 import L1Document, L1Line

logger = logging.getLogger(__name__)

_ANSWER_SECTION_RE = re.compile(r"(参考答案|答案|Answer\s*Key)", re.IGNORECASE)

# OCR 学科路由：公式密集科目用 PaddleOCR-VL-1.6，其余用 PP-StructureV3
# 详见 V1_LESSONS 3.30
# 分析结论（2026-08-18）：只有化学公式占比42.9%+选项标签问题需要VL
# 生物5.7%、地理0.3%、数学69.7%（但丢弃是解答题锚点问题非OCR）→ PPS足够
_SUBJECT_OCR_MODEL = {
    "化学": "PaddleOCR-VL-1.6",  # 公式密集+选项标签保留
}
_DEFAULT_OCR_MODEL = "PP-StructureV3"

_SUBJECT_RE = re.compile(
    r"(化学|生物|地理|语文|数学|英语|物理|历史|政治)"
)


def _extract_subject_from_filename(filename: str | None) -> str | None:
    """从文件名中提取科目名。

    只匹配考试试卷命名格式（含"期末/模拟/期中/高考/中考"等关键词），
    避免"化学老师批改.pdf"等非学科文件名误匹配。
    """
    if not filename:
        return None
    # 必须同时包含科目名和考试关键词，才认定为学科试卷
    m = _SUBJECT_RE.search(filename)
    if not m:
        return None
    subject = m.group(1)
    # 考试关键词（文件名中常见）
    exam_keywords = re.compile(r"(期末|模拟|期中|高考|中考|月考|联考|统考|测试|真题|教师版|学生版)")
    if exam_keywords.search(filename):
        return subject
    # 无考试关键词时，科目名在文件名开头或紧跟年份/地名，也认为是学科
    start_pos = m.start()
    if start_pos <= 6:  # 文件名前 6 字符内出现科目名
        return subject
    return None


def _ocr_model_for_subject(
    subject: str | None,
    *,
    override: str | None = None,
) -> str:
    """根据学科返回 OCR 模型名。

    Args:
        subject: 学科名（如"化学"）
        override: 显式覆盖（优先级最高），来自参数而非环境变量。
    """
    if override:
        return override
    # 环境变量覆盖（CLI 场景使用）
    env_override = os.environ.get("OCR_MODEL_OVERRIDE")
    if env_override:
        return env_override
    if subject and subject in _SUBJECT_OCR_MODEL:
        return _SUBJECT_OCR_MODEL[subject]
    return _DEFAULT_OCR_MODEL


def _actual_ocr_model(
    provider_name: str | None,
    routed_model: str | None,
) -> str | None:
    """返回实际完成 OCR 的提供方所用模型（T0-4 证据准确性）。

    路由模型（routed_model）是学科路由的期望模型；当链降级到 VL 提供方时，
    实际模型与路由模型不同，必须按胜出提供方返回真实模型。
    """
    from app.core.config import settings
    if provider_name == "paddleocr":
        return routed_model
    if provider_name == "mimo-vl":
        return settings.mimo_vl_model or None
    if provider_name == "deepseek-vl":
        return settings.deepseek_vl_model or None
    return routed_model


def _has_retryable_failures(sliced, doc: L1Document) -> bool:
    """判断当前结果是否值得触发一次 LLM 标注重试。"""
    for sq in sliced:
        if any("禁止自动发布" in i for i in (sq.issues or [])):
            return True
        if not (sq.answer or "").strip():
            return True
    try:
        expected = {str(q) for q in _build_question_start_map(doc)}
    except Exception:
        expected = set()
    if expected:
        present = {sq.question_number for sq in sliced}
        if expected - present:
            return True
    return False


def _build_retry_hints(sliced) -> list[str]:
    """把第一遍质量门失败项转成 LLM 可执行的 retry hints。

    只反馈结构性失败（题干/选项/答案锚点），避免把每道题所有细节都塞进
    第二遍 prompt；同一题的问题合并为一条，控制 token 开销。
    """
    hints: list[str] = []
    for sq in sliced:
        problem_parts: list[str] = []

        stem_status = sq.stem_anchor.anchor_status if sq.stem_anchor else "missing"
        if not (sq.stem or "").strip() or stem_status in ("retry", "missing"):
            problem_parts.append("题干行号未通过校验，请重新输出 stem_line_ids")

        missing_options: list[str] = []
        if sq.question_type in ("single_choice", "multiple_choice"):
            if sq.options_anchor is None and not sq.options:
                problem_parts.append(
                    "所有选项行号缺失，请重新输出 options_line_ids"
                )
            else:
                for anchor in (sq.corrected_anchors or []):
                    if not anchor.field.startswith("option_"):
                        continue
                    label = anchor.field.replace("option_", "")
                    if (
                        anchor.anchor_status in ("retry", "missing")
                        or not anchor.corrected_line_ids
                    ):
                        missing_options.append(label)
        if missing_options:
            problem_parts.append(
                f"选项 {'/'.join(sorted(missing_options))} 行号缺失或无效，"
                "请重新输出 options_line_ids"
            )

        if not (sq.answer or "").strip() and sq.answer_provenance:
            if sq.answer_provenance.source == "llm_fallback":
                problem_parts.append(
                    "答案未匹配到文档，请重新输出 answer_line_ids 或补全 answer"
                )

        if problem_parts:
            hints.append(f"题目 {sq.question_number}：{'；'.join(problem_parts)}")

    return hints[:20]


def _count_ingested(sliced) -> int:
    """统计达到可入库标准的题目数，与 PipelineResult.ingest_summary 口径一致。"""
    return sum(
        1 for sq in sliced
        if sq.confidence >= 0.8
        and not any("禁止自动发布" in i for i in (sq.issues or []))
        and (sq.stem or "").strip()
        and (sq.answer or "").strip()
    )


def _quality_score(sliced, doc: L1Document) -> tuple:
    """返回可比较的质量分数，越高越好。"""
    blocked = sum(
        1 for sq in sliced
        if any("禁止自动发布" in i for i in (sq.issues or []))
    )
    empty = sum(1 for sq in sliced if not (sq.answer or "").strip())
    try:
        expected = {str(q) for q in _build_question_start_map(doc)}
    except Exception:
        expected = set()
    present = {sq.question_number for sq in sliced}
    missing = len(expected - present) if expected else 0
    return (_count_ingested(sliced), -blocked, -empty, -missing)


def _select_better_result(
    prev_annotation,
    prev_sliced,
    retry_annotation,
    retry_sliced,
    doc: L1Document,
):
    """选择两遍结果中质量更好的一遍，避免重试导致质量倒退。"""
    prev_score = _quality_score(prev_sliced, doc)
    retry_score = _quality_score(retry_sliced, doc)
    if retry_score > prev_score:
        return retry_annotation, retry_sliced
    return prev_annotation, prev_sliced


def _build_pp_canonical(
    ppsv3_doc: L1Document,
    native_doc: L1Document | None,
) -> tuple[L1Document, dict]:
    """构建 PP canonical L1，并附加 native 证据。

    边界规则：
    - PP 非空：正文保留 PP，native 只写入 raw_sources 作为证据
    - PP 为空：用同页同行 native 文本兜底，并标记 native_fallback
    - 不逐行合并、不逐行 LLM 仲裁、不覆盖 PP 已有内容
    - canonical 行号保留 PP；native 行号只通过 raw_sources["native_line_id"] 溯源
    """
    native_by_key: dict[tuple[int, int], L1Line] = {}
    if native_doc:
        for line in native_doc.lines:
            native_by_key.setdefault((line.page_no, line.line_no_in_page), line)

    lines: list[L1Line] = []
    empty_filled = 0
    native_matched = 0
    for line in ppsv3_doc.lines:
        text = line.text
        source = "ppsv3"
        selected_source = "ppsv3"
        evidence = ""
        raw_sources = {"ppsv3": line.text}

        native = native_by_key.get((line.page_no, line.line_no_in_page))
        if native is not None:
            raw_sources["native"] = native.text
            raw_sources["native_line_id"] = native.line_id
            native_matched += 1
            if not (text or "").strip() and (native.text or "").strip():
                text = native.text
                source = "native"
                selected_source = "native"
                evidence = "native_fallback"
                empty_filled += 1

        lines.append(L1Line(
            line_id=line.line_id,
            page_no=line.page_no,
            line_no_in_page=line.line_no_in_page,
            order=line.order,
            text=text,
            block_type=line.block_type,
            bbox=line.bbox,
            source=source,
            continuation=line.continuation,
            raw_sources=raw_sources,
            selected_source=selected_source,
            evidence=evidence,
            confidence=1.0,
        ))

    stats = {
        "empty_pp_filled_by_native": empty_filled,
        "native_lines_matched": native_matched,
        "native_images": len(native_doc.images) if native_doc else 0,
        "native_answer_section_lines": (
            sum(1 for l in native_doc.lines if _ANSWER_SECTION_RE.search(l.text))
            if native_doc else 0
        ),
    }
    doc = L1Document(
        filename=ppsv3_doc.filename,
        pages=ppsv3_doc.pages,
        lines=lines,
        images=list(ppsv3_doc.images),
        source="ppsv3",
        total_pages=ppsv3_doc.total_pages,
        text_coverage=ppsv3_doc.text_coverage,
        raw_lines=ppsv3_doc.raw_lines,
    )
    return doc, stats


async def run_simple_pipeline(
    pdf_path: Path | None = None,
    *,
    filename: str | None = None,
    subject: str | None = None,
    ocr_model: str | None = None,
    gateway,
    page_range: tuple[int, int] | None = None,
    ppsv3_doc: L1Document | None = None,
    native_doc: L1Document | None = None,
    progress_callback=None,
) -> PipelineResult:
    """执行 PP 主路径实验管线，返回 PipelineResult。

    该路径不调用 l1_arbiter；现有 pipeline.py 保持不变，作为 fallback。

    Args:
        subject: 学科名（如"化学"），用于 OCR 模型路由。
                 为 None 时从 filename 自动提取；均无则用默认模型。
        ocr_model: 显式覆盖 OCR 模型（如"PaddleOCR-VL"），优先级最高。
    """
    # 学科识别：优先参数 > 文件名
    if subject is None:
        subject = _extract_subject_from_filename(filename)
    resolved_model = _ocr_model_for_subject(subject, override=ocr_model)
    if subject or ocr_model:
        logger.info(
            "ocr routing: subject=%s model=%s (override=%s)",
            subject, resolved_model, ocr_model,
        )
    result = PipelineResult()
    total_start = time.perf_counter()

    async def _emit_progress(stage: str, progress: float) -> None:
        if progress_callback is not None:
            try:
                await progress_callback(stage, progress)
            except Exception:
                logger.debug("progress_callback failed", exc_info=True)

    # 1. native 证据 L1
    is_docx = pdf_path is not None and pdf_path.suffix.lower() == ".docx"
    if is_docx:
        # DOCX 原生文本：python-docx 直接提取，不需要 OCR
        try:
            stage_start = time.perf_counter()
            native_doc = extract_l1_from_docx(
                pdf_path, filename=filename
            )
            result.add_stage(
                "native_l1",
                int((time.perf_counter() - stage_start) * 1000),
                lines=len(native_doc.lines),
            )
        except Exception as exc:
            result.status = "failed"
            result.errors.append(f"simple_pipeline docx_l1 failed: {exc}")
            return result
    elif native_doc is None and pdf_path is not None:
        try:
            stage_start = time.perf_counter()
            native_doc = extract_l1_from_pdf(
                pdf_path, filename=filename, page_range=page_range
            )
            result.add_stage(
                "native_l1",
                int((time.perf_counter() - stage_start) * 1000),
                lines=len(native_doc.lines),
            )
        except Exception as exc:
            logger.warning("simple_pipeline native_l1 failed: %s", exc)

    # 保存 native L1 到结果中（供后续入库持久化）
    if native_doc is not None:
        result.native_l1_document = native_doc

    # 2026-08-25 扫描件标注：纯扫描 PDF（无文本层，text_coverage 极低）
    # 的题号/公式区域 OCR 后不可靠（昌平生物 8 题题号被误读），换 OCR
    # 引擎亦无法解决（同一后端、题号印刷模糊）。此类样本少，先标注出来
    # 交由后续集中处理，不浪费 OCR/LLM token 跑一条注定质量差的管线。
    _SCANNED_TEXT_COVERAGE_THRESHOLD = 0.02
    if (
        not is_docx
        and native_doc is not None
        and native_doc.text_coverage < _SCANNED_TEXT_COVERAGE_THRESHOLD
    ):
        result.status = "scanned"
        result.errors.append(
            "scanned_pdf: 扫描版 PDF（无文本层），题号/公式 OCR 不可靠，"
            "暂不进入管线，后续集中处理"
        )
        logger.warning(
            "scanned_pdf detected: filename=%s text_coverage=%.4f",
            filename,
            native_doc.text_coverage,
        )
        return result

    # 2. PP canonical L1
    if is_docx:
        # DOCX 原生文本即 canonical（无 OCR；ppsv3_doc 复用 native 以通过
        # 后续非空检查与 merge——两者同一对象时 merge 无变化）。
        ppsv3_doc = native_doc
        result.ocr_provider_used = None
        result.ocr_model_used = None
    elif ppsv3_doc is None:
        if pdf_path is None:
            result.status = "failed"
            result.errors.append("simple_pipeline: no ppsv3_doc and no pdf_path")
            return result
        try:
            stage_start = time.perf_counter()
            ocr_chain = build_ocr_chain(model=resolved_model)
            try:
                ocr_doc = await ocr_chain.extract(pdf_path)
            finally:
                ocr_chain.close()
            # T0-4: OCR 提供方证据（task result 可审计"哪个提供方完成"）
            result.ocr_provider_used = ocr_doc.provider_used or result.ocr_provider_used
            result.ocr_model_used = _actual_ocr_model(
                result.ocr_provider_used, resolved_model,
            )
            ppsv3_doc = extract_l1_from_ocr(ocr_doc, filename=filename)
            result.add_stage(
                "ppsv3_l1",
                int((time.perf_counter() - stage_start) * 1000),
                lines=len(ppsv3_doc.lines),
                provider=result.ocr_provider_used,
                model=result.ocr_model_used,
            )
        except Exception as exc:
            # OCR 失败（2026-08-25 用户决策：不降级 LLM VL）。
            # 主识别 paddle（PPS/PVL）不可用 → 标记 ocr_unavailable，等待
            # paddle 恢复后重跑；错误信息保留供审计/批量恢复脚本识别。
            result.status = "failed"
            result.errors.append(f"simple_pipeline ppsv3_l1 failed (ocr_unavailable): {exc}")
            logger.warning("OCR failed, marked as ocr_unavailable: %s", exc)
            return result

    if page_range:
        if native_doc:
            native_doc = _filter_by_page_range(native_doc, page_range)
        ppsv3_doc = _filter_by_page_range(ppsv3_doc, page_range)

    if not ppsv3_doc or not ppsv3_doc.lines:
        result.status = "failed"
        result.errors.append("simple_pipeline: PP L1 is empty")
        return result

    stage_start = time.perf_counter()
    doc, evidence_stats = _build_pp_canonical(ppsv3_doc, native_doc)
    result.l1_document = doc
    result.add_stage(
        "pp_primary_l1",
        int((time.perf_counter() - stage_start) * 1000),
        lines=len(doc.lines),
        **evidence_stats,
    )
    await _emit_progress("l1_generation", 0.3)

    # 3. 图片去重
    if doc.images:
        try:
            stage_start = time.perf_counter()
            dedup_images, dedup_result = deduplicate_images(doc.images)
            doc.images = dedup_images
            result.add_stage(
                "image_dedup",
                int((time.perf_counter() - stage_start) * 1000),
                original_count=dedup_result.original_count,
                deduplicated_count=dedup_result.deduplicated_count,
            )
        except Exception as exc:
            result.add_stage("image_dedup", 0, error=str(exc))

    # 4-8. LLM 语义提取 + 确定性处理；有未入库/missing 时重试一次
    selected_annotation = None
    selected_sliced: list = []
    selected_pass_no = 0
    prev_annotation = None
    prev_sliced: list = []
    retry_hints: list[str] = []
    for pass_no in range(2):
        if pass_no == 0:
            await _emit_progress("llm_annotation", 0.4)
            stage_name = "llm_annotation"
            temperature = 0.0
        else:
            await _emit_progress("llm_annotation_retry", 0.45)
            stage_name = "llm_annotation_retry"
            temperature = 0.0
        try:
            stage_start = time.perf_counter()
            annotation = await annotate_document(
                doc,
                gateway,
                temperature=temperature,
                retry_hints=retry_hints,
            )
            result.l2_annotation = annotation
            result.add_stage(
                stage_name,
                int((time.perf_counter() - stage_start) * 1000),
                questions=len(annotation.questions),
                hint_count=len(retry_hints),
            )
        except Exception as exc:
            if pass_no == 0:
                result.status = "failed"
                result.errors.append(
                    f"simple_pipeline llm_annotation failed: {exc}"
                )
                return result
            logger.warning(
                "simple_pipeline llm_annotation_retry failed: %s", exc
            )
            break

        suffix = "" if pass_no == 0 else "_retry"
        try:
            # 锚点校正（仍复用确定性校正，不调用 LLM）
            await _emit_progress(f"anchor_correction{suffix}", 0.5)
            stage_start = time.perf_counter()
            annotation = correct_anchors(annotation, doc)
            result.add_stage(
                f"anchor_correction{suffix}",
                int((time.perf_counter() - stage_start) * 1000),
                summary=annotation.anchor_status_summary,
            )

            # 内容切片
            await _emit_progress(f"content_slicing{suffix}", 0.6)
            stage_start = time.perf_counter()
            sliced = slice_questions(annotation, doc)
            result.add_stage(
                f"content_slicing{suffix}",
                int((time.perf_counter() - stage_start) * 1000),
                sliced=len(sliced),
            )

            # 答案/详解匹配
            await _emit_progress(f"answer_matching{suffix}", 0.7)
            stage_start = time.perf_counter()
            sliced = match_answers(sliced, doc, llm_annotation=annotation)
            matched = sum(1 for sq in sliced if sq.answer is not None)
            result.add_stage(
                f"answer_matching{suffix}",
                int((time.perf_counter() - stage_start) * 1000),
                matched=matched,
            )

            # 质量门
            await _emit_progress(f"quality_gate{suffix}", 0.8)
            stage_start = time.perf_counter()
            sliced = evaluate_quality(sliced)
            result.sliced_questions = sliced
            high_conf = sum(1 for sq in sliced if sq.confidence >= 0.8)
            blocked = sum(
                1 for sq in sliced
                if any("禁止自动发布" in i for i in sq.issues)
            )
            result.add_stage(
                f"quality_gate{suffix}",
                int((time.perf_counter() - stage_start) * 1000),
                high_confidence=high_conf,
                blocked=blocked,
            )
        except Exception as exc:
            if pass_no == 0:
                result.status = "failed"
                result.errors.append(
                    f"simple_pipeline post_llm failed: {exc}"
                )
                return result
            logger.warning(
                "simple_pipeline retry post_llm failed: %s", exc
            )
            break

        if pass_no == 0:
            prev_annotation = annotation
            prev_sliced = sliced
            if _has_retryable_failures(sliced, doc):
                logger.info(
                    "simple_pipeline retry_triggered questions=%d",
                    len(sliced),
                )
                retry_hints = _build_retry_hints(sliced)
                selected_annotation = annotation
                selected_sliced = sliced
                selected_pass_no = 0
                continue
            selected_annotation = annotation
            selected_sliced = sliced
            selected_pass_no = 0
            break

        selected_annotation, selected_sliced = _select_better_result(
            prev_annotation,
            prev_sliced,
            annotation,
            sliced,
            doc,
        )
        selected_pass_no = 1 if selected_sliced is sliced else 0
        break

    annotation = selected_annotation
    sliced = selected_sliced
    result.l2_annotation = annotation
    result.sliced_questions = sliced
    selected_suffix = "" if selected_pass_no == 0 else "_retry"
    for stage in result.stages:
        if stage.get("name") in {
            f"llm_annotation{selected_suffix}",
            f"anchor_correction{selected_suffix}",
            f"content_slicing{selected_suffix}",
            f"answer_matching{selected_suffix}",
            f"quality_gate{selected_suffix}",
        }:
            stage["selected"] = True

    # 9. 题-图关联
    await _emit_progress("question_images", 0.9)
    stage_start = time.perf_counter()
    result.question_images = _build_question_images(sliced, doc.images, doc)
    result.add_stage(
        "question_images",
        int((time.perf_counter() - stage_start) * 1000),
    )

    result.total_time_ms = int((time.perf_counter() - total_start) * 1000)
    return result
