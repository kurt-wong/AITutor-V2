"""
Chemistry question type seed data.

Source: QUESTION_TYPE_TREE.md -- 全国新高考 + 北京高考 2026
Subject code: CHEM
"""

from __future__ import annotations

from ..types import QuestionTypeSeed

# ═══ Level 1: Major categories ════════════════════════════════════════════════

_L1 = [
    QuestionTypeSeed(
        code="CHEM-CHOICE",
        name="选择题",
        level=1,
        parent_code=None,
        description="选择题，含化学与STSE、实验基础、有机、无机、原理等",
        keywords=["选择题", "multiple choice", "化学选择"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY",
        name="非选择题",
        level=1,
        parent_code=None,
        description="非选择题，含工艺流程、原理综合、实验探究、有机推断、物质结构",
        keywords=["非选择题", "non-choice questions", "大题"],
    ),
]

# ═══ Level 2: Subcategories ══════════════════════════════════════════════════

_L2 = [
    # -- 非选择题
    QuestionTypeSeed(
        code="CHEM-ESSAY-PROCESS",
        name="工艺流程题",
        level=2,
        parent_code="CHEM-ESSAY",
        description="工业流程题，含方程式书写、操作条件、定量计算、绿色评价",
        keywords=["工艺流程", "industrial process flow", "工业流程"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-PRINCIPLE",
        name="原理综合题",
        level=2,
        parent_code="CHEM-ESSAY",
        description="化学原理综合，含盖斯定律、速率与平衡、电化学、图像分析",
        keywords=["原理综合", "chemical principles synthesis", "化学原理"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-EXPLORE",
        name="实验探究题",
        level=2,
        parent_code="CHEM-ESSAY",
        description="实验探究，含仪器操作、制备分离、定量滴定、方案评价",
        keywords=["实验探究", "experimental inquiry", "化学实验"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-ORGANIC",
        name="有机推断与合成",
        level=2,
        parent_code="CHEM-ESSAY",
        description="有机化学推断与合成路线设计",
        keywords=["有机推断", "organic inference", "有机合成"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-STRUCT",
        name="物质结构与性质",
        level=2,
        parent_code="CHEM-ESSAY",
        description="原子/分子结构与性质",
        keywords=["物质结构", "atomic/molecular structure", "结构与性质"],
    ),
]

# ═══ Level 3: Specific types ═════════════════════════════════════════════════

_L3 = [
    # -- 工艺流程题
    QuestionTypeSeed(
        code="CHEM-ESSAY-PROCESS-EQ",
        name="方程式书写",
        level=3,
        parent_code="CHEM-ESSAY-PROCESS",
        description="离子/化学方程式书写",
        keywords=["方程式", "equation writing", "离子方程式", "化学方程式"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-PROCESS-OP",
        name="操作与条件",
        level=3,
        parent_code="CHEM-ESSAY-PROCESS",
        description="温度/pH/萃取/结晶等操作条件",
        keywords=["操作条件", "operations & conditions", "温度", "pH", "萃取"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-PROCESS-CALC",
        name="定量计算",
        level=3,
        parent_code="CHEM-ESSAY-PROCESS",
        description="产率/纯度/Ksp等定量计算",
        keywords=["定量计算", "quantitative calculation", "产率", "纯度", "Ksp"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-PROCESS-GREEN",
        name="绿色评价",
        level=3,
        parent_code="CHEM-ESSAY-PROCESS",
        description="原子利用率/循环利用等绿色化学评价",
        keywords=["绿色评价", "green chemistry", "原子利用率", "循环利用"],
    ),
    # -- 原理综合题
    QuestionTypeSeed(
        code="CHEM-ESSAY-PRINCIPLE-HESS",
        name="盖斯定律",
        level=3,
        parent_code="CHEM-ESSAY-PRINCIPLE",
        description="反应热计算",
        keywords=["盖斯定律", "Hess's law", "反应热"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-PRINCIPLE-RATE",
        name="速率与平衡",
        level=3,
        parent_code="CHEM-ESSAY-PRINCIPLE",
        description="Kp/Kc/转化率/平衡移动",
        keywords=["速率与平衡", "rate & equilibrium", "平衡常数", "转化率"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-PRINCIPLE-ELEC",
        name="电化学",
        level=3,
        parent_code="CHEM-ESSAY-PRINCIPLE",
        description="电极反应/离子迁移",
        keywords=["电化学", "electrochemistry", "电极反应", "离子迁移"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-PRINCIPLE-GRAPH",
        name="图像分析",
        level=3,
        parent_code="CHEM-ESSAY-PRINCIPLE",
        description="能量图/速率图/平衡曲线",
        keywords=["图像分析", "graph analysis", "能量图", "速率图"],
    ),
    # -- 实验探究题
    QuestionTypeSeed(
        code="CHEM-ESSAY-EXPLORE-INST",
        name="仪器操作",
        level=3,
        parent_code="CHEM-ESSAY-EXPLORE",
        description="气密性/防倒吸/滴定管操作",
        keywords=["仪器操作", "instrument operation", "气密性", "滴定管"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-EXPLORE-PREP",
        name="制备分离",
        level=3,
        parent_code="CHEM-ESSAY-EXPLORE",
        description="除杂/提纯",
        keywords=["制备分离", "preparation & separation", "除杂", "提纯"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-EXPLORE-TITR",
        name="定量滴定",
        level=3,
        parent_code="CHEM-ESSAY-EXPLORE",
        description="酸碱/氧化还原滴定与误差分析",
        keywords=["定量滴定", "quantitative titration", "酸碱滴定", "误差"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-EXPLORE-EVAL",
        name="方案评价",
        level=3,
        parent_code="CHEM-ESSAY-EXPLORE",
        description="控制变量/对照实验方案评价",
        keywords=["方案评价", "scheme evaluation", "控制变量", "对照实验"],
    ),
    # -- 有机推断与合成
    QuestionTypeSeed(
        code="CHEM-ESSAY-ORGANIC-FG",
        name="官能团识别",
        level=3,
        parent_code="CHEM-ESSAY-ORGANIC",
        description="官能团识别与性质判断",
        keywords=["官能团", "functional group", "官能团识别"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-ORGANIC-TYPE",
        name="反应类型",
        level=3,
        parent_code="CHEM-ESSAY-ORGANIC",
        description="取代/加成/消去等反应类型判断",
        keywords=["反应类型", "reaction type", "取代", "加成", "消去"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-ORGANIC-ISO",
        name="同分异构体",
        level=3,
        parent_code="CHEM-ESSAY-ORGANIC",
        description="限定条件书写与计数",
        keywords=["同分异构体", "isomers", "异构体"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-ORGANIC-ROUTE",
        name="合成路线",
        level=3,
        parent_code="CHEM-ESSAY-ORGANIC",
        description="3-4步合成路线设计",
        keywords=["合成路线", "synthetic route", "合成设计"],
    ),
    # -- 物质结构与性质
    QuestionTypeSeed(
        code="CHEM-ESSAY-STRUCT-CONFIG",
        name="电子排布/电离能",
        level=3,
        parent_code="CHEM-ESSAY-STRUCT",
        description="电子排布与电离能分析",
        keywords=["电子排布", "电离能", "electron configuration", "ionization energy"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-STRUCT-HYBRID",
        name="杂化与空间构型",
        level=3,
        parent_code="CHEM-ESSAY-STRUCT",
        description="杂化方式与空间构型判断",
        keywords=["杂化", "空间构型", "hybridization", "geometry"],
    ),
    QuestionTypeSeed(
        code="CHEM-ESSAY-STRUCT-CRYSTAL",
        name="晶胞计算",
        level=3,
        parent_code="CHEM-ESSAY-STRUCT",
        description="密度/配位数等晶胞计算",
        keywords=["晶胞计算", "crystal cell calculation", "密度", "配位数"],
    ),
]

CHEMISTRY_QUESTION_TYPES: list[QuestionTypeSeed] = _L1 + _L2 + _L3
