"""
化学知识树 v2 (课程标准对齐) — 按教材模块组织

模块结构 (5 大模块):
  CHEM-C1  必修一 (物质变化/钠氯/铁金属/结构周期律)
  CHEM-C2  必修二 (非金属/反应与能量/有机化合物/可持续发展)
  CHEM-S1  选必一·反应原理 (热效应/速率平衡/水溶液平衡/电化学)
  CHEM-S2  选必二·结构性质 (原子结构/分子结构/晶体结构)
  CHEM-S3  选必三·有机基础 (有机研究方法/烃/烃衍生物/生物大分子与高分子)

编码: CHEM-{MODULE}-{CHAPTER} for L3, CHEM-{MODULE}-{CHAPTER}-{POINT} for L4
"""

from __future__ import annotations

from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed

CHEMISTRY_KNOWLEDGE_TREE_V2: list[KnowledgeTreeSeed] = [

    # ═══ Level 2: 课程模块 (5) ═════════════════════════════════════════════════════

    KnowledgeTreeSeed(
        code="CHEM-C1", name="必修一", level=2, parent_code="CHEM",
        description="物质及其变化、海水中的重要元素钠和氯、铁金属材料、物质结构元素周期律",
        keywords=[
            "必修一",
            "物质分类",
            "离子反应",
            "氧化还原",
            "钠",
            "氯",
            "铁",
            "物质的量",
            "元素周期律",
            "化学键",
            "中和滴定",
            "滴定",
            "误差分析",
            "配制",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2", name="必修二", level=2, parent_code="CHEM",
        description="化工生产中的重要非金属元素、化学反应与能量、有机化合物、化学与可持续发展",
        keywords=[
            "必修二", "硫", "氮", "硅", "有机化合物", "化学能",
            "反应速率", "化学平衡", "可持续发展",
        ],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1", name="选必一·反应原理", level=2, parent_code="CHEM",
        description="化学反应的热效应、化学反应速率与平衡、水溶液中的离子反应与平衡、化学反应与电能",
        keywords=[
            "反应原理",
            "热效应",
            "焓变",
            "盖斯定律",
            "速率",
            "平衡",
            "电离平衡",
            "水解",
            "沉淀溶解",
            "原电池",
            "电解池",
            "pH",
            "ΔH",
            "勒夏特列",
            "热化学",
            "电化学",
            "电离",
            "金属腐蚀",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2", name="选必二·结构性质", level=2, parent_code="CHEM",
        description="原子结构与性质、分子结构与性质、晶体结构与性质",
        keywords=[
            "结构性质", "原子结构", "电子排布", "分子结构", "杂化轨道",
            "VSEPR", "晶体", "晶胞", "配位数",
        ],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3", name="选必三·有机基础", level=2, parent_code="CHEM",
        description="有机化合物结构特点与研究方法、烃、烃的衍生物、生物大分子与合成高分子",
        keywords=[
            "有机基础",
            "烃",
            "烃的衍生物",
            "糖类",
            "蛋白质",
            "核酸",
            "合成高分子",
            "官能团",
            "有机合成",
            "同分异构",
            "同系物",
            "命名",
            "有机",
        ]
    ),

    # ═══ CHEM-C1: 必修一 ══════════════════════════════════════════════════════════

    # ─── C1-01 物质及其变化 ─────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-C1-01", name="物质及其变化", level=3, parent_code="CHEM-C1",
        description="物质的分类与转化、离子反应、氧化还原反应",
        keywords=["物质分类", "离子反应", "氧化还原", "电解质", "化合价"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-01-01", name="物质的分类与转化", level=4, parent_code="CHEM-C1-01",
        description="纯净物与混合物、单质与化合物、酸碱盐氧化物分类、电解质与非电解质、物质的转化关系",
        keywords=["分类", "纯净物", "混合物", "电解质", "非电解质", "胶体", "丁达尔效应"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-01-02", name="离子反应", level=4, parent_code="CHEM-C1-01",
        description="电解质的电离、离子反应发生的条件、离子方程式的书写与正误判断、离子共存",
        keywords=["离子反应", "离子方程式", "电离", "离子共存", "复分解"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-01-03", name="氧化还原反应", level=4, parent_code="CHEM-C1-01",
        description="化合价升降与电子转移、氧化剂与还原剂、氧化还原反应的判断与配平",
        keywords=[
            "氧化还原",
            "化合价",
            "氧化剂",
            "还原剂",
            "电子转移",
            "配平",
            "n=m/M",
            "元素周期",
            "化合价升降法",
            "化学式",
            "化学键",
            "周期表",
            "摩尔",
            "氧化反应",
            "氧化还原计算",
            "物质的量",
            "电子守恒",
            "离子",
            "还原反应",
            "阿伏加德罗",
        ]
    ),

    # ─── C1-02 海水中的重要元素──钠和氯 ──────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-C1-02", name="海水中的重要元素──钠和氯", level=3, parent_code="CHEM-C1",
        description="钠及其化合物、氯及其化合物、物质的量、气体摩尔体积、物质的量浓度",
        keywords=["钠", "氯", "物质的量", "气体摩尔体积", "物质的量浓度"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-02-01", name="钠及其化合物", level=4, parent_code="CHEM-C1-02",
        description="钠的性质(与水/氧气反应)、Na₂O与Na₂O₂、Na₂CO₃与NaHCO₃的性质与鉴别",
        keywords=[
            "钠",
            "Na",
            "Na₂O₂",
            "Na₂CO₃",
            "NaHCO₃",
            "过氧化钠",
            "Al(OH)₃",
            "Fe²⁺",
            "侯氏制碱",
            "金属",
            "铁",
            "铝",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-02-02", name="氯及其化合物", level=4, parent_code="CHEM-C1-02",
        description="Cl₂的制备与性质(强氧化性)、HClO(漂白)、氯水成分、Cl⁻的检验",
        keywords=["氯气", "Cl₂", "次氯酸", "HClO", "漂白", "氯水", "Cl⁻检验"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-02-03", name="物质的量", level=4, parent_code="CHEM-C1-02",
        description="物质的量(n)、摩尔(mol)、阿伏加德罗常数(Nₐ)、摩尔质量(M)、n=m/M、N=nNₐ",
        keywords=[
            "物质的量",
            "摩尔",
            "阿伏加德罗常数",
            "Nₐ",
            "摩尔质量",
            "n=m/M",
            "Cl⁻",
            "NH₄⁺",
            "N_A",
            "SO₄²⁻",
            "微粒数",
            "收集",
            "检验",
            "气体制备",
            "鉴别",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-02-04", name="气体摩尔体积", level=4, parent_code="CHEM-C1-02",
        description="气体摩尔体积(Vm)、标准状况下Vm=22.4L/mol、阿伏加德罗定律及推论",
        keywords=["气体摩尔体积", "22.4L/mol", "标准状况", "阿伏加德罗定律", "c=n/V", "稀释", "配制"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-02-05", name="物质的量浓度", level=4, parent_code="CHEM-C1-02",
        description="物质的量浓度(c=n/V)、一定物质的量浓度溶液的配制、稀释定律(c₁V₁=c₂V₂)",
        keywords=["物质的量浓度", "c=n/V", "配制溶液", "稀释", "容量瓶"],
    ),

    # ─── C1-03 铁 金属材料 ──────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-C1-03", name="铁 金属材料", level=3, parent_code="CHEM-C1",
        description="铁及其化合物、金属材料、金属的腐蚀与防护",
        keywords=["铁", "Fe²⁺", "Fe³⁺", "合金", "金属腐蚀", "防护"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-03-01", name="铁及其化合物", level=4, parent_code="CHEM-C1-03",
        description="铁的化学性质、Fe²⁺与Fe³⁺的性质与转化(铁三角)、Fe(OH)₂与Fe(OH)₃、KSCN检验Fe³⁺",
        keywords=[
            "铁",
            "Fe²⁺",
            "Fe³⁺",
            "铁三角",
            "Fe(OH)₂",
            "Fe(OH)₃",
            "KSCN",
            "Fe",
            "Fe(OH)2",
            "Fe(OH)3",
            "Fe2+",
            "Fe2O3",
            "Fe3+",
            "Fe3O4",
            "FeCl3",
            "FeO",
            "FeS2",
            "FeSO4",
            "KSCN检验",
            "亚铁",
            "亚铁离子",
            "沉淀颜色",
            "磁性",
            "红棕色",
            "铁离子",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-03-02", name="金属材料", level=4, parent_code="CHEM-C1-03",
        description="金属的通性(导电导热延展性)、合金概念与性质、金属活动性顺序、铝的两性",
        keywords=["合金", "金属活动性", "铝", "两性", "Al(OH)₃", "铝热反应", "Al"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-03-03", name="金属的腐蚀与防护", level=4, parent_code="CHEM-C1-03",
        description="化学腐蚀与电化学腐蚀(吸氧腐蚀/析氢腐蚀)、防护方法(涂层/电化学保护/改变组成)",
        keywords=["金属腐蚀", "吸氧腐蚀", "析氢腐蚀", "电化学保护", "牺牲阳极"],
    ),

    # ─── C1-04 物质结构 元素周期律 ───────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-C1-04", name="物质结构 元素周期律", level=3, parent_code="CHEM-C1",
        description="原子结构与元素周期表、元素周期律、化学键",
        keywords=["原子结构", "元素周期表", "元素周期律", "化学键", "离子键", "共价键", "原子半径", "周期表", "电负性"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-04-01", name="原子结构与元素周期表", level=4, parent_code="CHEM-C1-04",
        description="原子的构成(质子/中子/电子)、核外电子排布规律、原子结构示意图、同位素、周期表结构(周期/族)",
        keywords=["原子结构", "电子排布", "同位素", "元素周期表", "周期", "族", "核外电子"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-04-02", name="元素周期律", level=4, parent_code="CHEM-C1-04",
        description="原子半径/化合价/金属性/非金属性的周期性变化、同周期同主族元素性质递变规律",
        keywords=[
            "元素周期律",
            "原子半径",
            "金属性",
            "非金属性",
            "递变规律",
            "Al(OH)3",
            "H2CO3",
            "H2SO4",
            "H3PO4",
            "HClO4",
            "Mg(OH)2",
            "NaOH",
            "元素周期表",
            "周期律",
            "对角线规则",
            "最高价氧化物",
            "电离能",
            "电负性",
            "碱性",
            "酸性",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C1-04-03", name="化学键", level=4, parent_code="CHEM-C1-04",
        description="离子键与共价键(极性/非极性)的形成、共价化合物与离子化合物、电子式表示化学键",
        keywords=[
            "离子键",
            "共价键",
            "极性共价键",
            "电子式",
            "共价化合物",
            "离子化合物",
            "中和滴定",
            "制备",
            "实验",
            "指示剂",
            "检验",
            "气体制备",
            "滴定",
            "萃取",
            "蒸发",
            "蒸馏",
            "误差分析",
            "过滤",
        ]
    ),

    # ═══ CHEM-C2: 必修二 ══════════════════════════════════════════════════════════

    # ─── C2-01 化工生产中的重要非金属元素 ─────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-C2-01", name="化工生产中的重要非金属元素", level=3, parent_code="CHEM-C2",
        description="硫及其化合物、氮及其化合物、无机非金属材料",
        keywords=[
            "硫",
            "氮",
            "硅",
            "非金属",
            "SO₂",
            "NH₃",
            "HNO₃",
            "SiO₂",
            "Cl₂",
            "卤素",
            "合金",
            "氯",
            "碱金属",
            "过渡金属",
            "金属",
            "金属活动性",
            "钠",
            "铁",
            "铝",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-01-01", name="硫及其化合物", level=4, parent_code="CHEM-C2-01",
        description="硫单质、SO₂的漂白性与还原性、浓H₂SO₄(吸水性/脱水性/强氧化性)、SO₄²⁻检验",
        keywords=["硫", "SO₂", "浓硫酸", "SO₄²⁻检验", "接触法制硫酸"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-01-02", name="氮及其化合物", level=4, parent_code="CHEM-C2-01",
        description="N₂、NO与NO₂、NH₃(喷泉实验/催化氧化)、铵盐(NH₄⁺检验)、HNO₃(稀/浓与金属反应)",
        keywords=[
            "氮",
            "NH₃",
            "氨",
            "HNO₃",
            "硝酸",
            "NO",
            "NO₂",
            "铵盐",
            "喷泉实验",
            "AgNO3",
            "HNO3",
            "N2",
            "NH4",
            "NO2",
            "N₂",
            "氨的催化氧化",
            "浓硝酸",
            "稀硝酸",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-01-03", name="无机非金属材料", level=4, parent_code="CHEM-C2-01",
        description="硅(Si)单质与半导体、SiO₂(光导纤维)、Na₂SiO₃(水玻璃)、传统硅酸盐材料(水泥/玻璃/陶瓷)",
        keywords=["硅", "Si", "SiO₂", "光导纤维", "硅酸盐", "水泥", "玻璃", "陶瓷"],
    ),

    # ─── C2-02 化学反应与能量 ─────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-C2-02", name="化学反应与能量", level=3, parent_code="CHEM-C2",
        description="化学反应与热能、化学反应与电能、化学反应的速率与限度",
        keywords=["化学能", "热能", "原电池", "反应速率", "化学平衡"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-02-01", name="化学反应与热能", level=4, parent_code="CHEM-C2-02",
        description="吸热反应与放热反应、化学键与能量变化的关系、热化学方程式初步、能量图",
        keywords=["吸热反应", "放热反应", "能量变化", "热化学方程式"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-02-02", name="化学反应与电能", level=4, parent_code="CHEM-C2-02",
        description="原电池工作原理(负极氧化/正极还原)、正负极判断、电极反应式、常见化学电源初步",
        keywords=["原电池", "负极", "正极", "电极反应", "化学电源"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-02-03", name="化学反应的速率与限度", level=4, parent_code="CHEM-C2-02",
        description="化学反应速率表示(v=Δc/Δt)、影响速率的因素(浓度/温度/催化剂)、可逆反应、化学平衡状态初步",
        keywords=["反应速率", "v=Δc/Δt", "催化剂", "可逆反应", "化学平衡"],
    ),

    # ─── C2-03 有机化合物 ─────────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-C2-03", name="有机化合物", level=3, parent_code="CHEM-C2",
        description="认识有机化合物、乙烯与高分子材料、乙醇与乙酸、基本营养物质",
        keywords=["有机化合物", "乙烯", "乙醇", "乙酸", "营养物质"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-03-01", name="认识有机化合物", level=4, parent_code="CHEM-C2-03",
        description="有机物的概念与特点、碳原子成键特点、同分异构体、烷烃通式与命名",
        keywords=[
            "有机物",
            "碳四价",
            "同分异构体",
            "烷烃",
            "结构式",
            "加成",
            "取代",
            "官能团",
            "有机",
            "消去",
            "烃",
            "聚合",
            "酯",
            "酯化",
            "酸",
            "醇",
            "醛",
            "高分子",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-03-02", name="乙烯与高分子材料", level=4, parent_code="CHEM-C2-03",
        description="乙烯的结构(C=C双键)与加成反应、加聚反应、常见高分子材料(聚乙烯/聚氯乙烯)",
        keywords=["乙烯", "C=C", "加成反应", "加聚反应", "聚乙烯", "聚氯乙烯", "乙炔", "溴水褪色", "甲烷"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-03-03", name="乙醇与乙酸", level=4, parent_code="CHEM-C2-03",
        description="乙醇(与Na反应/催化氧化/酯化)、乙酸(酸性/酯化反应)、官能团(-OH/-COOH)",
        keywords=["乙醇", "C₂H₅OH", "乙酸", "CH₃COOH", "酯化反应", "羟基", "羧基"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-03-04", name="基本营养物质", level=4, parent_code="CHEM-C2-03",
        description="油脂(皂化反应)、糖类(葡萄糖银镜反应/淀粉水解)、蛋白质(变性/颜色反应)、维生素",
        keywords=["油脂", "糖类", "蛋白质", "葡萄糖", "淀粉", "氨基酸", "皂化", "仪器", "分液", "萃取", "蒸发", "蒸馏", "过滤"]
    ),

    # ─── C2-04 化学与可持续发展 ───────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-C2-04", name="化学与可持续发展", level=3, parent_code="CHEM-C2",
        description="自然资源的开发利用、化学品的合理使用、环境保护与绿色化学",
        keywords=["资源开发", "化学品安全", "环境保护", "绿色化学"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-04-01", name="自然资源的开发利用", level=4, parent_code="CHEM-C2-04",
        description="海水资源综合利用、金属矿物的冶炼(热还原法/电解法)、化石燃料的合理利用、新能源",
        keywords=["海水资源", "金属冶炼", "化石燃料", "新能源", "热还原法"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-04-02", name="化学品的合理使用", level=4, parent_code="CHEM-C2-04",
        description="常见化学品的安全使用(漂白粉/消毒剂)、化学品对人体与环境的影响、化学品分类与标识",
        keywords=["漂白粉", "消毒剂", "安全使用", "化学品标识"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-C2-04-03", name="环境保护与绿色化学", level=4, parent_code="CHEM-C2-04",
        description="酸雨/臭氧层空洞/温室效应等环境问题、三废处理、绿色化学原则与应用",
        keywords=["酸雨", "臭氧层", "温室效应", "绿色化学", "三废处理"],
    ),

    # ═══ CHEM-S1: 选必一·反应原理 ══════════════════════════════════════════════════

    # ─── S1-01 化学反应的热效应 ───────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S1-01", name="化学反应的热效应", level=3, parent_code="CHEM-S1",
        description="反应热与焓变、盖斯定律、燃烧热",
        keywords=["反应热", "焓变", "ΔH", "盖斯定律", "燃烧热", "中和热", "热化学"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-01-01", name="反应热与焓变", level=4, parent_code="CHEM-S1-01",
        description="反应热的概念、焓变(ΔH)的含义与计算、热化学方程式的书写规范(状态/ΔH符号)",
        keywords=["反应热", "焓变", "ΔH", "热化学方程式", "放热", "吸热"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-01-02", name="盖斯定律", level=4, parent_code="CHEM-S1-01",
        description="盖斯定律内容(反应热与途径无关)、利用盖斯定律计算反应热、热化学方程式组合运算",
        keywords=["盖斯定律", "反应热计算", "热化学方程式组合"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-01-03", name="燃烧热与中和热", level=4, parent_code="CHEM-S1-01",
        description="燃烧热的定义(1mol可燃物完全燃烧)、中和热(强酸强碱稀溶液)、中和热的测定实验",
        keywords=["燃烧热", "中和热", "中和热测定", "完全燃烧"],
    ),

    # ─── S1-02 化学反应速率与平衡 ─────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S1-02", name="化学反应速率与平衡", level=3, parent_code="CHEM-S1",
        description="反应速率、化学平衡、平衡移动、反应调控",
        keywords=["反应速率", "化学平衡", "平衡常数", "勒夏特列", "平衡移动", "K", "催化剂", "平衡", "速率"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-02-01", name="化学反应速率", level=4, parent_code="CHEM-S1-02",
        description="反应速率表示与计算、浓度/温度/压强/催化剂对速率的影响、有效碰撞理论与活化能",
        keywords=["反应速率", "v=Δc/Δt", "活化能", "有效碰撞", "催化剂"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-02-02", name="化学平衡", level=4, parent_code="CHEM-S1-02",
        description="平衡状态的特征与判断(v正=v逆)、平衡常数K的表达式与计算、平衡转化率、三段式计算",
        keywords=["化学平衡", "平衡常数K", "转化率", "三段式", "v正=v逆", "K", "勒夏特列", "平衡移动"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-02-03", name="化学平衡的移动", level=4, parent_code="CHEM-S1-02",
        description="勒夏特列原理、浓度/温度/压强变化对平衡的影响、等效平衡",
        keywords=["勒夏特列", "平衡移动", "浓度", "温度", "压强", "等效平衡"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-02-04", name="化学反应的调控", level=4, parent_code="CHEM-S1-02",
        description="工业生产中反应条件的选择与优化(如合成氨)、反应方向(熵变/吉布斯自由能ΔG)",
        keywords=["反应调控", "合成氨", "条件优化", "熵变", "ΔG"],
    ),

    # ─── S1-03 水溶液中的离子反应与平衡 ───────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S1-03", name="水溶液中的离子反应与平衡", level=3, parent_code="CHEM-S1",
        description="电离平衡、水的电离与pH、盐类水解、沉淀溶解平衡",
        keywords=["电离平衡", "pH", "水解", "Ksp", "沉淀溶解", "K_sp", "沉淀", "缓冲溶液"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-03-01", name="弱电解质的电离平衡", level=4, parent_code="CHEM-S1-03",
        description="弱电解质的电离平衡、电离平衡常数Ka/Kb、电离度、同离子效应与稀释定律",
        keywords=["弱电解质", "电离平衡", "Ka", "Kb", "电离度", "同离子效应", "K_a", "K_b"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-03-02", name="水的电离与溶液的pH", level=4, parent_code="CHEM-S1-03",
        description="水的电离平衡与Kw=1×10⁻¹⁴(25°C)、pH的定义与计算(pH=-lg[H⁺])、酸碱指示剂",
        keywords=["水的电离", "Kw", "pH", "pH计算", "酸碱指示剂", "K_w", "pH=-lg[H⁺]", "中和滴定"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-03-03", name="盐类的水解", level=4, parent_code="CHEM-S1-03",
        description="盐类水解的规律(谁弱谁水解)、水解方程式书写、影响水解平衡的因素、水解应用(明矾净水等)",
        keywords=["盐类水解", "水解方程式", "水解平衡", "明矾净水"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-03-04", name="沉淀溶解平衡", level=4, parent_code="CHEM-S1-03",
        description="溶度积常数Ksp的含义与计算、Qc与Ksp比较判断沉淀生成/溶解、沉淀的转化与应用",
        keywords=["沉淀溶解平衡", "Ksp", "溶度积", "沉淀转化", "Qc与Ksp", "K_sp", "沉淀溶解", "盐类水解"]
    ),

    # ─── S1-04 化学反应与电能 ─────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S1-04", name="化学反应与电能", level=3, parent_code="CHEM-S1",
        description="原电池、电解池、金属腐蚀与防护",
        keywords=["原电池", "电解池", "电解", "电极反应", "金属腐蚀", "电化学保护", "电镀"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-04-01", name="原电池与化学电源", level=4, parent_code="CHEM-S1-04",
        description="原电池工作原理深化、常见化学电源(锌锰干电池/铅蓄电池/氢氧燃料电池/锂离子电池)",
        keywords=["原电池", "干电池", "铅蓄电池", "燃料电池", "锂离子电池", "正极", "负极"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-04-02", name="电解池与电解应用", level=4, parent_code="CHEM-S1-04",
        description="电解池工作原理(阳极氧化/阴极还原)、放电顺序、电解应用(氯碱工业/电镀/电冶金/精炼铜)",
        keywords=["电解池", "电解", "阳极", "阴极", "氯碱工业", "电镀", "电冶金", "金属腐蚀"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S1-04-03", name="金属的腐蚀与防护", level=4, parent_code="CHEM-S1-04",
        description="金属腐蚀原理深化(化学腐蚀与电化学腐蚀)、金属防护方法(涂层/电化学保护/改变组成)",
        keywords=["金属腐蚀", "化学腐蚀", "电化学腐蚀", "防护", "牺牲阳极", "外加电流"],
    ),

    # ═══ CHEM-S2: 选必二·结构性质 ══════════════════════════════════════════════════

    # ─── S2-01 原子结构与性质 ─────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S2-01", name="原子结构与性质", level=3, parent_code="CHEM-S2",
        description="原子结构(能层/能级/电子排布)、元素周期表与周期律深化、元素性质递变",
        keywords=["原子结构", "电子排布", "能层", "能级", "周期律", "电负性"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2-01-01", name="原子结构", level=4, parent_code="CHEM-S2-01",
        description="能层与能级、原子轨道(电子云形状)、构造原理、电子排布式与简化电子排布式、电子自旋",
        keywords=["能层", "能级", "原子轨道", "构造原理", "电子排布式", "电子自旋"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2-01-02", name="元素周期表与周期律深化", level=4, parent_code="CHEM-S2-01",
        description="电子排布与族的关系、能级组与周期的关系、价电子、原子半径递变规律",
        keywords=["元素周期表", "能级组", "价电子", "原子半径", "族"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2-01-03", name="元素性质及其变化规律", level=4, parent_code="CHEM-S2-01",
        description="电离能与电负性的递变规律、金属性与非金属性的周期性变化、对角线规则",
        keywords=["电离能", "电负性", "金属性", "非金属性", "对角线规则"],
    ),

    # ─── S2-02 分子结构与性质 ─────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S2-02", name="分子结构与性质", level=3, parent_code="CHEM-S2",
        description="共价键(σ键/π键/键参数)、分子的空间结构(VSEPR/杂化轨道)、分子间作用力与氢键",
        keywords=["共价键", "σ键", "π键", "VSEPR", "杂化轨道", "分子间作用力", "氢键", "离子键", "范德华力", "金属键"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2-02-01", name="共价键", level=4, parent_code="CHEM-S2-02",
        description="共价键的本质(σ键与π键)、键参数(键能/键长/键角)、键的极性与分子极性",
        keywords=["σ键", "π键", "键能", "键长", "键角", "极性分子", "非极性分子"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2-02-02", name="分子的空间结构", level=4, parent_code="CHEM-S2-02",
        description="VSEPR模型(价层电子对互斥)、杂化轨道理论(sp/sp²/sp³)、配位键与配位化合物",
        keywords=["VSEPR", "杂化轨道", "sp杂化", "sp²杂化", "sp³杂化", "配位键"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2-02-03", name="分子间作用力与物质性质", level=4, parent_code="CHEM-S2-02",
        description="范德华力(取向力/诱导力/色散力)及其对物理性质的影响、氢键(分子间/分子内)及其对性质的影响",
        keywords=["范德华力", "氢键", "分子间氢键", "分子内氢键", "沸点"],
    ),

    # ─── S2-03 晶体结构与性质 ─────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S2-03", name="晶体结构与性质", level=3, parent_code="CHEM-S2",
        description="晶体概念与晶胞、晶体的分类(离子/原子/分子/金属晶体)、晶体结构与计算",
        keywords=["晶体", "晶胞", "离子晶体", "原子晶体", "分子晶体", "金属晶体"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2-03-01", name="晶体与晶胞", level=4, parent_code="CHEM-S2-03",
        description="晶体的特征(各向异性/固定熔点)、晶胞的概念与均摊法计算、晶体与非晶体的区别",
        keywords=["晶体", "晶胞", "均摊法", "各向异性", "非晶体"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2-03-02", name="晶体的分类与性质", level=4, parent_code="CHEM-S2-03",
        description="离子晶体(离子键/NaCl型)、原子晶体(共价键/金刚石/SiO₂)、分子晶体(分子间力/干冰)、金属晶体(金属键)",
        keywords=["离子晶体", "原子晶体", "分子晶体", "金属晶体", "NaCl", "金刚石", "干冰"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S2-03-03", name="晶体结构与计算", level=4, parent_code="CHEM-S2-03",
        description="晶体中粒子的堆积方式(密堆积/非密堆积)、配位数、晶胞参数与密度计算、晶体结构的测定方法",
        keywords=["堆积方式", "配位数", "晶胞密度", "X射线衍射"],
    ),

    # ═══ CHEM-S3: 选必三·有机基础 ══════════════════════════════════════════════════

    # ─── S3-01 有机化合物结构特点与研究方法 ───────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S3-01", name="有机化合物结构特点与研究方法", level=3, parent_code="CHEM-S3",
        description="有机化合物的分类、结构特点(碳的成键方式/同分异构体)、研究方法(光谱分析等)",
        keywords=["有机分类", "碳四价", "同分异构体", "光谱分析", "官能团"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-01-01", name="有机化合物的分类", level=4, parent_code="CHEM-S3-01",
        description="按碳骨架分类(链状/环状)、按官能团分类、同系物的概念",
        keywords=["链状", "环状", "官能团分类", "同系物"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-01-02", name="有机化合物的结构特点", level=4, parent_code="CHEM-S3-01",
        description="碳原子的成键特点(四价/碳链/碳环)、有机物中σ键与π键、同分异构现象(碳链/位置/官能团异构)",
        keywords=["碳四价", "碳链", "碳环", "σ键", "π键", "同分异构体"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-01-03", name="有机化合物的研究方法", level=4, parent_code="CHEM-S3-01",
        description="元素分析与相对分子质量测定、红外光谱(IR)、核磁共振氢谱(¹H NMR)、质谱(MS)",
        keywords=["元素分析", "红外光谱", "核磁共振", "质谱", "IR", "NMR"],
    ),

    # ─── S3-02 烃 ────────────────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S3-02", name="烃", level=3, parent_code="CHEM-S3",
        description="烷烃、烯烃、炔烃、芳香烃的结构与性质",
        keywords=["烷烃", "烯烃", "炔烃", "芳香烃", "加成", "取代", "消去", "苯"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-02-01", name="烷烃", level=4, parent_code="CHEM-S3-02",
        description="烷烃通式CₙH₂ₙ₊₂与结构特点、物理性质递变规律、同系物概念与系统命名法、取代反应",
        keywords=["烷烃", "CₙH₂ₙ₊₂", "取代反应", "系统命名法", "同系物"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-02-02", name="烯烃", level=4, parent_code="CHEM-S3-02",
        description="烯烃通式CₙH₂ₙ与C=C双键结构、加成反应、顺反异构、1,2-加成与1,4-加成、加聚反应与氧化反应",
        keywords=["烯烃", "CₙH₂ₙ", "C=C", "加成反应", "顺反异构", "加聚反应"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-02-03", name="炔烃", level=4, parent_code="CHEM-S3-02",
        description="炔烃通式CₙH₂ₙ₋₂与C≡C三键结构、炔烃的加成反应、炔烃在有机合成中的应用",
        keywords=["炔烃", "CₙH₂ₙ₋₂", "C≡C", "三键", "加成反应"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-02-04", name="芳香烃", level=4, parent_code="CHEM-S3-02",
        description="苯的结构(大π键/平面正六边形)、苯的取代反应(溴代/硝化)与加成反应、苯的同系物(甲苯/二甲苯)性质",
        keywords=["苯", "大π键", "芳香烃", "溴代", "硝化", "甲苯", "二甲苯", "C₆H₆", "磺化"]
    ),

    # ─── S3-03 烃的衍生物 ─────────────────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S3-03", name="烃的衍生物", level=3, parent_code="CHEM-S3",
        description="卤代烃、醇酚、醛酮、羧酸酯、胺与酰胺",
        keywords=["卤代烃", "醇", "酚", "醛", "酮", "羧酸", "酯", "胺", "酰胺"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-03-01", name="卤代烃", level=4, parent_code="CHEM-S3-03",
        description="卤代烃的结构特点与分类、取代反应(水解生成醇)、消去反应(生成烯烃)、在有机合成中的桥梁作用",
        keywords=["卤代烃", "水解", "消去反应", "NaOH水溶液", "NaOH醇溶液", "C₂H₅OH", "乙醇", "消去"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-03-02", name="醇与酚", level=4, parent_code="CHEM-S3-03",
        description="醇的分类与结构(-OH)、醇的催化氧化/消去/酯化反应、乙醇性质、酚的弱酸性与FeCl₃显色反应",
        keywords=["醇", "酚", "羟基", "-OH", "催化氧化", "消去", "酯化", "苯酚", "FeCl₃"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-03-03", name="醛与酮", level=4, parent_code="CHEM-S3-03",
        description="醛基(-CHO)结构与性质、银镜反应与新制Cu(OH)₂反应、甲醛与乙醛、酮的加成反应",
        keywords=["醛", "酮", "-CHO", "银镜反应", "Cu(OH)₂", "甲醛", "乙醛", "羰基", "CH₃COOH", "羧酸", "酯化"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-03-04", name="羧酸与酯", level=4, parent_code="CHEM-S3-03",
        description="羧基(-COOH)结构与酸性、酯化反应机理、酯的结构与水解(酸性/碱性)、油脂与皂化反应",
        keywords=["羧酸", "酯", "-COOH", "酯化反应", "水解", "油脂", "皂化", "硬化"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-03-05", name="胺与酰胺", level=4, parent_code="CHEM-S3-03",
        description="胺的结构(-NH₂)与碱性、酰胺的结构(-CONH-)与水解、氨基酸的两性与成肽反应",
        keywords=["胺", "酰胺", "-NH₂", "-CONH-", "氨基酸", "两性", "成肽反应"],
    ),

    # ─── S3-04 生物大分子与合成高分子 ─────────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHEM-S3-04", name="生物大分子与合成高分子", level=3, parent_code="CHEM-S3",
        description="糖类、蛋白质、核酸、合成高分子",
        keywords=["糖类", "蛋白质", "核酸", "合成高分子", "加聚", "缩聚", "有机合成", "逆合成", "高分子"]
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-04-01", name="糖类", level=4, parent_code="CHEM-S3-04",
        description="单糖(葡萄糖/果糖的链状与环状结构)、二糖(蔗糖/麦芽糖水解)、多糖(淀粉/纤维素结构与水解)",
        keywords=["糖类", "葡萄糖", "果糖", "蔗糖", "麦芽糖", "淀粉", "纤维素", "银镜反应"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-04-02", name="蛋白质", level=4, parent_code="CHEM-S3-04",
        description="氨基酸的结构特点(氨基与羧基)、肽键与多肽链、蛋白质的结构层次(一级→四级)、蛋白质的性质(变性/颜色反应)",
        keywords=["蛋白质", "氨基酸", "肽键", "多肽", "变性", "颜色反应"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-04-03", name="核酸", level=4, parent_code="CHEM-S3-04",
        description="核酸的基本组成(核苷酸=磷酸+五碳糖+碱基)、DNA与RNA的结构特点(双螺旋)、核酸的功能(遗传信息)",
        keywords=["核酸", "DNA", "RNA", "核苷酸", "双螺旋", "遗传信息"],
    ),
    KnowledgeTreeSeed(
        code="CHEM-S3-04-04", name="合成高分子", level=4, parent_code="CHEM-S3-04",
        description="加聚反应与缩聚反应、单体与链节/聚合度、常见合成材料(聚乙烯/聚氯乙烯/聚苯乙烯/聚酯/尼龙)、高吸水性树脂与导电高分子",
        keywords=["加聚反应", "缩聚反应", "链节", "聚合度", "聚乙烯", "聚氯乙烯", "尼龙", "功能高分子"],
    ),
]
