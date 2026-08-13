"""
LLM 行号标注器 — L1Document → L2DocumentAnnotation。

LLM 只输出行号引用和元数据，不输出题目内容文本。
Prompt 只要求：question_number, question_type, section_id,
stem_line_ids, options_line_ids, difficulty, score, knowledge_points。

详见 Docs/01_Product/T3_IMPLEMENTATION.md §8 Task 1.2。
遵守 V1_LESSONS 3.1/3.16（不输出 LaTeX 题干/选项/答案/解析原文）。
"""

from __future__ import annotations

import json
import logging

from app.ai.gateway import LLMGateway
from app.ai.json_utils import parse_json_object
from app.domains.document.schemas_l1 import L1Document
from app.domains.document.schemas_l2 import L2DocumentAnnotation, L2QuestionAnnotation

logger = logging.getLogger(__name__)

# 标注 Prompt 模板
ANNOTATION_PROMPT = """你是一个试卷文档标注助手。给定一份试卷的文本行（带行号），请识别所有题目并输出标注结果。

## 规则
1. 每个题目必须包含：question_number, question_type, section_id, stem_line_ids, options_line_ids；question_type 使用 canonical 枚举：single_choice / multiple_choice / fill_in / true_false / short_answer
2. 可选字段：difficulty(1-5), score, knowledge_points
3. options_line_ids 的 key 是选项标签（A/B/C/D），value 是该选项所在的行号列表
4. 填空题和解答题的 options_line_ids 为空对象 {{}}
5. 共享材料题（如完形填空）用 section_id 标识共享材料范围
6. 行号必须是文档中实际存在的行号（格式 P{{page}}L{{line:03d}}）
7. 不要输出答案或详解内容，只输出行号引用

## 输出格式
严格输出 JSON 对象，不要输出其他内容：
```json
{{
  "filename": "文档文件名",
  "subject": "科目",
  "questions": [
    {{
      "question_number": "1",
      "question_type": "single_choice",
      "section_id": "选择题",
      "stem_line_ids": ["P1L003"],
      "options_line_ids": {{
        "A": ["P1L004"],
        "B": ["P1L005"],
        "C": ["P1L006"],
        "D": ["P1L007"]
      }},
      "difficulty": 2,
      "score": 5.0,
      "knowledge_points": ["函数"]
    }}
  ],
  "metadata_confidence": 0.8,
  "warnings": []
}}
```

## 文档内容
文件名: {filename}

{text_lines}
"""


def build_annotation_prompt(doc: L1Document) -> str:
    """构建标注 Prompt。

    将 L1 文档的行文本格式化为带行号的列表，发送给 LLM。
    """
    text_lines = []
    for line in doc.lines:
        text_lines.append(f"[{line.line_id}] {line.text}")

    return ANNOTATION_PROMPT.format(
        filename=doc.filename,
        text_lines="\n".join(text_lines),
    )


async def annotate_document(
    doc: L1Document,
    gateway: LLMGateway,
    *,
    temperature: float = 0.2,
) -> L2DocumentAnnotation:
    """用 LLM 标注文档中的题目。

    Args:
        doc: L1 文档
        gateway: LLM 网关
        temperature: 生成温度

    Returns:
        L2DocumentAnnotation：标注结果
    """
    prompt = build_annotation_prompt(doc)

    # 调用 LLM
    response_text = await gateway.complete(prompt, temperature=temperature)

    # 解析 JSON
    parsed = parse_json_object(response_text)

    # 构建 L2DocumentAnnotation
    questions: list[L2QuestionAnnotation] = []
    valid_line_ids = {l.line_id for l in doc.lines}

    for q_data in parsed.get("questions", []):
        # 验证行 ID 有效性
        stem_ids = _validate_line_ids(
            q_data.get("stem_line_ids", []), valid_line_ids, "stem"
        )
        options_ids = {}
        for opt, lids in q_data.get("options_line_ids", {}).items():
            options_ids[opt] = _validate_line_ids(
                lids, valid_line_ids, f"option {opt}"
            )

        question = L2QuestionAnnotation(
            question_number=str(q_data.get("question_number", "")),
            question_type=q_data.get("question_type", "unknown"),
            section_id=q_data.get("section_id"),
            stem_line_ids=stem_ids,
            options_line_ids=options_ids,
            difficulty=q_data.get("difficulty"),
            score=q_data.get("score"),
            knowledge_points=q_data.get("knowledge_points", []),
            confidence=q_data.get("confidence", 0.5),
            source_page=_get_source_page(stem_ids),
        )
        questions.append(question)

    return L2DocumentAnnotation(
        filename=doc.filename,
        subject=parsed.get("subject"),
        grade=parsed.get("grade"),
        year=parsed.get("year"),
        school=parsed.get("school"),
        questions=questions,
        metadata_confidence=parsed.get("metadata_confidence", 0.5),
        warnings=parsed.get("warnings", []),
    )


def _validate_line_ids(
    line_ids: list[str], valid_ids: set[str], field_name: str
) -> list[str]:
    """验证行 ID 有效性，过滤无效 ID。"""
    valid = []
    for lid in line_ids:
        if lid in valid_ids:
            valid.append(lid)
        else:
            logger.warning(
                "invalid_line_id field=%s line_id=%s", field_name, lid
            )
    return valid


def _get_source_page(line_ids: list[str]) -> int | None:
    """从行 ID 列表推断起始页码。"""
    if not line_ids:
        return None
    first_id = line_ids[0]
    # P1L001 → 1
    try:
        page_str = first_id.split("L")[0][1:]
        return int(page_str)
    except (IndexError, ValueError):
        return None
