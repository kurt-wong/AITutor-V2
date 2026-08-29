"""
Biology question type seed data.

Source: QUESTION_TYPE_TREE.md -- 全国新高考 + 北京高考 2026
Subject code: BIO
"""

from __future__ import annotations

from ..types import QuestionTypeSeed

# ═══ Level 1: Major categories ════════════════════════════════════════════════

_L1 = [
    QuestionTypeSeed(
        code="BIO-CHOICE",
        name="选择题",
        level=1,
        parent_code=None,
        description="选择题，含概念辨析与信息提取",
        keywords=["选择题", "multiple choice", "生物选择"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY",
        name="非选择题",
        level=1,
        parent_code=None,
        description="非选择题，含细胞代谢、遗传变异、动植物调节、实验设计",
        keywords=["非选择题", "non-choice questions", "大题"],
    ),
]

# ═══ Level 2: Subcategories ══════════════════════════════════════════════════

_L2 = [
    # -- 选择题
    QuestionTypeSeed(
        code="BIO-CHOICE-CONCEPT",
        name="概念辨析",
        level=2,
        parent_code="BIO-CHOICE",
        description="生物学概念辨析",
        keywords=["概念辨析", "concept discrimination", "概念"],
    ),
    QuestionTypeSeed(
        code="BIO-CHOICE-INFO",
        name="信息提取",
        level=2,
        parent_code="BIO-CHOICE",
        description="从材料中提取信息进行判断",
        keywords=["信息提取", "information extraction", "信息题"],
    ),
    # -- 非选择题
    QuestionTypeSeed(
        code="BIO-ESSAY-METAB",
        name="细胞代谢",
        level=2,
        parent_code="BIO-ESSAY",
        description="光合与呼吸、酶与ATP",
        keywords=["细胞代谢", "cell metabolism", "光合", "呼吸"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-GENET",
        name="遗传与变异",
        level=2,
        parent_code="BIO-ESSAY",
        description="遗传规律、变异类型、育种方案、基因频率（区分度最高）",
        keywords=["遗传与变异", "genetics & variation", "遗传", "变异"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-ANIMAL",
        name="动物生理调节",
        level=2,
        parent_code="BIO-ESSAY",
        description="神经调节、体液调节、免疫调节",
        keywords=["动物生理", "animal physiology", "神经调节", "体液调节", "免疫"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-PLANT",
        name="植物调节与环境",
        level=2,
        parent_code="BIO-ESSAY",
        description="植物激素、种群群落、生态系统",
        keywords=["植物调节", "plant regulation", "生态", "植物激素"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-EXP",
        name="实验设计与探究",
        level=2,
        parent_code="BIO-ESSAY",
        description="变量分析、步骤补充、结果预测、评价改进",
        keywords=["实验设计", "experimental design", "实验探究"],
    ),
    # -- 北京卷特有
    QuestionTypeSeed(
        code="BIO-ESSAY-THINK",
        name="科学思维路径",
        level=2,
        parent_code="BIO-ESSAY",
        description="北京卷特有：按'提出问题-作出假设-科学验证-进一步假设'设计的递进式探究题",
        keywords=["科学思维路径", "scientific thinking pathway", "递进探究"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-OPEN",
        name="开放性设问",
        level=2,
        parent_code="BIO-ESSAY",
        description="北京卷特有：鼓励提出创造性解决方案的开放性试题",
        keywords=["开放性设问", "open-ended question", "创造性方案"],
    ),
]

# ═══ Level 3: Specific types ═════════════════════════════════════════════════

_L3 = [
    # -- 细胞代谢
    QuestionTypeSeed(
        code="BIO-ESSAY-METAB-PHOTO",
        name="光合与呼吸",
        level=3,
        parent_code="BIO-ESSAY-METAB",
        description="光暗反应/C3/C5/净光合速率",
        keywords=["光合与呼吸", "photosynthesis & respiration", "光合", "呼吸作用"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-METAB-ENZ",
        name="酶与ATP",
        level=3,
        parent_code="BIO-ESSAY-METAB",
        description="影响因素/底物浓度曲线",
        keywords=["酶", "ATP", "enzyme", "底物浓度"],
    ),
    # -- 遗传与变异
    QuestionTypeSeed(
        code="BIO-ESSAY-GENET-LAW",
        name="遗传规律",
        level=3,
        parent_code="BIO-ESSAY-GENET",
        description="分离/自由组合/伴性遗传（系谱图）",
        keywords=["遗传规律", "genetic laws", "分离定律", "自由组合", "系谱图"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-GENET-VAR",
        name="变异类型",
        level=3,
        parent_code="BIO-ESSAY-GENET",
        description="基因突变/重组/染色体变异",
        keywords=["变异类型", "variation types", "基因突变", "染色体变异"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-GENET-BREED",
        name="育种方案",
        level=3,
        parent_code="BIO-ESSAY-GENET",
        description="杂交/诱变/单倍体育种",
        keywords=["育种方案", "breeding schemes", "杂交育种", "诱变育种"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-GENET-FREQ",
        name="基因频率",
        level=3,
        parent_code="BIO-ESSAY-GENET",
        description="哈代-温伯格定律",
        keywords=["基因频率", "gene frequency", "哈代-温伯格"],
    ),
    # -- 动物生理调节
    QuestionTypeSeed(
        code="BIO-ESSAY-ANIMAL-NEURAL",
        name="神经调节",
        level=3,
        parent_code="BIO-ESSAY-ANIMAL",
        description="反射弧/兴奋传导/膜电位",
        keywords=["神经调节", "neural regulation", "反射弧", "兴奋传导", "膜电位"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-ANIMAL-HUMOR",
        name="体液调节",
        level=3,
        parent_code="BIO-ESSAY-ANIMAL",
        description="激素分级/反馈调节",
        keywords=["体液调节", "humoral regulation", "激素", "反馈调节"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-ANIMAL-IMMUN",
        name="免疫调节",
        level=3,
        parent_code="BIO-ESSAY-ANIMAL",
        description="体液免疫/细胞免疫",
        keywords=["免疫调节", "immune regulation", "体液免疫", "细胞免疫"],
    ),
    # -- 植物调节与环境
    QuestionTypeSeed(
        code="BIO-ESSAY-PLANT-HORM",
        name="植物激素",
        level=3,
        parent_code="BIO-ESSAY-PLANT",
        description="生长素/赤霉素/脱落酸",
        keywords=["植物激素", "plant hormones", "生长素", "赤霉素"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-PLANT-POP",
        name="种群与群落",
        level=3,
        parent_code="BIO-ESSAY-PLANT",
        description="特征/种间关系",
        keywords=["种群与群落", "population & community", "种间关系"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-PLANT-ECO",
        name="生态系统",
        level=3,
        parent_code="BIO-ESSAY-PLANT",
        description="能量流动/物质循环/稳定性",
        keywords=["生态系统", "ecosystem", "能量流动", "物质循环"],
    ),
    # -- 实验设计与探究
    QuestionTypeSeed(
        code="BIO-ESSAY-EXP-VAR",
        name="变量分析",
        level=3,
        parent_code="BIO-ESSAY-EXP",
        description="自变量/因变量/无关变量",
        keywords=["变量分析", "variable analysis", "自变量", "因变量"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-EXP-PROC",
        name="步骤补充",
        level=3,
        parent_code="BIO-ESSAY-EXP",
        description="实验步骤补充完善",
        keywords=["步骤补充", "procedure completion", "实验步骤"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-EXP-PRED",
        name="结果预测",
        level=3,
        parent_code="BIO-ESSAY-EXP",
        description="表格/曲线形式的结果预测",
        keywords=["结果预测", "result prediction", "实验结果"],
    ),
    QuestionTypeSeed(
        code="BIO-ESSAY-EXP-EVAL",
        name="评价改进",
        level=3,
        parent_code="BIO-ESSAY-EXP",
        description="对照/重复/随机等实验评价改进",
        keywords=["评价改进", "evaluation & improvement", "对照实验", "重复"],
    ),
]

BIOLOGY_QUESTION_TYPES: list[QuestionTypeSeed] = _L1 + _L2 + _L3
