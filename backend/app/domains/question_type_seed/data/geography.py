"""
Geography question type seed data.

Source: QUESTION_TYPE_TREE.md -- 全国新高考 + 北京高考 2026
Subject code: GEOG
"""

from __future__ import annotations

from ..types import QuestionTypeSeed

# ═══ Level 1: Major categories ════════════════════════════════════════════════

_L1 = [
    QuestionTypeSeed(
        code="GEOG-CHOICE",
        name="选择题",
        level=1,
        parent_code=None,
        description="选择题，含图表判读与原理应用",
        keywords=["选择题", "multiple choice", "地理选择"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY",
        name="非选择题",
        level=1,
        parent_code=None,
        description="非选择题，含自然地理、人文地理、区域分析",
        keywords=["非选择题", "non-choice questions", "大题"],
    ),
]

# ═══ Level 2: Subcategories ══════════════════════════════════════════════════

_L2 = [
    # -- 选择题
    QuestionTypeSeed(
        code="GEOG-CHOICE-CHART",
        name="图表判读",
        level=2,
        parent_code="GEOG-CHOICE",
        description="图表/地图判读型选择题",
        keywords=["图表判读", "chart/map interpretation", "图表", "地图"],
    ),
    QuestionTypeSeed(
        code="GEOG-CHOICE-PRIN",
        name="原理应用",
        level=2,
        parent_code="GEOG-CHOICE",
        description="地理原理应用型选择题",
        keywords=["原理应用", "principle application", "地理原理"],
    ),
    # -- 非选择题
    QuestionTypeSeed(
        code="GEOG-ESSAY-PHYS",
        name="自然地理",
        level=2,
        parent_code="GEOG-ESSAY",
        description="大气圈、水圈、岩石圈、整体性与差异性",
        keywords=["自然地理", "physical geography", "自然"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-HUMAN",
        name="人文地理",
        level=2,
        parent_code="GEOG-ESSAY",
        description="人口城市、农业工业区位、交通区域、可持续发展",
        keywords=["人文地理", "human geography", "人文"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-REGION",
        name="区域地理与区域分析",
        level=2,
        parent_code="GEOG-ESSAY",
        description="区域定位、区域比较、区域问题与对策",
        keywords=["区域地理", "regional geography", "区域分析"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-TOUR",
        name="旅游地理",
        level=2,
        parent_code="GEOG-ESSAY",
        description="旅游资源评价、开发条件、影响与保护（选考/穿插）",
        keywords=["旅游地理", "tourism geography", "旅游"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-ENVIRO",
        name="环境保护",
        level=2,
        parent_code="GEOG-ESSAY",
        description="环境问题成因、防治措施、资源利用（选考/穿插）",
        keywords=["环境保护", "environmental protection", "环保"],
    ),
]

# ═══ Level 3: Specific types ═════════════════════════════════════════════════

_L3 = [
    # -- 自然地理
    QuestionTypeSeed(
        code="GEOG-ESSAY-PHYS-ATMO",
        name="大气圈",
        level=3,
        parent_code="GEOG-ESSAY-PHYS",
        description="天气系统/气候成因/热力环流",
        keywords=["大气圈", "atmosphere", "天气系统", "气候", "热力环流"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-PHYS-HYDRO",
        name="水圈",
        level=3,
        parent_code="GEOG-ESSAY-PHYS",
        description="水循环/河流补给/洋流",
        keywords=["水圈", "hydrosphere", "水循环", "河流补给", "洋流"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-PHYS-LITHO",
        name="岩石圈",
        level=3,
        parent_code="GEOG-ESSAY-PHYS",
        description="内/外力作用/板块构造/地貌",
        keywords=["岩石圈", "lithosphere", "板块构造", "地貌", "内力", "外力"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-PHYS-HOLISM",
        name="整体性与差异性",
        level=3,
        parent_code="GEOG-ESSAY-PHYS",
        description="垂直地带性/地域分异",
        keywords=["整体性", "差异性", "holism", "zonality", "地带性"],
    ),
    # -- 人文地理
    QuestionTypeSeed(
        code="GEOG-ESSAY-HUMAN-POP",
        name="人口与城市",
        level=3,
        parent_code="GEOG-ESSAY-HUMAN",
        description="迁移因素/城市结构/城市化",
        keywords=["人口与城市", "population & cities", "城市化", "人口迁移"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-HUMAN-LOC",
        name="农业/工业区位",
        level=3,
        parent_code="GEOG-ESSAY-HUMAN",
        description="区位因素分析",
        keywords=["区位", "agricultural/industrial location", "农业区位", "工业区位"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-HUMAN-TRANS",
        name="交通与区域",
        level=3,
        parent_code="GEOG-ESSAY-HUMAN",
        description="布局因素及影响",
        keywords=["交通与区域", "transportation & regions", "交通布局"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-HUMAN-SUST",
        name="可持续发展",
        level=3,
        parent_code="GEOG-ESSAY-HUMAN",
        description="人地关系/循环经济",
        keywords=["可持续发展", "sustainable development", "人地关系", "循环经济"],
    ),
    # -- 区域地理与区域分析
    QuestionTypeSeed(
        code="GEOG-ESSAY-REGION-POS",
        name="区域定位与特征",
        level=3,
        parent_code="GEOG-ESSAY-REGION",
        description="区域定位与特征描述",
        keywords=["区域定位", "区域特征", "regional positioning"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-REGION-COMP",
        name="区域比较",
        level=3,
        parent_code="GEOG-ESSAY-REGION",
        description="不同区域的比较分析",
        keywords=["区域比较", "regional comparison"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-REGION-PROB",
        name="区域问题与对策",
        level=3,
        parent_code="GEOG-ESSAY-REGION",
        description="荒漠化/水土流失等问题与对策",
        keywords=["区域问题", "regional problems", "荒漠化", "水土流失"],
    ),
    # -- 旅游地理
    QuestionTypeSeed(
        code="GEOG-ESSAY-TOUR-RES",
        name="资源评价",
        level=3,
        parent_code="GEOG-ESSAY-TOUR",
        description="旅游资源评价",
        keywords=["资源评价", "resource evaluation", "旅游资源"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-TOUR-DEV",
        name="开发条件",
        level=3,
        parent_code="GEOG-ESSAY-TOUR",
        description="旅游开发条件分析",
        keywords=["开发条件", "development conditions"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-TOUR-IMPACT",
        name="影响与保护",
        level=3,
        parent_code="GEOG-ESSAY-TOUR",
        description="旅游影响与保护措施",
        keywords=["影响与保护", "impact & protection"],
    ),
    # -- 环境保护
    QuestionTypeSeed(
        code="GEOG-ESSAY-ENVIRO-CAUSE",
        name="环境问题成因",
        level=3,
        parent_code="GEOG-ESSAY-ENVIRO",
        description="污染/生物多样性等环境问题成因",
        keywords=["环境问题成因", "environmental causes", "污染", "生物多样性"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-ENVIRO-PREV",
        name="防治措施",
        level=3,
        parent_code="GEOG-ESSAY-ENVIRO",
        description="环境问题防治措施",
        keywords=["防治措施", "prevention & control"],
    ),
    QuestionTypeSeed(
        code="GEOG-ESSAY-ENVIRO-RES",
        name="资源利用",
        level=3,
        parent_code="GEOG-ESSAY-ENVIRO",
        description="资源合理利用",
        keywords=["资源利用", "resource utilization"],
    ),
]

GEOGRAPHY_QUESTION_TYPES: list[QuestionTypeSeed] = _L1 + _L2 + _L3
