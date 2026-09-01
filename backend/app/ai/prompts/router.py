"""LLM 路由器 — 根据科目选择 Prompt 模块并组装。

设计原则：
- 只负责"选模块"，不做多步串行 LLM
- 仍然单次调用，不增加调用次数
- 复用现有 pipeline，不改输出契约
"""

from __future__ import annotations

import logging

from .registry import PromptRegistry

logger = logging.getLogger(__name__)


class LLMRouter:
    """LLM 路由器 — 根据科目选择 Prompt 模块。"""

    def __init__(self, registry: PromptRegistry | None = None):
        self.registry = registry or PromptRegistry()

    def detect_subject(
        self,
        filename: str | None = None,
        metadata_subject: str | None = None,
        text_lines: str | None = None,
    ) -> str:
        """识别科目。

        优先级：
        1. 文档元数据（上传时指定）
        2. 文件名解析
        3. 内容推断（最后手段）
        """
        # 1. 元数据优先
        if metadata_subject and metadata_subject.strip():
            return metadata_subject.strip()

        # 2. 文件名解析
        if filename:
            subject = self._extract_subject_from_filename(filename)
            if subject:
                return subject

        # 3. 内容推断（简单规则）
        if text_lines:
            subject = self._infer_subject_from_content(text_lines)
            if subject:
                return subject

        return "未知"

    def _extract_subject_from_filename(self, filename: str) -> str | None:
        """从文件名提取科目。"""
        subject_keywords = {
            "英语": ["英语", "English", "ENG"],
            "数学": ["数学", "Mathematics", "MATH"],
            "语文": ["语文", "Chinese", "CHN"],
            "物理": ["物理", "Physics", "PHYS"],
            "化学": ["化学", "Chemistry", "CHEM"],
            "生物": ["生物", "Biology", "BIO"],
            "政治": ["政治", "Politics", "POLI"],
            "历史": ["历史", "History", "HIST"],
            "地理": ["地理", "Geography", "GEOG"],
        }

        filename_lower = filename.lower()
        for subject, keywords in subject_keywords.items():
            if any(kw.lower() in filename_lower for kw in keywords):
                return subject

        return None

    def _infer_subject_from_content(self, text_lines: str) -> str | None:
        """从内容推断科目（最后手段）。"""
        # 只检查前 50 行，避免处理整份文档
        lines = text_lines.split("\n")[:50]
        text = "\n".join(lines)

        # 英语特征词
        english_keywords = ["完形填空", "阅读理解", "七选五", "语法填空", "书面表达", "Cloze", "Reading"]
        if any(kw in text for kw in english_keywords):
            return "英语"

        # 数学特征词
        math_keywords = ["函数", "导数", "三角", "数列", "概率", "立体几何", "解析几何"]
        if any(kw in text for kw in math_keywords):
            return "数学"

        # 语文特征词
        chinese_keywords = ["现代文阅读", "文言文", "古诗", "默写", "写作"]
        if any(kw in text for kw in chinese_keywords):
            return "语文"

        # 物理特征词
        physics_keywords = ["力学", "电学", "电磁感应", "实验题", "计算题"]
        if any(kw in text for kw in physics_keywords):
            return "物理"

        # 化学特征词
        chemistry_keywords = ["化学方程式", "有机化学", "无机化学", "工艺流程"]
        if any(kw in text for kw in chemistry_keywords):
            return "化学"

        return None

    def build_prompt(
        self,
        filename: str,
        text_lines: str,
        subject: str | None = None,
        metadata_subject: str | None = None,
        retry_hints: list[str] | None = None,
    ) -> tuple[str, str]:
        """构建 Prompt 并返回 (subject, prompt)。

        Returns:
            tuple: (识别的科目, 组装后的 Prompt)
        """
        # 识别科目
        detected_subject = self.detect_subject(
            filename=filename,
            metadata_subject=metadata_subject,
            text_lines=text_lines,
        )

        # 使用指定科目或识别的科目
        final_subject = subject or detected_subject

        # 组装 Prompt
        prompt = self.registry.build_annotation_prompt(
            filename=filename,
            text_lines=text_lines,
            subject=final_subject,
            retry_hints=retry_hints,
        )

        logger.info(
            "Built prompt: subject=%s, length=%d chars",
            final_subject,
            len(prompt),
        )

        return final_subject, prompt
