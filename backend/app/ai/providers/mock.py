"""Mock LLM provider for testing.

Returns pre-configured responses. For eval mode, supports both:
- Annotation prompts → golden annotation JSON
- Arbitration prompts → proper audit format with line_id/selected_source
"""

from __future__ import annotations

import json
import re

from app.ai.providers.base import LLMProvider


class MockLLMProvider(LLMProvider):
    name = "mock"

    def __init__(self, response: str | None = None) -> None:
        self.response = response or "MOCK_LLM_RESPONSE"

    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        # 检测仲裁 prompt：包含 "document parsing arbiter" 或 "selected_source"
        if "document parsing arbiter" in prompt or '"selected_source"' in prompt:
            return self._mock_arbitrate(prompt)
        return self.response

    async def complete_vision(
        self,
        prompt: str,
        image_data_url: str,
        *,
        temperature: float = 0.2,
    ) -> str:
        return self.response

    def _mock_arbitrate(self, prompt: str) -> str:
        """解析仲裁 prompt 中的输入行，返回正确的审计格式。

        规则（遵循新仲裁契约）：
        - PP-StructureV3 是默认基座，优先选 PP
        - 公式/符号行（含 LaTeX、$、\\）→ 选 ppsv3
        - 纯文本行也选 ppsv3（默认基座）
        - 两源文本完全相同 → conflict_type="equivalent"
        - Native 更完整（PP 截断）→ 选 native, conflict_type="complementary"
        - Native 部分内容 → 选 PP, conflict_type="partial"
        """
        # 从 prompt 中提取 JSON 输入块
        # 格式: "Input:\n[{...}, {...}]"
        input_match = re.search(r'Input:\n(\[.*\])', prompt, re.DOTALL)
        if not input_match:
            return "[]"

        try:
            inputs = json.loads(input_match.group(1))
        except json.JSONDecodeError:
            return "[]"

        results = []
        for item in inputs:
            line_id = item.get("line_id", "")
            native_text = item.get("native", "")
            ppsv3_text = item.get("ppsv3", "")
            block_type = item.get("block_type", "text")

            # 判断冲突类型
            if native_text.strip() == ppsv3_text.strip():
                conflict_type = "equivalent"
                selected = "ppsv3"
                evidence = "两源内容相同，默认选 PP"
            else:
                # 检查 native 是否更完整（包含 PP 缺失的内容）
                pp_opts = set(re.findall(r'[（(]\s*([A-D])\s*[）)]', ppsv3_text))
                nat_opts = set(re.findall(r'[（(]\s*([A-D])\s*[）)]', native_text))
                pp_qnums = set(re.findall(r'[（(]\s*(\d+)\s*[）)]\s*[A-D]', ppsv3_text))
                nat_qnums = set(re.findall(r'[（(]\s*(\d+)\s*[）)]\s*[A-D]', native_text))

                if pp_opts and pp_opts.issubset(nat_opts) and len(nat_opts) > len(pp_opts):
                    conflict_type = "complementary"
                    selected = "native"
                    evidence = "Native 包含 PP 缺失的选项"
                elif pp_qnums and not pp_qnums.issubset(nat_qnums):
                    conflict_type = "partial"
                    selected = "ppsv3"
                    evidence = "Native 缺少 PP 的部分答案条目"
                elif len(native_text.strip()) > len(ppsv3_text.strip()) * 1.5:
                    # Native 明显更长（可能包含更多内容），选 native
                    conflict_type = "complementary"
                    selected = "native"
                    evidence = "Native 文本更完整"
                else:
                    conflict_type = "equivalent"
                    selected = "ppsv3"
                    evidence = "默认选 PP（默认基座）"

            conflict = native_text != ppsv3_text

            results.append({
                "line_id": line_id,
                "selected_source": selected,
                "conflict_type": conflict_type,
                "conflict": conflict,
                "evidence": evidence,
                "confidence": 0.9 if conflict_type == "equivalent" else 0.7,
            })

        return json.dumps(results, ensure_ascii=False)
