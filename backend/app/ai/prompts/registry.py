"""Prompt 注册表 — 管理和组装 Prompt 模块。

设计原则：
- base：总则，所有科目共享
- subjects：科目专用规则，按需加载
- examples：golden 示例，用示例代替长篇解释
- 组装后仍然单次 LLM 调用，不增加调用次数
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 模块根目录
_MODULE_DIR = Path(__file__).parent
_EXAMPLES_DIR = _MODULE_DIR / "examples"


@dataclass
class PromptModule:
    """Prompt 模块基类。"""
    name: str
    version: str
    description: str

    def get_rules(self) -> str:
        """获取模块规则文本。"""
        raise NotImplementedError


class PromptRegistry:
    """Prompt 注册表 — 管理所有 Prompt 模块。"""

    def __init__(self):
        self._base_modules: dict[str, PromptModule] = {}
        self._subject_modules: dict[str, PromptModule] = {}
        self._examples: dict[str, list[dict]] = {}
        self._load_modules()

    def _load_modules(self) -> None:
        """加载所有模块。"""
        # 延迟导入避免循环依赖
        from .base import (
            json_output_rules,
            line_id_rules,
            difficulty_rules,
            composite_rules,
            answer_rules,
        )
        from .subjects import (
            english_rules,
            math_rules,
            chinese_rules,
            science_rules,
            generic_rules,
        )

        # 注册基础模块
        self._base_modules["json_output"] = json_output_rules
        self._base_modules["line_id"] = line_id_rules
        self._base_modules["difficulty"] = difficulty_rules
        self._base_modules["composite"] = composite_rules
        self._base_modules["answer"] = answer_rules

        # 注册科目模块
        self._subject_modules["英语"] = english_rules
        self._subject_modules["数学"] = math_rules
        self._subject_modules["语文"] = chinese_rules
        self._subject_modules["物理"] = science_rules
        self._subject_modules["化学"] = science_rules
        self._subject_modules["生物"] = science_rules
        self._subject_modules["政治"] = generic_rules
        self._subject_modules["历史"] = generic_rules
        self._subject_modules["地理"] = generic_rules
        self._subject_modules["未知"] = generic_rules

        # 加载示例
        self._load_examples()

        logger.info(
            "PromptRegistry loaded: %d base modules, %d subject modules, %d example sets",
            len(self._base_modules),
            len(self._subject_modules),
            len(self._examples),
        )

    def _load_examples(self) -> None:
        """加载 golden 示例。"""
        if not _EXAMPLES_DIR.exists():
            return

        for example_file in _EXAMPLES_DIR.glob("*.json"):
            try:
                data = json.loads(example_file.read_text(encoding="utf-8"))
                subject = data.get("subject", "unknown")
                self._examples[subject] = data.get("examples", [])
            except Exception as e:
                logger.warning("Failed to load examples from %s: %s", example_file, e)

    def get_subject_module(self, subject: str) -> PromptModule:
        """获取科目专用模块。"""
        return self._subject_modules.get(subject, self._subject_modules["未知"])

    def get_examples(self, subject: str) -> list[dict]:
        """获取科目的 golden 示例。"""
        return self._examples.get(subject, [])

    def build_annotation_prompt(
        self,
        filename: str,
        text_lines: str,
        subject: str | None = None,
        retry_hints: list[str] | None = None,
    ) -> str:
        """组装完整的标注 Prompt。

        组装顺序：
        1. base 规则（JSON 输出、行号、难度、综合题、答案）
        2. 科目专用规则
        3. golden 示例
        4. 重试提示（如果有）
        5. 文档内容
        """
        parts = []

        # 1. 基础规则
        parts.append("你是一个试卷文档标注助手。给定一份试卷的文本行（带行号），请识别所有题目并输出标注结果。")
        parts.append("")

        # 2. 各基础模块规则
        parts.append("## 规则")
        for module in self._base_modules.values():
            parts.append(module.get_rules())
            parts.append("")

        # 3. 科目专用规则
        if subject:
            subject_module = self.get_subject_module(subject)
            parts.append(f"## {subject}专用规则")
            parts.append(subject_module.get_rules())
            parts.append("")

        # 4. golden 示例
        examples = self.get_examples(subject or "未知")
        if examples:
            parts.append("## 示例")
            for i, example in enumerate(examples[:2], 1):  # 最多2个示例
                parts.append(f"### 示例 {i}: {example.get('description', '')}")
                parts.append("输入:")
                parts.append(f"```\n{example.get('input', '')}\n```")
                parts.append("输出:")
                parts.append(f"```json\n{json.dumps(example.get('output', {}), ensure_ascii=False, indent=2)}\n```")
                parts.append("")

        # 5. 重试提示
        if retry_hints:
            parts.append("## 上一轮标注问题（必须修正）")
            parts.append("以下题目在上轮标注中未通过校验。请只修正这些问题对应的行号或字段，不要遗漏，也不要虚构不存在的行号。")
            for hint in retry_hints:
                parts.append(f"- {hint}")
            parts.append("")

        # 6. 文档内容
        parts.append("## 文档内容")
        parts.append(f"文件名: {filename}")
        parts.append("")
        parts.append(text_lines)

        return "\n".join(parts)
