"""管线共享内核 — 生产代码从这里导入共享符号。

2026-08-27（P2 Pipeline 共享内核拆分，方案 A）：从 pipeline.py 拆出
PipelineResult + save_result + 题目配图/序列化 helper，供生产三文件
（simple_pipeline / processor / ingestion）与 pipeline.py 共用。

约束（审计决策）：
- **无循环依赖**：本模块不 import pipeline；pipeline.py 通过 re-export
  兼容 legacy 测试与旧调用（生产代码禁止从 pipeline 导入共享符号）。
- 不进 shared：extract_l1_from_pdf/ocr（legacy 测试面，等删除时处理）、
  run_pipeline、_merge_dual_source 等双源仲裁逻辑留在 pipeline.py。
- 测试零改动：pipeline.py 顶部 re-export 全部共享符号。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.domains.document.schemas_l1 import L1Document, L1Line
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
                        # P4E.1（2026-08-27）：补子题行号 + 切片文本。
                        # 此前只输出 qno/type/answer/kp/score，子题 stem/options
                        # 行号与文本在 to_dict 处丢失（LOG v6.43 链路断裂 #2）。
                        "stem_line_ids": getattr(sq_sub, "stem_line_ids", None) or [],
                        "options_line_ids": getattr(sq_sub, "options_line_ids", None) or {},
                        "stem": getattr(sq_sub, "stem", "") or "",
                        "options": getattr(sq_sub, "options", None) or [],
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
                # P4E.1（2026-08-27）：必须同页才可能关联——此前缺 page 约束，
                # 不同页的 bbox 是页内相对坐标，数值碰巧重叠即误关联
                # （八中数学 Q1 关联到第 8 页的 P8IMG001，页眉页脚横条混入，
                # LOG v6.43）。
                if line and line.bbox and line.page_no == img.page_no:
                    if _bbox_contains_with_margin(line.bbox, img_cx, img_cy, MARGIN):
                        if best_placement != "stem":
                            best_q = qno
                            best_placement = "stem"
                            best_distance = 0

            # 检查 options 行（P0-1：从 corrected_anchors 收集 option_* 锚点行号）
            option_lids = _question_option_line_ids(q)
            for lid in option_lids:
                line = line_by_id.get(lid)
                if line and line.bbox and line.page_no == img.page_no:
                    if _bbox_contains_with_margin(line.bbox, img_cx, img_cy, MARGIN):
                        if best_placement is None:
                            best_q = qno
                            best_placement = "options"

            # 检查 answer 行
            for lid in (getattr(q, "answer_line_ids", None) or []):
                line = line_by_id.get(lid)
                if line and line.bbox and line.page_no == img.page_no:
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
