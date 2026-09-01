"""LLM Prompt 模块化注册表。

将巨型 Prompt 拆分为可组合模块：
- base：总则（JSON 输出、行号规范、难度等）
- subjects：科目专用规则（英语、数学、语文等）
- examples：golden 示例（用示例代替长篇解释）

组装方式：base + subject_rules + examples + retry_hints + 文档行
仍然单次 LLM 调用，不增加调用次数。
"""

from .registry import PromptRegistry, PromptModule
from .router import LLMRouter

__all__ = ["PromptRegistry", "PromptModule", "LLMRouter"]
