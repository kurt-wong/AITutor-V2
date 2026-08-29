"""
Mathematics question type seed data.

Source: QUESTION_TYPE_TREE.md -- 全国新高考 + 北京高考 2026
Subject code: MATH
"""

from __future__ import annotations

from ..types import QuestionTypeSeed

# ═══ Level 1: Major categories ════════════════════════════════════════════════

_L1 = [
    QuestionTypeSeed(
        code="MATH-OBJ",
        name="客观题",
        level=1,
        parent_code=None,
        description="客观题，含单选题、多选题和填空题",
        keywords=["客观题", "objective questions", "选择题", "填空题"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL",
        name="解答题",
        level=1,
        parent_code=None,
        description="解答题，含三角函数、数列、立体几何、概率统计、函数导数、解析几何",
        keywords=["解答题", "solution questions", "计算题"],
    ),
]

# ═══ Level 2: Subcategories ══════════════════════════════════════════════════

_L2 = [
    # -- 客观题
    QuestionTypeSeed(
        code="MATH-OBJ-CHOICE",
        name="选择题",
        level=2,
        parent_code="MATH-OBJ",
        description="单选题与多选题",
        keywords=["选择题", "multiple choice", "单选", "多选"],
    ),
    # -- 北京卷特有
    QuestionTypeSeed(
        code="MATH-OBJ-MULTI",
        name="多项选择",
        level=2,
        parent_code="MATH-OBJ",
        description="北京卷特有：答案个数不确定的选择题（可能1-4个正确答案），判分逻辑与单选不同",
        keywords=["多项选择", "multi-select", "不定项选择", "多选题"],
    ),
    QuestionTypeSeed(
        code="MATH-OBJ-FILL",
        name="填空题",
        level=2,
        parent_code="MATH-OBJ",
        description="填空题，含直接计算和多空填空",
        keywords=["填空题", "fill-in-the-blank", "填空"],
    ),
    # -- 解答题
    QuestionTypeSeed(
        code="MATH-SOL-TRIG",
        name="三角函数与解三角形",
        level=2,
        parent_code="MATH-SOL",
        description="正余弦定理、恒等变换等",
        keywords=["三角函数", "trigonometry", "解三角形", "正余弦定理"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-SEQ",
        name="数列",
        level=2,
        parent_code="MATH-SOL",
        description="等差/等比数列、递推、前n项和等",
        keywords=["数列", "sequences", "等差数列", "等比数列"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-SPACE",
        name="立体几何",
        level=2,
        parent_code="MATH-SOL",
        description="平行垂直证明、空间角计算、距离与体积",
        keywords=["立体几何", "solid geometry", "空间几何"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-PROB",
        name="概率与统计",
        level=2,
        parent_code="MATH-SOL",
        description="古典概型、条件概率、分布列、回归分析等",
        keywords=["概率统计", "probability & statistics", "概率", "统计"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-FUNC",
        name="函数与导数",
        level=2,
        parent_code="MATH-SOL",
        description="切线/单调性/极值/零点/不等式证明（压轴题）",
        keywords=["函数与导数", "functions & calculus", "导数", "压轴题"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-ANAL",
        name="解析几何",
        level=2,
        parent_code="MATH-SOL",
        description="圆锥曲线，含曲线方程、弦长面积、定点定值",
        keywords=["解析几何", "analytic geometry", "圆锥曲线", "椭圆", "抛物线"],
    ),
    # -- 北京卷特有
    QuestionTypeSeed(
        code="MATH-SOL-NEWDEF",
        name="新定义题",
        level=2,
        parent_code="MATH-SOL",
        description="北京卷特有：以数表/数阵为背景定义新性质，层层递进（判断→计数→证明），通常为压轴题",
        keywords=["新定义题", "new definition", "数表", "数阵", "新性质"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-ILLSTRUCT",
        name="结构不良/开放型",
        level=2,
        parent_code="MATH-SOL",
        description="北京卷特有：条件或结论开放、答案不唯一的开放性试题",
        keywords=["结构不良", "ill-structured", "开放型", "open-ended", "条件开放"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-TASKDRIV",
        name="任务驱动题",
        level=2,
        parent_code="MATH-SOL",
        description="北京卷特有：以实际任务为载体的综合应用题",
        keywords=["任务驱动题", "task-driven", "真实情境题", "real-world context"],
    ),
]

# ═══ Level 3: Specific types ═════════════════════════════════════════════════

_L3 = [
    # -- 选择题
    QuestionTypeSeed(
        code="MATH-OBJ-CHOICE-DIRECT",
        name="直接计算",
        level=3,
        parent_code="MATH-OBJ-CHOICE",
        description="直接计算型选择题",
        keywords=["直接计算", "direct calculation"],
    ),
    QuestionTypeSeed(
        code="MATH-OBJ-CHOICE-CONCEPT",
        name="概念判断",
        level=3,
        parent_code="MATH-OBJ-CHOICE",
        description="概念判断型选择题",
        keywords=["概念判断", "concept judgment"],
    ),
    # -- 填空题
    QuestionTypeSeed(
        code="MATH-OBJ-FILL-DIRECT",
        name="直接计算",
        level=3,
        parent_code="MATH-OBJ-FILL",
        description="直接计算型填空题",
        keywords=["直接计算", "direct calculation"],
    ),
    QuestionTypeSeed(
        code="MATH-OBJ-FILL-MULTI",
        name="多空填空",
        level=3,
        parent_code="MATH-OBJ-FILL",
        description="多空填空题",
        keywords=["多空填空", "multi-blank fill"],
    ),
    # -- 三角函数
    QuestionTypeSeed(
        code="MATH-SOL-TRIG-RULE",
        name="正余弦定理",
        level=3,
        parent_code="MATH-SOL-TRIG",
        description="求边/角/面积",
        keywords=["正余弦定理", "sine/cosine rule", "求边", "求角"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-TRIG-IDENT",
        name="恒等变换",
        level=3,
        parent_code="MATH-SOL-TRIG",
        description="求周期/单调性/平移",
        keywords=["恒等变换", "identical transformation", "周期", "单调性"],
    ),
    # -- 数列
    QuestionTypeSeed(
        code="MATH-SOL-SEQ-TERM",
        name="通项公式",
        level=3,
        parent_code="MATH-SOL-SEQ",
        description="等差/等比/递推求通项",
        keywords=["通项公式", "general term", "等差", "等比", "递推"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-SEQ-SUM",
        name="前n项和",
        level=3,
        parent_code="MATH-SOL-SEQ",
        description="裂项相消/错位相减",
        keywords=["前n项和", "summation", "裂项相消", "错位相减"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-SEQ-INEQ",
        name="数列不等式",
        level=3,
        parent_code="MATH-SOL-SEQ",
        description="数列不等式证明",
        keywords=["数列不等式", "inequality proof", "不等式证明"],
    ),
    # -- 立体几何
    QuestionTypeSeed(
        code="MATH-SOL-SPACE-PROOF",
        name="平行垂直证明",
        level=3,
        parent_code="MATH-SOL-SPACE",
        description="几何法证明平行与垂直关系",
        keywords=["平行垂直证明", "parallel/perpendicular proof", "几何法"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-SPACE-ANGLE",
        name="空间角计算",
        level=3,
        parent_code="MATH-SOL-SPACE",
        description="线线角/线面角/二面角（向量法）",
        keywords=["空间角", "spatial angles", "线线角", "线面角", "二面角", "向量法"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-SPACE-DIST",
        name="距离与体积",
        level=3,
        parent_code="MATH-SOL-SPACE",
        description="空间距离与体积计算",
        keywords=["距离与体积", "distance & volume"],
    ),
    # -- 概率与统计
    QuestionTypeSeed(
        code="MATH-SOL-PROB-CLASSIC",
        name="古典概型与条件概率",
        level=3,
        parent_code="MATH-SOL-PROB",
        description="古典概型与条件概率计算",
        keywords=["古典概型", "条件概率", "classical probability", "conditional probability"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-PROB-DIST",
        name="分布列与期望",
        level=3,
        parent_code="MATH-SOL-PROB",
        description="二项/超几何/正态分布",
        keywords=["分布列", "期望", "distribution", "二项分布", "正态分布"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-PROB-REG",
        name="回归与独立性检验",
        level=3,
        parent_code="MATH-SOL-PROB",
        description="线性回归与卡方独立性检验",
        keywords=["回归", "独立性检验", "regression", "chi-square"],
    ),
    # -- 函数与导数
    QuestionTypeSeed(
        code="MATH-SOL-FUNC-TANG",
        name="切线/单调性",
        level=3,
        parent_code="MATH-SOL-FUNC",
        description="导数求切线方程与单调区间",
        keywords=["切线", "单调性", "tangent", "monotonicity"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-FUNC-EXT",
        name="极值与最值",
        level=3,
        parent_code="MATH-SOL-FUNC",
        description="求函数极值与最值",
        keywords=["极值", "最值", "extrema", "max/min"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-FUNC-ZERO",
        name="零点问题",
        level=3,
        parent_code="MATH-SOL-FUNC",
        description="函数零点与根的问题",
        keywords=["零点", "zero/root problems", "根"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-FUNC-INEQ",
        name="不等式证明",
        level=3,
        parent_code="MATH-SOL-FUNC",
        description="利用导数构造不等式证明",
        keywords=["不等式证明", "inequality construction"],
    ),
    # -- 解析几何
    QuestionTypeSeed(
        code="MATH-SOL-ANAL-EQ",
        name="曲线方程",
        level=3,
        parent_code="MATH-SOL-ANAL",
        description="求圆锥曲线方程",
        keywords=["曲线方程", "conic equations", "椭圆方程", "抛物线方程"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-ANAL-CHORD",
        name="弦长/面积",
        level=3,
        parent_code="MATH-SOL-ANAL",
        description="弦长与面积计算",
        keywords=["弦长", "面积", "chord length", "area"],
    ),
    QuestionTypeSeed(
        code="MATH-SOL-ANAL-FIXED",
        name="定点定值",
        level=3,
        parent_code="MATH-SOL-ANAL",
        description="定点定值问题",
        keywords=["定点定值", "fixed points", "constants"],
    ),
]

MATH_QUESTION_TYPES: list[QuestionTypeSeed] = _L1 + _L2 + _L3
