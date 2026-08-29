"""
政治知识树 V2 (新课标课程结构对齐)

课程模块结构 (4 必修 + 3 选必):
  POLI-C1  必修一   (中国特色社会主义)
  POLI-C2  必修二   (经济与社会)
  POLI-C3  必修三   (政治与法治)
  POLI-C4  必修四   (哲学与文化)
  POLI-S1  选必一   (当代国际政治与经济)
  POLI-S2  选必二   (法律与生活)
  POLI-S3  选必三   (逻辑与思维)

与 humanities.py (POLI-ECON / POLI-POLI / POLI-CULT / POLI-PHIL / POLI-LAW) 并行存在，
不产生 code 冲突。

编码体系:
  L2: POLI-{C|S}{册}              e.g. POLI-C1
  L3: POLI-{C|S}{册}-CH{章}       e.g. POLI-C1-CH1
  L4: POLI-{C|S}{册}-CH{章}-{节}   e.g. POLI-C1-CH1-01
"""

from __future__ import annotations

from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed

POLITICS_KNOWLEDGE_TREE_V2: list[KnowledgeTreeSeed] = [

    # ═══════════════════════════════════════════════════════════════════════════════
    #  Level 2: 课程模块 (7 册)
    # ═══════════════════════════════════════════════════════════════════════════════

    KnowledgeTreeSeed(
        code="POLI-C1",
        name="必修一 · 中国特色社会主义",
        level=2,
        parent_code="POLI",
        description="社会主义从空想到科学到实践、只有社会主义才能救中国、中国特色社会主义才能发展中国、坚持发展中国特色社会主义",
        keywords=["必修一", "社会主义", "中国特色", "科学社会主义", "民族复兴"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C2",
        name="必修二 · 经济与社会",
        level=2,
        parent_code="POLI",
        description="基本经济制度与社会主义市场经济体制、经济发展与社会进步(收入分配/社会保障)",
        keywords=["必修二", "经济制度", "市场经济", "收入分配", "社会保障"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C3",
        name="必修三 · 政治与法治",
        level=2,
        parent_code="POLI",
        description="中国共产党的领导、人民当家作主、全面依法治国",
        keywords=["必修三", "党的领导", "人民民主", "依法治国"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C4",
        name="必修四 · 哲学与文化",
        level=2,
        parent_code="POLI",
        description="探索世界与把握规律、认识社会与价值选择、文化传承与创新",
        keywords=["必修四", "哲学", "唯物辩证法", "认识论", "文化", "传承", "创新", "民族精神"]
    ),
    KnowledgeTreeSeed(
        code="POLI-S1",
        name="选必一 · 当代国际政治与经济",
        level=2,
        parent_code="POLI",
        description="各具特色的国家、国家结构形式、国际政治经济、国际组织",
        keywords=["选必一", "国家", "国际政治", "国际组织", "经济全球化"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S2",
        name="选必二 · 法律与生活",
        level=2,
        parent_code="POLI",
        description="民事权利与义务、家庭与婚姻、就业与创业、社会争议解决",
        keywords=["选必二", "民事权利", "婚姻家庭", "就业创业", "争议解决"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S3",
        name="选必三 · 逻辑与思维",
        level=2,
        parent_code="POLI",
        description="逻辑思维的基本要求、演绎推理与归纳推理、辩证思维与创新思维",
        keywords=["选必三", "逻辑", "推理", "辩证思维", "创新思维"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  POLI-C1: 必修一 · 中国特色社会主义
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 社会主义从空想到科学、从理论到实践 ─────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C1-CH1",
        name="社会主义从空想到科学、从理论到实践",
        level=3,
        parent_code="POLI-C1",
        description="空想社会主义的局限、科学社会主义的诞生、十月革命与社会主义实践",
        keywords=["空想社会主义", "科学社会主义", "十月革命", "马克思"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C1-CH1-01",
        name="空想社会主义与科学社会主义的诞生",
        level=4,
        parent_code="POLI-C1-CH1",
        description="空想社会主义(圣西门/傅立叶/欧文)的局限、马克思恩格斯创立科学社会主义、《共产党宣言》",
        keywords=["空想社会主义", "科学社会主义", "共产党宣言", "唯物史观", "剩余价值"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C1-CH1-02",
        name="十月革命与社会主义实践",
        level=4,
        parent_code="POLI-C1-CH1",
        description="十月革命(1917/第一个社会主义国家)、社会主义从一国到多国、苏联模式的经验教训",
        keywords=["十月革命", "列宁", "苏联", "社会主义国家", "苏联模式"],
    ),

    # ── 第二章: 只有社会主义才能救中国 ─────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C1-CH2",
        name="只有社会主义才能救中国",
        level=3,
        parent_code="POLI-C1",
        description="近代中国探索复兴之路、新民主主义革命、社会主义制度在中国的确立",
        keywords=["救中国", "新民主主义革命", "社会主义改造"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C1-CH2-01",
        name="新民主主义革命",
        level=4,
        parent_code="POLI-C1-CH2",
        description="近代中国的基本国情(半殖民地半封建)、各种救国方案的失败、中国共产党领导新民主主义革命胜利",
        keywords=["半殖民地半封建", "新民主主义革命", "中共领导", "革命胜利"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C1-CH2-02",
        name="社会主义制度在中国的确立",
        level=4,
        parent_code="POLI-C1-CH2",
        description="社会主义改造(1953-1956)、社会主义制度确立的伟大意义、社会主义建设的艰辛探索",
        keywords=["社会主义改造", "社会主义制度", "公有制", "计划经济"],
    ),

    # ── 第三章: 中国特色社会主义的创立与发展 ─────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C1-CH3",
        name="中国特色社会主义的创立与发展",
        level=3,
        parent_code="POLI-C1",
        description="改革开放、邓小平理论、三个代表、科学发展观、习近平新时代中国特色社会主义思想",
        keywords=["改革开放", "邓小平理论", "新时代"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C1-CH3-01",
        name="改革开放与中国特色社会主义的开创",
        level=4,
        parent_code="POLI-C1-CH3",
        description="十一届三中全会(1978)、邓小平理论(社会主义初级阶段/改革开放)、社会主义市场经济体制",
        keywords=["改革开放", "邓小平", "社会主义初级阶段", "市场经济"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C1-CH3-02",
        name="中国特色社会主义进入新时代",
        level=4,
        parent_code="POLI-C1-CH3",
        description="新时代的历史方位、习近平新时代中国特色社会主义思想、新时代社会主要矛盾的转化",
        keywords=["新时代", "习近平新时代", "主要矛盾", "中国梦", "民族复兴"],
    ),

    # ── 第四章: 坚持和发展中国特色社会主义 ─────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C1-CH4",
        name="坚持和发展中国特色社会主义",
        level=3,
        parent_code="POLI-C1",
        description="中国特色社会主义道路、理论、制度、文化自信、实现中华民族伟大复兴",
        keywords=["四个自信", "道路", "理论", "制度", "文化", "民族复兴", "国际", "政治", "民主"]
    ),
    KnowledgeTreeSeed(
        code="POLI-C1-CH4-01",
        name="中国特色社会主义道路理论制度文化",
        level=4,
        parent_code="POLI-C1-CH4",
        description="中国特色社会主义道路(路径)、理论体系(指导)、制度(保障)、文化(精神力量)",
        keywords=["中国道路", "理论体系", "制度优势", "文化自信"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C1-CH4-02",
        name="实现中华民族伟大复兴的中国梦",
        level=4,
        parent_code="POLI-C1-CH4",
        description="中国梦的内涵(国家富强/民族振兴/人民幸福)、两步走战略、新时代青年的使命担当",
        keywords=["中国梦", "两步走", "国家富强", "民族振兴", "青年使命"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  POLI-C2: 必修二 · 经济与社会
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 我国的基本经济制度 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C2-CH1",
        name="我国的基本经济制度",
        level=3,
        parent_code="POLI-C2",
        description="公有制为主体多种所有制经济共同发展、社会主义市场经济体制",
        keywords=["基本经济制度", "所有制", "市场经济", "消费", "生产"]
    ),
    KnowledgeTreeSeed(
        code="POLI-C2-CH1-01",
        name="公有制为主体、多种所有制经济共同发展",
        level=4,
        parent_code="POLI-C2-CH1",
        description="公有制经济(国有经济/集体经济/混合所有制中的国有和集体成分)、非公有制经济(个体/私营/外资)、两个毫不动摇",
        keywords=["公有制", "国有经济", "集体经济", "非公有制", "两个毫不动摇"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C2-CH1-02",
        name="社会主义市场经济体制",
        level=4,
        parent_code="POLI-C2-CH1",
        description="市场经济的一般规律(供求/价格/竞争)、社会主义市场经济的基本特征(公有制/共同富裕/宏观调控)",
        keywords=["市场经济", "供求关系", "宏观调控", "社会主义市场经济", "市场调节", "市场", "市场失灵"]
    ),

    # ── 第二章: 我国的经济发展与社会进步 ─────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C2-CH2",
        name="我国的经济发展与社会进步",
        level=3,
        parent_code="POLI-C2",
        description="新发展理念与新发展格局、个人收入分配与社会保障",
        keywords=["新发展理念", "收入分配", "社会保障", "共同富裕"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C2-CH2-01",
        name="新发展理念与新发展格局",
        level=4,
        parent_code="POLI-C2-CH2",
        description="新发展理念(创新/协调/绿色/开放/共享)、新发展格局(以国内大循环为主体)、高质量发展",
        keywords=["新发展理念", "新发展格局", "高质量发展", "双循环", "供给侧结构性改革", "全球化", "开放"]
    ),
    KnowledgeTreeSeed(
        code="POLI-C2-CH2-02",
        name="个人收入分配与社会保障",
        level=4,
        parent_code="POLI-C2-CH2",
        description="按劳分配为主体多种分配方式并存、效率与公平、社会保障体系(养老/医疗/失业/最低生活保障)",
        keywords=["按劳分配", "效率与公平", "社会保障", "养老保险", "医疗保险", "共同富裕", "公平", "分配", "效率", "税收", "财政"]
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  POLI-C3: 必修三 · 政治与法治
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 中国共产党的领导 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C3-CH1",
        name="中国共产党的领导",
        level=3,
        parent_code="POLI-C3",
        description="历史和人民的选择、中国共产党的先进性、坚持和加强党的全面领导",
        keywords=["党的领导", "历史选择", "先进性", "全面领导"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH1-01",
        name="历史和人民的选择",
        level=4,
        parent_code="POLI-C3-CH1",
        description="中国共产党执政是历史和人民的选择、没有共产党就没有新中国、党的领导是中国特色社会主义最本质的特征",
        keywords=["历史选择", "人民选择", "最本质特征", "最大优势"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH1-02",
        name="中国共产党的先进性",
        level=4,
        parent_code="POLI-C3-CH1",
        description="党的性质(两个先锋队)、党的宗旨(全心全意为人民服务)、党的指导思想(马克思主义中国化)",
        keywords=["先锋队", "为人民服务", "指导思想", "立党为公", "执政为民"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH1-03",
        name="坚持和加强党的全面领导",
        level=4,
        parent_code="POLI-C3-CH1",
        description="党的领导方式(政治/思想/组织)、全面从严治党、党的领导与依法治国的统一",
        keywords=["全面领导", "从严治党", "政治领导", "思想领导", "组织领导"],
    ),

    # ── 第二章: 人民当家作主 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C3-CH2",
        name="人民当家作主",
        level=3,
        parent_code="POLI-C3",
        description="人民民主专政、人民代表大会制度、政党制度、民族区域自治、基层群众自治",
        keywords=["人民民主", "人大制度", "政党制度", "基层自治"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH2-01",
        name="人民民主专政的国体",
        level=4,
        parent_code="POLI-C3-CH2",
        description="我国的国体(人民民主专政)、人民民主的特点(最广泛/最真实/最管用)、公民的政治权利与义务",
        keywords=["人民民主专政", "国体", "政治权利", "政治义务", "民主"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH2-02",
        name="人民代表大会制度",
        level=4,
        parent_code="POLI-C3-CH2",
        description="人民代表大会制度是我国的政体、全国人大的地位与职权(立法/决定/任免/监督)、人大代表的权利与义务",
        keywords=["人大制度", "政体", "全国人大", "人大代表", "立法权", "监督权", "政治制度", "民主"]
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH2-03",
        name="中国共产党领导的多党合作和政治协商制度",
        level=4,
        parent_code="POLI-C3-CH2",
        description="政党制度的基本内容(友党关系/政治准则/基本方针)、人民政协的性质与职能(政治协商/民主监督/参政议政)",
        keywords=["多党合作", "政治协商", "人民政协", "民主党派", "参政议政"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH2-04",
        name="民族区域自治制度与基层群众自治",
        level=4,
        parent_code="POLI-C3-CH2",
        description="民族区域自治制度(自治区/州/县)、基层群众自治(村委会/居委会)、社会主义民主的广泛实践",
        keywords=["民族区域自治", "自治机关", "村委会", "居委会", "基层民主"],
    ),

    # ── 第三章: 全面依法治国 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C3-CH3",
        name="全面依法治国",
        level=3,
        parent_code="POLI-C3",
        description="治国理政的基本方式(法治)、法治中国建设、全面依法治国的基本要求",
        keywords=["依法治国", "法治", "宪法", "法治中国"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH3-01",
        name="治国理政的基本方式",
        level=4,
        parent_code="POLI-C3-CH3",
        description="法治与人治的区别、我国法治建设的历程、全面推进依法治国的总目标(建设中国特色社会主义法治体系)",
        keywords=["法治", "人治", "依法治国", "法治体系", "法治国家"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH3-02",
        name="法治中国建设",
        level=4,
        parent_code="POLI-C3-CH3",
        description="法治国家(宪法至上)、法治政府(依法行政)、法治社会(全民守法)",
        keywords=["法治国家", "法治政府", "法治社会", "宪法至上", "依法行政", "政府", "治理"]
    ),
    KnowledgeTreeSeed(
        code="POLI-C3-CH3-03",
        name="全面依法治国的基本要求",
        level=4,
        parent_code="POLI-C3-CH3",
        description="科学立法/严格执法/公正司法/全民守法、法治与德治相结合",
        keywords=["科学立法", "严格执法", "公正司法", "全民守法", "法治德治结合"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  POLI-C4: 必修四 · 哲学与文化
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 探索世界与把握规律 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C4-CH1",
        name="探索世界与把握规律",
        level=3,
        parent_code="POLI-C4",
        description="时代精神的精华(哲学基本问题)、探究世界的本质(唯物论)、把握世界的规律(辩证法)",
        keywords=["哲学", "唯物论", "辩证法", "物质", "意识", "规律", "唯物", "实践", "矛盾"]
    ),
    KnowledgeTreeSeed(
        code="POLI-C4-CH1-01",
        name="时代精神的精华",
        level=4,
        parent_code="POLI-C4-CH1",
        description="哲学的基本问题(思维与存在/物质与意识)、唯物主义与唯心主义、马克思主义哲学的基本特征",
        keywords=["哲学基本问题", "唯物主义", "唯心主义", "马克思主义哲学"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C4-CH1-02",
        name="探究世界的本质",
        level=4,
        parent_code="POLI-C4-CH1",
        description="世界的物质性(物质决定意识)、意识的本质(人脑对客观存在的反映)、物质与意识的辩证关系、一切从实际出发",
        keywords=["物质", "意识", "物质决定意识", "意识能动作用", "一切从实际出发"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C4-CH1-03",
        name="把握世界的规律",
        level=4,
        parent_code="POLI-C4-CH1",
        description="联系观(普遍性/客观性/多样性/整体与部分)、发展观(量变质变/前进性与曲折性)、矛盾观(对立统一/普遍性与特殊性/主次矛盾)",
        keywords=["联系", "发展", "矛盾", "对立统一", "量变质变", "否定之否定", "否定", "辩证法"]
    ),

    # ── 第二章: 认识社会与价值选择 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C4-CH2",
        name="认识社会与价值选择",
        level=3,
        parent_code="POLI-C4",
        description="认识的奥秘(认识论)、社会历史的真谛(唯物史观)、实现人生的价值(价值观)",
        keywords=["认识论", "唯物史观", "价值观", "实践"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C4-CH2-01",
        name="认识的奥秘",
        level=4,
        parent_code="POLI-C4-CH2",
        description="实践是认识的基础(来源/动力/检验标准/目的)、真理的客观性/条件性/具体性、认识的反复性/无限性/上升性",
        keywords=["实践", "认识", "真理", "感性认识", "理性认识", "认识规律", "认识论"]
    ),
    KnowledgeTreeSeed(
        code="POLI-C4-CH2-02",
        name="社会历史的真谛",
        level=4,
        parent_code="POLI-C4-CH2",
        description="社会存在与社会意识的辩证关系、生产力与生产关系/经济基础与上层建筑、人民群众是历史的创造者",
        keywords=["社会存在", "社会意识", "生产力", "生产关系", "人民群众"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C4-CH2-03",
        name="实现人生的价值",
        level=4,
        parent_code="POLI-C4-CH2",
        description="价值与价值观(社会主义核心价值观)、价值判断与价值选择(自觉遵循规律/自觉站在人民立场)、人生价值的实现(劳动与奉献)",
        keywords=["价值观", "核心价值观", "价值判断", "价值选择", "人生价值", "劳动奉献"],
    ),

    # ── 第三章: 文化传承与文化创新 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-C4-CH3",
        name="文化传承与文化创新",
        level=3,
        parent_code="POLI-C4",
        description="中华优秀传统文化、外来文化有益成果、发展中国特色社会主义文化",
        keywords=["文化传承", "传统文化", "外来文化", "文化创新", "传承", "创新", "多样性", "文化作用", "继承", "软实力"]
    ),
    KnowledgeTreeSeed(
        code="POLI-C4-CH3-01",
        name="中华优秀传统文化",
        level=4,
        parent_code="POLI-C4-CH3",
        description="中华文化的特点(源远流长/博大精深)、中华优秀传统文化的当代价值、创造性转化与创新性发展",
        keywords=["中华文化", "源远流长", "博大精深", "创造性转化", "文化自信", "核心价值观", "民族精神", "爱国主义"]
    ),
    KnowledgeTreeSeed(
        code="POLI-C4-CH3-02",
        name="学习借鉴外来文化有益成果",
        level=4,
        parent_code="POLI-C4-CH3",
        description="文化的多样性与文化交流、面向世界博采众长、以我为主为我所用",
        keywords=["文化多样性", "文化交流", "博采众长", "以我为主"],
    ),
    KnowledgeTreeSeed(
        code="POLI-C4-CH3-03",
        name="发展中国特色社会主义文化",
        level=4,
        parent_code="POLI-C4-CH3",
        description="中国特色社会主义文化的内涵、文化强国建设、坚定文化自信",
        keywords=["中国特色社会主义文化", "文化强国", "文化自信", "意识形态"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  POLI-S1: 选必一 · 当代国际政治与经济
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 各具特色的国家 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S1-CH1",
        name="各具特色的国家",
        level=3,
        parent_code="POLI-S1",
        description="国体与政体、国家的管理形式(民主共和/君主立宪)、政党制度",
        keywords=["国体", "政体", "民主共和", "君主立宪", "政党"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S1-CH1-01",
        name="国体与政体",
        level=4,
        parent_code="POLI-S1-CH1",
        description="国体(国家的阶级本质)与政体(政权组织形式)的关系、代议制是现代政治管理的基本形式",
        keywords=["国体", "政体", "代议制", "统治阶级", "政权组织形式"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S1-CH1-02",
        name="国家的管理形式与政党制度",
        level=4,
        parent_code="POLI-S1-CH1",
        description="民主共和制与君主立宪制、议会制与总统制、一党制/两党制/多党制的比较",
        keywords=["共和制", "君主立宪", "议会制", "总统制", "两党制", "多党制"],
    ),

    # ── 第二章: 国家的结构形式 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S1-CH2",
        name="国家的结构形式",
        level=3,
        parent_code="POLI-S1",
        description="单一制与联邦制、中央与地方的关系、国家主权",
        keywords=["单一制", "联邦制", "中央地方关系", "主权"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S1-CH2-01",
        name="单一制与联邦制",
        level=4,
        parent_code="POLI-S1-CH2",
        description="单一制国家(中央统一领导/地方服从中央)、联邦制国家(联邦与成员单位分权)、两种结构形式的比较",
        keywords=["单一制", "联邦制", "中央集权", "分权", "地方自治"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S1-CH2-02",
        name="国家主权与国际关系",
        level=4,
        parent_code="POLI-S1-CH2",
        description="国家主权的含义(对内最高/对外独立)、主权国家的权利与义务、国际关系的决定因素(国家利益)",
        keywords=["国家主权", "主权国家", "国家利益", "国际关系", "综合国力"],
    ),

    # ── 第三章: 国际政治经济 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S1-CH3",
        name="国际政治经济",
        level=3,
        parent_code="POLI-S1",
        description="和平与发展是时代主题、经济全球化、世界多极化趋势",
        keywords=["和平与发展", "经济全球化", "多极化", "霸权主义", "公民", "市场", "权利", "消费", "生产", "监督", "经济", "选举"]
    ),
    KnowledgeTreeSeed(
        code="POLI-S1-CH3-01",
        name="和平与发展",
        level=4,
        parent_code="POLI-S1-CH3",
        description="和平与发展是当今时代主题、霸权主义与强权政治是主要障碍、建立国际新秩序",
        keywords=["和平与发展", "霸权主义", "强权政治", "国际新秩序", "全球治理"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S1-CH3-02",
        name="经济全球化与世界多极化",
        level=4,
        parent_code="POLI-S1-CH3",
        description="经济全球化的表现与影响(机遇与挑战)、世界多极化趋势(多种力量中心)、中国的大国外交",
        keywords=["经济全球化", "多极化", "机遇与挑战", "中国外交", "人类命运共同体"],
    ),

    # ── 第四章: 国际组织 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S1-CH4",
        name="国际组织",
        level=3,
        parent_code="POLI-S1",
        description="国际组织的分类与作用、联合国、区域性国际组织",
        keywords=["国际组织", "联合国", "安理会", "区域性组织", "国际", "外交"]
    ),
    KnowledgeTreeSeed(
        code="POLI-S1-CH4-01",
        name="国际组织概览",
        level=4,
        parent_code="POLI-S1-CH4",
        description="国际组织的分类(政府间/非政府间/全球性/区域性)、国际组织的作用(促进合作/维护和平)",
        keywords=["国际组织", "政府间", "非政府间", "全球性", "区域性"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S1-CH4-02",
        name="联合国与区域性国际组织",
        level=4,
        parent_code="POLI-S1-CH4",
        description="联合国的宗旨/原则/主要机构(大会/安理会/经社理事会)、中国与联合国、欧盟/非盟/东盟等",
        keywords=["联合国", "安理会", "欧盟", "非盟", "东盟", "中国与联合国"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  POLI-S2: 选必二 · 法律与生活
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 民事权利与义务 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S2-CH1",
        name="民事权利与义务",
        level=3,
        parent_code="POLI-S2",
        description="民法的基本原则、人身权、财产权、合同与侵权责任",
        keywords=["民事权利", "民法", "人身权", "财产权", "合同", "侵权", "法律"]
    ),
    KnowledgeTreeSeed(
        code="POLI-S2-CH1-01",
        name="民法的基本原则与人身权",
        level=4,
        parent_code="POLI-S2-CH1",
        description="民法的基本原则(平等/自愿/公平/诚信/公序良俗/绿色)、生命权/健康权/姓名权/肖像权/名誉权/隐私权",
        keywords=["民法原则", "人身权", "生命权", "肖像权", "隐私权", "名誉权"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S2-CH1-02",
        name="财产权与合同",
        level=4,
        parent_code="POLI-S2-CH1",
        description="物权(所有权/用益物权/担保物权)、知识产权(著作权/专利权/商标权)、合同的订立与履行",
        keywords=["物权", "所有权", "知识产权", "著作权", "专利权", "合同"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S2-CH1-03",
        name="侵权责任",
        level=4,
        parent_code="POLI-S2-CH1",
        description="侵权行为的构成要件、过错责任与无过错责任、侵权责任的承担方式(赔偿/道歉/恢复原状)",
        keywords=["侵权责任", "过错责任", "无过错责任", "赔偿损失", "侵权行为"],
    ),

    # ── 第二章: 家庭与婚姻 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S2-CH2",
        name="家庭与婚姻",
        level=3,
        parent_code="POLI-S2",
        description="父母子女关系、婚姻关系的法律规范、继承制度",
        keywords=["家庭", "婚姻", "继承", "父母子女"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S2-CH2-01",
        name="父母子女关系与婚姻",
        level=4,
        parent_code="POLI-S2-CH2",
        description="父母对子女的抚养教育义务、子女对父母的赡养扶助义务、结婚的条件与程序、离婚的法律后果",
        keywords=["抚养", "赡养", "结婚条件", "离婚", "家庭关系"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S2-CH2-02",
        name="继承制度",
        level=4,
        parent_code="POLI-S2-CH2",
        description="法定继承(继承顺序与份额)、遗嘱继承(遗嘱的形式与效力)、遗赠与遗赠扶养协议",
        keywords=["法定继承", "遗嘱继承", "继承顺序", "遗赠", "遗产"],
    ),

    # ── 第三章: 就业与创业 ─────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S2-CH3",
        name="就业与创业",
        level=3,
        parent_code="POLI-S2",
        description="劳动者的权利与义务、劳动合同、创业的法律保障",
        keywords=["就业", "劳动权利", "劳动合同", "创业"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S2-CH3-01",
        name="劳动者的权利与义务",
        level=4,
        parent_code="POLI-S2-CH3",
        description="劳动者的权利(平等就业/取得报酬/休息休假/劳动安全)、劳动者的义务、劳动争议的解决途径",
        keywords=["劳动权利", "劳动义务", "劳动安全", "劳动争议", "仲裁"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S2-CH3-02",
        name="劳动合同与创业",
        level=4,
        parent_code="POLI-S2-CH3",
        description="劳动合同的订立/内容/变更/解除、创业的法律形式(个体/合伙/公司)、知识产权保护",
        keywords=["劳动合同", "五险一金", "创业", "公司法", "知识产权"],
    ),

    # ── 第四章: 社会争议解决 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S2-CH4",
        name="社会争议解决",
        level=3,
        parent_code="POLI-S2",
        description="调解与仲裁、诉讼(民事/刑事/行政)、证据与法律援助",
        keywords=["调解", "仲裁", "诉讼", "证据", "法律援助"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S2-CH4-01",
        name="调解与仲裁",
        level=4,
        parent_code="POLI-S2-CH4",
        description="调解(人民调解/行政调解/司法调解)、仲裁(商事仲裁/劳动仲裁)、调解与仲裁的特点与适用",
        keywords=["调解", "仲裁", "人民调解", "商事仲裁", "劳动仲裁"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S2-CH4-02",
        name="诉讼与法律援助",
        level=4,
        parent_code="POLI-S2-CH4",
        description="诉讼的类型(民事/刑事/行政)、诉讼程序(起诉/受理/审理/判决)、证据制度、法律援助制度",
        keywords=["诉讼", "民事诉讼", "刑事诉讼", "行政诉讼", "证据", "法律援助"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  POLI-S3: 选必三 · 逻辑与思维
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 逻辑思维的基本要求 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S3-CH1",
        name="逻辑思维的基本要求",
        level=3,
        parent_code="POLI-S3",
        description="概念(内涵与外延)、判断(性质/关系/联言/选言/假言)、逻辑思维的基本规律",
        keywords=["概念", "判断", "逻辑规律", "同一律", "矛盾律"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S3-CH1-01",
        name="概念与判断",
        level=4,
        parent_code="POLI-S3-CH1",
        description="概念的内涵与外延、概念间的关系(全同/属种/交叉/矛盾/反对)、判断的类型与真假",
        keywords=["内涵", "外延", "属种关系", "矛盾关系", "判断", "真判断"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S3-CH1-02",
        name="逻辑思维的基本规律",
        level=4,
        parent_code="POLI-S3-CH1",
        description="同一律(思维的确定性)、矛盾律(思维的一致性)、排中律(思维的明确性)、充足理由律",
        keywords=["同一律", "矛盾律", "排中律", "充足理由律", "偷换概念", "自相矛盾"],
    ),

    # ── 第二章: 演绎推理与归纳推理 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S3-CH2",
        name="演绎推理与归纳推理",
        level=3,
        parent_code="POLI-S3",
        description="演绎推理(三段论/假言推理/选言推理)、归纳推理(完全/不完全)、类比推理",
        keywords=["演绎推理", "归纳推理", "类比推理", "三段论"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S3-CH2-01",
        name="演绎推理",
        level=4,
        parent_code="POLI-S3-CH2",
        description="三段论(大前提/小前提/结论)、假言推理(充分/必要条件)、选言推理(相容/不相容)",
        keywords=["三段论", "假言推理", "选言推理", "大前提", "小前提", "演绎"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S3-CH2-02",
        name="归纳推理与类比推理",
        level=4,
        parent_code="POLI-S3-CH2",
        description="完全归纳推理与不完全归纳推理(简单枚举/科学归纳)、类比推理的方法与可靠性",
        keywords=["归纳推理", "完全归纳", "不完全归纳", "类比推理", "科学归纳"],
    ),

    # ── 第三章: 辩证思维与创新思维 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="POLI-S3-CH3",
        name="辩证思维与创新思维",
        level=3,
        parent_code="POLI-S3",
        description="辩证思维(分析与综合/归纳与演绎)、创新思维(发散/聚合/逆向)、联想思维",
        keywords=["辩证思维", "创新思维", "分析综合", "发散思维"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S3-CH3-01",
        name="辩证思维",
        level=4,
        parent_code="POLI-S3-CH3",
        description="辩证思维的特征(整体性/动态性)、分析与综合的方法、归纳与演绎的辩证统一",
        keywords=["辩证思维", "分析", "综合", "整体性", "动态性"],
    ),
    KnowledgeTreeSeed(
        code="POLI-S3-CH3-02",
        name="创新思维",
        level=4,
        parent_code="POLI-S3-CH3",
        description="发散思维(一题多解)、聚合思维(多题一解)、逆向思维(反向思考)、联想思维与头脑风暴",
        keywords=["发散思维", "聚合思维", "逆向思维", "联想思维", "头脑风暴", "创新"],
    ),
]
