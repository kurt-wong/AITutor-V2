"""
History question type seed data.

Source: QUESTION_TYPE_TREE.md -- 全国新高考 + 北京高考 2026
Subject code: HIST
"""

from __future__ import annotations

from ..types import QuestionTypeSeed

# ═══ Level 1: Major categories ════════════════════════════════════════════════

_L1 = [
    QuestionTypeSeed(
        code="HIST-CHOICE",
        name="选择题",
        level=1,
        parent_code=None,
        description="选择题，含史料解读与时空观念",
        keywords=["选择题", "multiple choice", "历史选择"],
    ),
    QuestionTypeSeed(
        code="HIST-ESSAY",
        name="非选择题",
        level=1,
        parent_code=None,
        description="非选择题，含比较分析、背景影响、史料解读、开放性论述",
        keywords=["非选择题", "non-choice questions", "大题"],
    ),
]

# ═══ Level 2: Subcategories ══════════════════════════════════════════════════

_L2 = [
    # -- 选择题
    QuestionTypeSeed(
        code="HIST-CHOICE-SOURCE",
        name="史料解读",
        level=2,
        parent_code="HIST-CHOICE",
        description="史料解读型选择题",
        keywords=["史料解读", "source interpretation", "史料"],
    ),
    QuestionTypeSeed(
        code="HIST-CHOICE-TIME",
        name="时空观念",
        level=2,
        parent_code="HIST-CHOICE",
        description="时空观念型选择题",
        keywords=["时空观念", "spatial-temporal awareness", "时空"],
    ),
    # -- 非选择题
    QuestionTypeSeed(
        code="HIST-ESSAY-COMP",
        name="中外历史比较",
        level=2,
        parent_code="HIST-ESSAY",
        description="中外历史异同归纳与原因分析",
        keywords=["中外历史比较", "comparative history", "比较"],
    ),
    QuestionTypeSeed(
        code="HIST-ESSAY-BACK",
        name="背景与影响分析",
        level=2,
        parent_code="HIST-ESSAY",
        description="多角度背景与辩证影响分析",
        keywords=["背景与影响", "background & impact", "背景分析", "影响分析"],
    ),
    QuestionTypeSeed(
        code="HIST-ESSAY-SOURCE",
        name="史料解读与解释",
        level=2,
        parent_code="HIST-ESSAY",
        description="史料价值判断与观点评析",
        keywords=["史料解读", "historical source interpretation", "史料价值"],
    ),
    QuestionTypeSeed(
        code="HIST-ESSAY-OPEN",
        name="开放性论述",
        level=2,
        parent_code="HIST-ESSAY",
        description="小论文，自拟论题与史论结合",
        keywords=["开放性论述", "open-ended essay", "小论文"],
    ),
]

# ═══ Level 3: Specific types ═════════════════════════════════════════════════

_L3 = [
    # -- 中外历史比较
    QuestionTypeSeed(
        code="HIST-ESSAY-COMP-SD",
        name="异同归纳",
        level=3,
        parent_code="HIST-ESSAY-COMP",
        description="归纳中外历史事件的异同点",
        keywords=["异同归纳", "similarities & differences", "异同"],
    ),
    QuestionTypeSeed(
        code="HIST-ESSAY-COMP-CAUSE",
        name="原因分析",
        level=3,
        parent_code="HIST-ESSAY-COMP",
        description="地理/经济/文化/政治等多角度原因分析",
        keywords=["原因分析", "cause analysis", "地理", "经济", "文化", "政治"],
    ),
    # -- 背景与影响分析
    QuestionTypeSeed(
        code="HIST-ESSAY-BACK-MULTI",
        name="多角度背景",
        level=3,
        parent_code="HIST-ESSAY-BACK",
        description="政治/经济/思想/国际等多角度背景分析",
        keywords=["多角度背景", "multi-perspective background", "政治", "经济", "思想"],
    ),
    QuestionTypeSeed(
        code="HIST-ESSAY-BACK-DIAL",
        name="辩证影响",
        level=3,
        parent_code="HIST-ESSAY-BACK",
        description="短期/长期、积极/局限的辩证影响评价",
        keywords=["辩证影响", "dialectical impact", "积极", "局限"],
    ),
    # -- 史料解读与解释
    QuestionTypeSeed(
        code="HIST-ESSAY-SOURCE-VAL",
        name="史料价值",
        level=3,
        parent_code="HIST-ESSAY-SOURCE",
        description="一手/二手、文献/实物史料价值判断",
        keywords=["史料价值", "source value", "一手史料", "二手史料"],
    ),
    QuestionTypeSeed(
        code="HIST-ESSAY-SOURCE-VIEW",
        name="观点评析",
        level=3,
        parent_code="HIST-ESSAY-SOURCE",
        description="对同一事件的不同解释评析",
        keywords=["观点评析", "viewpoint evaluation", "不同解释"],
    ),
    # -- 开放性论述
    QuestionTypeSeed(
        code="HIST-ESSAY-OPEN-THESIS",
        name="自拟论题",
        level=3,
        parent_code="HIST-ESSAY-OPEN",
        description="自主拟定论述主题",
        keywords=["自拟论题", "proposing a thesis", "论题"],
    ),
    QuestionTypeSeed(
        code="HIST-ESSAY-OPEN-ARG",
        name="史论结合",
        level=3,
        parent_code="HIST-ESSAY-OPEN",
        description="史料与论述相结合",
        keywords=["史论结合", "combining history with argument", "史论"],
    ),
]

HISTORY_QUESTION_TYPES: list[QuestionTypeSeed] = _L1 + _L2 + _L3
