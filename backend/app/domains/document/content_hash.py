"""content_hash 规范化与计算（Phase 2A Step 5）+ 去重答案比较归一化。

设计（已冻结，docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md Step 5）：
- content_hash = SHA256(规范化题干 + 规范化选项 + 规范化题型)
- 规范化规则：Unicode NFKC + 全角转半角 + 去空白/换行/制表 + 去常见标点 + 小写，
  保证同一道题无论排版差异（空格/标点/换行/全半角）都得到相同 hash。
- 综合题（is_composite）：子题（qno+type+answer）拼接参与 hash，
  不同子题配置视为不同题目。

确定性要求：规范化规则对空白、标点、换行、Unicode 有确定性（可复现）。

本模块是「去重/规范化工具」，无任何项目内依赖；ingestion 与 question 域
（update_question_content 重算 hash 时的答案冲突判断）共用 compact_answer。
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

# 需要去除的标点（全角/半角常见标点）
_PUNCTUATION = set(
    " \t\n\r\u3000　，。！？；：、（）()【】[]《》〈〉「」『』“”‘’\"'…—–-·•.,!?;:"
)


def normalize_text(text: str | None) -> str:
    """规范化文本：NFKC + 全角转半角 + 去空白/标点 + 小写。

    - NFKC：统一 Unicode 兼容字符（全角数字/字母 → 半角，兼容性分解）
    - 去除空白、换行、制表、常见标点
    - 小写
    """
    if not text:
        return ""
    # NFKC 归一化（全角→半角、兼容字符合并）
    s = unicodedata.normalize("NFKC", text)
    # 逐字符过滤：去空白/标点，其余保留
    chars = []
    for ch in s:
        if ch in _PUNCTUATION or ch.isspace():
            continue
        chars.append(ch.lower())
    return "".join(chars)


def normalize_options(options: list[dict] | None) -> str:
    """规范化选项列表为确定性字符串。"""
    if not options:
        return ""
    items = []
    for opt in options:
        if isinstance(opt, dict):
            label = normalize_text(str(opt.get("label", "")))
            text = normalize_text(str(opt.get("text", "")))
            items.append(f"{label}:{text}")
        else:
            items.append(normalize_text(str(opt)))
    # 排序保证选项顺序不影响 hash（同选项不同顺序视为同一题）
    return "|".join(sorted(items))


def normalize_sub_questions(sub_questions: list | None) -> str:
    """规范化子题（综合题）：qno+type+answer 拼接，排序保证确定性。"""
    if not sub_questions:
        return ""
    items = []
    for sub in sub_questions:
        if isinstance(sub, dict):
            qno = normalize_text(str(sub.get("qno", "")))
            qtype = normalize_text(str(sub.get("question_type", "")))
            answer = normalize_text(str(sub.get("answer", "")))
            nested = normalize_sub_questions(sub.get("sub_sub_questions"))
            item = f"{qno}:{qtype}:{answer}"
            if nested:
                item += f"[{nested}]"
            items.append(item)
    return "|".join(sorted(items))


def compute_content_hash(
    *,
    stem: str | None,
    options: list[dict] | None = None,
    question_type: str | None = None,
    sub_questions: list | None = None,
) -> str:
    """计算 content_hash（SHA256，64 位 hex）。

    hash 覆盖：规范化题干 + 规范化选项 + 规范化题型 + 规范化子题。
    """
    parts = [
        normalize_text(stem),
        normalize_options(options),
        normalize_text(question_type),
        normalize_sub_questions(sub_questions),
    ]
    canonical = "\x00".join(parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compact_answer(text: str | None) -> str:
    """答案比较用归一：格式统一后再比对，消除"同内容不同格式"的假冲突。

    2026-08-25（BUG-026）：只去空白，语文朝阳 Q17 假冲突已修。
    2026-08-26（数学 40 题 answer_conflict）：同一道题两次入库，答案内容
    相同但格式不同（LLM/OCR 输出抖动）被误判冲突：
    - LaTeX 包裹：`$0$` vs `0`、`$\\frac{3\\pi}{4}$` vs `\\frac{3\\pi}{4}`
    - 全角/半角：`(1)` vs `（1）`、`；` vs `;`、`：` vs `:`
    - 分隔符：换行 vs `；` 拼接
    归一化顺序：去空白 → 全角转半角 → LaTeX 标记剥离 → 数学命令等价化。
    仅用于去重冲突判断，不改变存储的原始答案。

    2026-08-27：从 ingestion._compact_answer 提升为公共函数，
    question 域（update_question_content 答案冲突判断）与 ingestion 共用。
    """
    if not text:
        return ""
    out = "".join(text.split())  # 去全部空白（含全角空格/换行）
    # 圈号后点号/空白归一（`①.`/`①`/`①．` → `①`；LLM 输出圈号后点号有无抖动）
    out = re.sub(r"([①②③④⑤⑥⑦⑧⑨⑩])\s*[.．、]?", r"\1", out)
    # 全角 → 半角（常见标点；保留中文与圈号 ①②③）
    out = out.replace("（", "(").replace("）", ")")
    out = out.replace("；", ";").replace("：", ":").replace("，", ",")
    out = out.replace("．", ".").replace("。", ".")
    out = out.replace("－", "-").replace("～", "~")
    # 换行/分号分隔统一（LLM 输出有时 \n 换行、有时 ；拼接，同内容）
    out = out.replace("\\n", ";").replace("\n", ";")
    # LaTeX 标记剥离（含 $ 或 \\ 时才处理，否则原样）
    if "$" in out or "\\" in out:
        out = re.sub(r"\$\$", "", out).replace("$", "")
        out = out.replace(r"\(", "").replace(r"\)", "").replace(r"\[", "").replace(r"\]", "")
        # \frac{a}{b} → a/b（保留分子分母内容，去掉命令外壳）
        out = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"\1/\2", out)
        out = re.sub(r"\\dfrac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"\1/\2", out)
        out = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt(\1)", out)
        # \text{...} / \mathrm{...} 等文本标记 → 取内容
        out = re.sub(r"\\(?:text|mathrm|mathbf|mathit|mathrm|operatorname)\s*\{([^{}]*)\}", r"\1", out)
        out = out.replace(r"\{", "{").replace(r"\}", "}")
        out = out.replace(r"\pi", "π").replace(r"\mid", "|").replace(r"\le", "<=").replace(r"\ge", ">=")
        # 间距/括号命令与 \command 外壳 → 去命令名保留字母（\sin→sin 等）
        out = re.sub(r"\\(?:left|right|big|Big|bigg|Bigg|quad|qquad|;|,|!| )", "", out)
        out = re.sub(r"\\([a-zA-Z]+)", r"\1", out)
        out = out.replace("{", "").replace("}", "")
    return out
