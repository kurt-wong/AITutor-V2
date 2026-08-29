"""
Physics question type seed data.

Source: QUESTION_TYPE_TREE.md -- 全国新高考 + 北京高考 2026
Subject code: PHYS
"""

from __future__ import annotations

from ..types import QuestionTypeSeed

# ═══ Level 1: Major categories ════════════════════════════════════════════════

_L1 = [
    QuestionTypeSeed(
        code="PHYS-EXP",
        name="实验题",
        level=1,
        parent_code=None,
        description="物理实验题，含力学实验与电学实验",
        keywords=["实验题", "experimental questions", "物理实验"],
    ),
    QuestionTypeSeed(
        code="PHYS-CALC",
        name="计算题",
        level=1,
        parent_code=None,
        description="计算/综合题，含力学综合、电磁学综合与压轴综合",
        keywords=["计算题", "calculation questions", "综合题"],
    ),
]

# ═══ Level 2: Subcategories ══════════════════════════════════════════════════

_L2 = [
    # -- 实验题
    QuestionTypeSeed(
        code="PHYS-EXP-MECH",
        name="力学实验",
        level=2,
        parent_code="PHYS-EXP",
        description="力学实验，含纸带处理、验证性实验、仪器读数",
        keywords=["力学实验", "mechanics experiment", "力学"],
    ),
    QuestionTypeSeed(
        code="PHYS-EXP-ELEC",
        name="电学实验",
        level=2,
        parent_code="PHYS-EXP",
        description="电学实验，含电阻测量、电动势与内阻、多用电表",
        keywords=["电学实验", "electromagnetism experiment", "电学"],
    ),
    # -- 计算题
    QuestionTypeSeed(
        code="PHYS-CALC-MECH",
        name="力学综合",
        level=2,
        parent_code="PHYS-CALC",
        description="运动学、动力学、功与能、动量",
        keywords=["力学综合", "mechanics synthesis", "运动学", "动力学"],
    ),
    QuestionTypeSeed(
        code="PHYS-CALC-EM",
        name="电磁学综合",
        level=2,
        parent_code="PHYS-CALC",
        description="静电场、磁场、电磁感应",
        keywords=["电磁学综合", "electromagnetism synthesis", "电场", "磁场"],
    ),
    QuestionTypeSeed(
        code="PHYS-CALC-CHALLENGE",
        name="压轴综合题",
        level=2,
        parent_code="PHYS-CALC",
        description="力电磁多过程、多对象与图像信息",
        keywords=["压轴综合题", "comprehensive challenge", "压轴题"],
    ),
]

# ═══ Level 3: Specific types ═════════════════════════════════════════════════

_L3 = [
    # -- 力学实验
    QuestionTypeSeed(
        code="PHYS-EXP-MECH-TAPE",
        name="纸带处理",
        level=3,
        parent_code="PHYS-EXP-MECH",
        description="逐差法测加速度",
        keywords=["纸带处理", "tape processing", "逐差法", "加速度"],
    ),
    QuestionTypeSeed(
        code="PHYS-EXP-MECH-VERIF",
        name="验证性实验",
        level=3,
        parent_code="PHYS-EXP-MECH",
        description="牛二定律/机械能守恒/动量守恒验证",
        keywords=["验证性实验", "verification", "牛二定律", "机械能守恒"],
    ),
    QuestionTypeSeed(
        code="PHYS-EXP-MECH-INST",
        name="仪器读数",
        level=3,
        parent_code="PHYS-EXP-MECH",
        description="游标卡尺/螺旋测微器读数",
        keywords=["仪器读数", "instrument reading", "游标卡尺", "螺旋测微器"],
    ),
    # -- 电学实验
    QuestionTypeSeed(
        code="PHYS-EXP-ELEC-RES",
        name="电阻测量",
        level=3,
        parent_code="PHYS-EXP-ELEC",
        description="伏安法/半偏法/电桥法测电阻",
        keywords=["电阻测量", "resistance measurement", "伏安法", "半偏法"],
    ),
    QuestionTypeSeed(
        code="PHYS-EXP-ELEC-EMF",
        name="电源电动势与内阻",
        level=3,
        parent_code="PHYS-EXP-ELEC",
        description="U-I图像法测电动势与内阻",
        keywords=["电动势", "内阻", "EMF", "internal resistance", "U-I图像"],
    ),
    QuestionTypeSeed(
        code="PHYS-EXP-ELEC-MULTI",
        name="多用电表",
        level=3,
        parent_code="PHYS-EXP-ELEC",
        description="欧姆调零/故障判断",
        keywords=["多用电表", "multimeter", "欧姆调零", "故障判断"],
    ),
    # -- 力学综合
    QuestionTypeSeed(
        code="PHYS-CALC-MECH-KIN",
        name="运动学",
        level=3,
        parent_code="PHYS-CALC-MECH",
        description="匀变速/抛体/圆周运动",
        keywords=["运动学", "kinematics", "匀变速", "抛体", "圆周运动"],
    ),
    QuestionTypeSeed(
        code="PHYS-CALC-MECH-DYN",
        name="动力学",
        level=3,
        parent_code="PHYS-CALC-MECH",
        description="牛顿定律与受力分析",
        keywords=["动力学", "dynamics", "牛顿定律", "受力分析"],
    ),
    QuestionTypeSeed(
        code="PHYS-CALC-MECH-ENERGY",
        name="功与能",
        level=3,
        parent_code="PHYS-CALC-MECH",
        description="动能定理/机械能守恒",
        keywords=["功与能", "work & energy", "动能定理", "机械能守恒"],
    ),
    QuestionTypeSeed(
        code="PHYS-CALC-MECH-MOM",
        name="动量",
        level=3,
        parent_code="PHYS-CALC-MECH",
        description="动量守恒/碰撞",
        keywords=["动量", "momentum", "动量守恒", "碰撞"],
    ),
    # -- 电磁学综合
    QuestionTypeSeed(
        code="PHYS-CALC-EM-STAT",
        name="静电场",
        level=3,
        parent_code="PHYS-CALC-EM",
        description="场强/电势/偏转",
        keywords=["静电场", "electrostatics", "场强", "电势", "偏转"],
    ),
    QuestionTypeSeed(
        code="PHYS-CALC-EM-MAG",
        name="磁场",
        level=3,
        parent_code="PHYS-CALC-EM",
        description="洛伦兹力/圆周运动",
        keywords=["磁场", "magnetic field", "洛伦兹力", "圆周运动"],
    ),
    QuestionTypeSeed(
        code="PHYS-CALC-EM-INDUCT",
        name="电磁感应",
        level=3,
        parent_code="PHYS-CALC-EM",
        description="楞次定律/法拉第定律/动生感生电动势",
        keywords=["电磁感应", "electromagnetic induction", "楞次定律", "法拉第定律"],
    ),
    # -- 压轴综合题
    QuestionTypeSeed(
        code="PHYS-CALC-CHALLENGE-MULTI",
        name="力电磁多过程",
        level=3,
        parent_code="PHYS-CALC-CHALLENGE",
        description="力电磁多过程综合问题",
        keywords=["力电磁多过程", "multi-process", "多过程"],
    ),
    QuestionTypeSeed(
        code="PHYS-CALC-CHALLENGE-GRAPH",
        name="多对象与图像信息",
        level=3,
        parent_code="PHYS-CALC-CHALLENGE",
        description="多对象与图像信息综合分析",
        keywords=["多对象", "图像信息", "multi-object", "graph analysis"],
    ),
]

PHYSICS_QUESTION_TYPES: list[QuestionTypeSeed] = _L1 + _L2 + _L3
