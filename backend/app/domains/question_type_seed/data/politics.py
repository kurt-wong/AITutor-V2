"""
Politics question type seed data.

Source: QUESTION_TYPE_TREE.md -- 全国新高考 + 北京高考 2026
Subject code: POLI
"""

from __future__ import annotations

from ..types import QuestionTypeSeed

# ═══ Level 1: Major categories ════════════════════════════════════════════════

_L1 = [
    QuestionTypeSeed(
        code="POLI-CHOICE",
        name="选择题",
        level=1,
        parent_code=None,
        description="选择题，含原理判断与材料对应",
        keywords=["选择题", "multiple choice", "政治选择"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY",
        name="非选择题",
        level=1,
        parent_code=None,
        description="非选择题，含经济社会、政治法治、哲学文化、逻辑思维、开放综合",
        keywords=["非选择题", "non-choice questions", "大题"],
    ),
]

# ═══ Level 2: Subcategories ══════════════════════════════════════════════════

_L2 = [
    # -- 选择题
    QuestionTypeSeed(
        code="POLI-CHOICE-PRIN",
        name="原理判断",
        level=2,
        parent_code="POLI-CHOICE",
        description="政治原理判断型选择题",
        keywords=["原理判断", "principle judgment", "原理"],
    ),
    QuestionTypeSeed(
        code="POLI-CHOICE-MAT",
        name="材料对应",
        level=2,
        parent_code="POLI-CHOICE",
        description="材料与原理对应型选择题",
        keywords=["材料对应", "material matching", "材料"],
    ),
    # -- 非选择题
    QuestionTypeSeed(
        code="POLI-ESSAY-ECON",
        name="经济与社会",
        level=2,
        parent_code="POLI-ESSAY",
        description="经济现象分析、政策解读、企业与分配",
        keywords=["经济与社会", "economy & society", "经济", "社会"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-POLITICS",
        name="政治与法治",
        level=2,
        parent_code="POLI-ESSAY",
        description="制度运行、法治建设、公民参与",
        keywords=["政治与法治", "politics & rule of law", "政治", "法治"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-PHILO",
        name="哲学与文化",
        level=2,
        parent_code="POLI-ESSAY",
        description="唯物辩证法、认识论、历史唯物主义、文化自信",
        keywords=["哲学与文化", "philosophy & culture", "哲学", "文化"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-LOGIC",
        name="逻辑与思维",
        level=2,
        parent_code="POLI-ESSAY",
        description="逻辑推理、辩证与创新思维（新教材特有）",
        keywords=["逻辑与思维", "logic & thinking", "逻辑", "思维"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-OPEN",
        name="开放性综合",
        level=2,
        parent_code="POLI-ESSAY",
        description="观点评析、建议策略、发言提纲",
        keywords=["开放性综合", "open comprehensive", "开放题"],
    ),
]

# ═══ Level 3: Specific types ═════════════════════════════════════════════════

_L3 = [
    # -- 经济与社会
    QuestionTypeSeed(
        code="POLI-ESSAY-ECON-PHEN",
        name="现象分析",
        level=3,
        parent_code="POLI-ESSAY-ECON",
        description="价格/供求/消费等经济现象分析",
        keywords=["现象分析", "economic phenomena", "价格", "供求", "消费"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-ECON-POLICY",
        name="政策解读",
        level=3,
        parent_code="POLI-ESSAY-ECON",
        description="财政/货币/产业政策解读",
        keywords=["政策解读", "policy interpretation", "财政", "货币", "产业"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-ECON-ENT",
        name="企业与分配",
        level=3,
        parent_code="POLI-ESSAY-ECON",
        description="经营成功因素/共同富裕",
        keywords=["企业与分配", "enterprise & distribution", "企业经营", "共同富裕"],
    ),
    # -- 政治与法治
    QuestionTypeSeed(
        code="POLI-ESSAY-POLITICS-INST",
        name="制度运行",
        level=3,
        parent_code="POLI-ESSAY-POLITICS",
        description="人大/政府/政协/基层自治",
        keywords=["制度运行", "institutional operation", "人大", "政府", "政协"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-POLITICS-LEGAL",
        name="法治建设",
        level=3,
        parent_code="POLI-ESSAY-POLITICS",
        description="依法治国/依法行政",
        keywords=["法治建设", "legal construction", "依法治国", "依法行政"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-POLITICS-CITIZEN",
        name="公民参与",
        level=3,
        parent_code="POLI-ESSAY-POLITICS",
        description="民主选举/决策/管理/监督",
        keywords=["公民参与", "citizen participation", "民主选举", "民主监督"],
    ),
    # -- 哲学与文化
    QuestionTypeSeed(
        code="POLI-ESSAY-PHILO-MAT",
        name="唯物论与辩证法",
        level=3,
        parent_code="POLI-ESSAY-PHILO",
        description="物质意识/联系发展/矛盾",
        keywords=["唯物论", "辩证法", "materialism", "dialectics", "矛盾"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-PHILO-EPIST",
        name="认识论",
        level=3,
        parent_code="POLI-ESSAY-PHILO",
        description="实践认识/真理",
        keywords=["认识论", "epistemology", "实践", "认识", "真理"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-PHILO-HIST",
        name="历史唯物主义",
        level=3,
        parent_code="POLI-ESSAY-PHILO",
        description="社会基本矛盾/群众史观/价值观",
        keywords=["历史唯物主义", "historical materialism", "社会矛盾", "群众史观"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-PHILO-CULT",
        name="文化自信",
        level=3,
        parent_code="POLI-ESSAY-PHILO",
        description="传承/交流/民族精神",
        keywords=["文化自信", "cultural confidence", "传承", "民族精神"],
    ),
    # -- 逻辑与思维
    QuestionTypeSeed(
        code="POLI-ESSAY-LOGIC-REAS",
        name="逻辑推理",
        level=3,
        parent_code="POLI-ESSAY-LOGIC",
        description="演绎/归纳/类比推理",
        keywords=["逻辑推理", "logical reasoning", "演绎", "归纳", "类比"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-LOGIC-DIAL",
        name="辩证与创新思维",
        level=3,
        parent_code="POLI-ESSAY-LOGIC",
        description="分析综合/逆向/发散思维",
        keywords=["辩证思维", "创新思维", "dialectical thinking", "发散思维"],
    ),
    # -- 开放性综合
    QuestionTypeSeed(
        code="POLI-ESSAY-OPEN-OPIN",
        name="观点评析",
        level=3,
        parent_code="POLI-ESSAY-OPEN",
        description="对观点进行评析",
        keywords=["观点评析", "opinion evaluation"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-OPEN-SUGG",
        name="建议策略",
        level=3,
        parent_code="POLI-ESSAY-OPEN",
        description="如乡村振兴举措等建议策略",
        keywords=["建议策略", "suggestions & strategies", "建议", "策略"],
    ),
    QuestionTypeSeed(
        code="POLI-ESSAY-OPEN-SPEECH",
        name="发言提纲",
        level=3,
        parent_code="POLI-ESSAY-OPEN",
        description="发言提纲/短文写作",
        keywords=["发言提纲", "speech outline", "短文"],
    ),
]

POLITICS_QUESTION_TYPES: list[QuestionTypeSeed] = _L1 + _L2 + _L3
