"""
历史知识树 V2 (新课标课程结构对齐)

课程模块结构 (5 册 + 3 选必):
  HIST-C1  纲要上   (中国历史: 中华文明起源 → 改革开放)
  HIST-C2  纲要下   (世界历史: 古代文明 → 当代世界)
  HIST-S1  选必一   (国家制度与社会治理)
  HIST-S2  选必二   (经济与社会生活)
  HIST-S3  选必三   (文化交流与传播)

与 humanities.py (HIST-ANCI / HIST-MODN / HIST-WRLD) 并行存在，
不产生 code 冲突。

编码体系:
  L2: HIST-{C|S}{册}              e.g. HIST-C1
  L3: HIST-{C|S}{册}-CH{章}       e.g. HIST-C1-CH1
  L4: HIST-{C|S}{册}-CH{章}-{节}   e.g. HIST-C1-CH1-01
"""

from __future__ import annotations

from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed

HISTORY_KNOWLEDGE_TREE_V2: list[KnowledgeTreeSeed] = [

    # ═══════════════════════════════════════════════════════════════════════════════
    #  Level 2: 课程模块
    # ═══════════════════════════════════════════════════════════════════════════════

    KnowledgeTreeSeed(
        code="HIST-C1",
        name="中外历史纲要(上)",
        level=2,
        parent_code="HIST",
        description="中国历史: 中华文明起源与早期国家、统一多民族国家的发展、近代内忧外患与救亡图存、新中国建设与改革开放",
        keywords=["纲要上", "中国古代史", "中国近代史", "中国现代史", "革命", "唐宋", "建设", "改革", "科举", "经济重心", "近代", "魏晋"]
    ),
    KnowledgeTreeSeed(
        code="HIST-C2",
        name="中外历史纲要(下)",
        level=2,
        parent_code="HIST",
        description="世界历史: 古代文明、中古时期、走向整体的世界、资本主义、工业革命、世界大战、当代世界",
        keywords=["纲要下", "世界史", "古代文明", "工业革命", "世界大战", "全球化", "世界", "战争"]
    ),
    KnowledgeTreeSeed(
        code="HIST-S1",
        name="选必一 · 国家制度与社会治理",
        level=2,
        parent_code="HIST",
        description="政治制度、官员选拔与管理、法律与教化、民族关系与国家关系、货币与赋税、基层治理与社会保障",
        keywords=["选必一", "政治制度", "法律", "赋税", "基层治理"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2",
        name="选必二 · 经济与社会生活",
        level=2,
        parent_code="HIST",
        description="食物生产与劳作、商业贸易、村落城镇、交通变迁、医疗公共卫生",
        keywords=["选必二", "农业", "商业", "交通", "城市", "医疗"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3",
        name="选必三 · 文化交流与传播",
        level=2,
        parent_code="HIST",
        description="中华文化、世界文化、人口迁徙与文化交融、商路与文化交流、战争与文化交锋、文化传承保护",
        keywords=["选必三", "文化", "迁徙", "商路", "战争", "传承"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  HIST-C1: 中外历史纲要(上)
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 中华文明的起源与早期国家 ─────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH1",
        name="中华文明的起源与早期国家",
        level=3,
        parent_code="HIST-C1",
        description="石器时代文化遗存、夏商周的更替、西周分封制与宗法制、春秋战国大变革",
        keywords=["石器时代", "夏商周", "分封制", "宗法制", "百家争鸣"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH1-01",
        name="中华文明的起源",
        level=4,
        parent_code="HIST-C1-CH1",
        description="旧石器时代(元谋人/北京人)与新石器时代(仰韶/龙山/河姆渡)、中华文明多元一体的起源特征",
        keywords=["旧石器时代", "新石器时代", "仰韶文化", "龙山文化", "多元一体"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH1-02",
        name="早期国家的形成",
        level=4,
        parent_code="HIST-C1-CH1",
        description="夏朝建立(第一个王朝)、商朝(甲骨文/青铜器)、西周(分封制/宗法制/礼乐制)",
        keywords=["夏朝", "商朝", "甲骨文", "青铜器", "西周", "分封制", "宗法制"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH1-03",
        name="春秋战国时期的变革",
        level=4,
        parent_code="HIST-C1-CH1",
        description="春秋五霸与战国七雄、铁犁牛耕与井田制瓦解、百家争鸣(儒/道/法/墨)、各国变法",
        keywords=["春秋战国", "铁犁牛耕", "井田制", "百家争鸣", "商鞅变法", "先秦", "战国", "春秋"]
    ),

    # ── 第二章: 秦汉统一多民族封建国家的建立与巩固 ─────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH2",
        name="秦汉统一多民族封建国家的建立与巩固",
        level=3,
        parent_code="HIST-C1",
        description="秦朝统一与中央集权制度、两汉政治经济文化、丝绸之路",
        keywords=["秦朝", "汉朝", "中央集权", "丝绸之路", "大一统", "秦汉"]
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH2-01",
        name="秦朝的统一与制度",
        level=4,
        parent_code="HIST-C1-CH2",
        description="秦灭六国与统一措施(书同文/车同轨/统一度量衡)、皇帝制度、三公九卿、郡县制",
        keywords=["秦始皇", "皇帝制度", "三公九卿", "郡县制", "书同文", "焚书坑儒"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH2-02",
        name="两汉的统治",
        level=4,
        parent_code="HIST-C1-CH2",
        description="西汉(郡国并行/推恩令/独尊儒术/盐铁官营)、东汉(外戚宦官交替专权)、丝绸之路与对外交流",
        keywords=["西汉", "推恩令", "独尊儒术", "盐铁官营", "丝绸之路", "张骞"],
    ),

    # ── 第三章: 三国两晋南北朝的民族交融与隋唐统一 ─────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH3",
        name="三国两晋南北朝的民族交融与隋唐统一",
        level=3,
        parent_code="HIST-C1",
        description="三国鼎立、西晋统一与五胡乱华、南北朝民族交融、隋唐大一统与繁荣",
        keywords=["三国", "南北朝", "民族交融", "隋朝", "唐朝"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH3-01",
        name="三国两晋南北朝",
        level=4,
        parent_code="HIST-C1-CH3",
        description="三国鼎立(魏蜀吴)、西晋短暂统一、东晋十六国与南北朝、北魏孝文帝改革(汉化)",
        keywords=["三国鼎立", "西晋", "东晋", "南北朝", "孝文帝改革", "均田制"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH3-02",
        name="隋唐的繁荣",
        level=4,
        parent_code="HIST-C1-CH3",
        description="隋朝统一与大运河、唐朝贞观之治与开元盛世、三省六部制与科举制、唐对外文化交流",
        keywords=["隋朝", "大运河", "贞观之治", "开元盛世", "三省六部", "科举制"],
    ),

    # ── 第四章: 辽宋夏金元多民族政权并立与统一 ─────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH4",
        name="辽宋夏金元多民族政权并立与统一",
        level=3,
        parent_code="HIST-C1",
        description="两宋的政治军事经济、辽夏金的崛起、元朝的大一统",
        keywords=["宋朝", "辽", "西夏", "金", "元朝", "经济重心南移"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH4-01",
        name="两宋的政治与经济",
        level=4,
        parent_code="HIST-C1-CH4",
        description="北宋(中央集权强化/王安石变法)、南宋(偏安江南)、宋代商品经济繁荣(交子/市舶司)、经济重心南移",
        keywords=["北宋", "王安石变法", "南宋", "商品经济", "交子", "经济重心南移"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH4-02",
        name="辽夏金元的统治",
        level=4,
        parent_code="HIST-C1-CH4",
        description="辽(南北面官)、西夏、金(猛安谋克)、蒙古崛起与元朝统一、行省制度、民族融合",
        keywords=["辽", "南北面官", "猛安谋克", "成吉思汗", "忽必烈", "行省制"],
    ),

    # ── 第五章: 明清中国版图的奠定与社会危机 ─────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH5",
        name="明清中国版图的奠定与社会危机",
        level=3,
        parent_code="HIST-C1",
        description="明朝政治与经济、清朝前中期的鼎盛与危机、思想文化",
        keywords=["明朝", "清朝", "君主专制", "闭关锁国", "资本主义萌芽"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH5-01",
        name="明朝的统治",
        level=4,
        parent_code="HIST-C1-CH5",
        description="废丞相设内阁、厂卫制度、郑和下西洋、海禁政策、商品经济发展与资本主义萌芽",
        keywords=["朱元璋", "内阁", "厂卫", "郑和下西洋", "海禁", "资本主义萌芽"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH5-02",
        name="清朝前中期的统治",
        level=4,
        parent_code="HIST-C1-CH5",
        description="军机处与君主专制强化、康乾盛世、版图奠定(台湾/西藏/新疆/蒙古)、闭关锁国",
        keywords=["军机处", "康乾盛世", "雍正", "闭关锁国", "版图奠定"],
    ),

    # ── 第六章: 晚清时期的内忧外患 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH6",
        name="晚清时期的内忧外患",
        level=3,
        parent_code="HIST-C1",
        description="鸦片战争、太平天国运动、洋务运动、甲午战争与戊戌变法、八国联军侵华",
        keywords=["鸦片战争", "太平天国", "洋务运动", "甲午战争", "戊戌变法", "专制顶峰", "戊戌", "明清", "洋务", "辛亥", "闭关"]
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH6-01",
        name="两次鸦片战争",
        level=4,
        parent_code="HIST-C1-CH6",
        description="第一次鸦片战争(1840-1842/南京条约)、第二次鸦片战争(1856-1860/天津条约/北京条约)",
        keywords=["鸦片战争", "林则徐", "南京条约", "半殖民地半封建", "第二次鸦片战争"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH6-02",
        name="太平天国与洋务运动",
        level=4,
        parent_code="HIST-C1-CH6",
        description="太平天国运动(天朝田亩制度/资政新篇)、洋务运动(自强求富/中体西用/近代化起步)",
        keywords=["太平天国", "洪秀全", "洋务运动", "自强求富", "中体西用", "李鸿章"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH6-03",
        name="甲午战争与戊戌变法",
        level=4,
        parent_code="HIST-C1-CH6",
        description="甲午中日战争(1894-1895/马关条约)、列强瓜分中国(租借地/势力范围)、戊戌变法(百日维新)",
        keywords=["甲午战争", "马关条约", "戊戌变法", "百日维新", "康有为", "梁启超"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH6-04",
        name="八国联军侵华与清末新政",
        level=4,
        parent_code="HIST-C1-CH6",
        description="义和团运动、八国联军侵华(1900/辛丑条约)、清末新政与预备立宪",
        keywords=["义和团", "八国联军", "辛丑条约", "清末新政", "预备立宪"],
    ),

    # ── 第七章: 辛亥革命与中华民国的建立 ─────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH7",
        name="辛亥革命与中华民国的建立",
        level=3,
        parent_code="HIST-C1",
        description="辛亥革命与民国建立、北洋军阀统治、新文化运动与五四运动",
        keywords=["辛亥革命", "孙中山", "民国", "北洋军阀", "新文化运动", "五四运动", "五四", "抗日", "解放"]
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH7-01",
        name="辛亥革命",
        level=4,
        parent_code="HIST-C1-CH7",
        description="同盟会与三民主义、武昌起义(1911)、中华民国成立、清帝退位、《中华民国临时约法》",
        keywords=["同盟会", "三民主义", "武昌起义", "辛亥革命", "临时约法", "袁世凯"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH7-02",
        name="北洋军阀统治与新文化运动",
        level=4,
        parent_code="HIST-C1-CH7",
        description="袁世凯独裁与复辟、军阀割据、新文化运动(民主与科学)、五四运动(1919/反帝反封建)",
        keywords=["北洋军阀", "袁世凯", "新文化运动", "陈独秀", "民主科学", "五四运动"],
    ),

    # ── 第八章: 中国共产党的成立与新民主主义革命 ─────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH8",
        name="中国共产党的成立与新民主主义革命",
        level=3,
        parent_code="HIST-C1",
        description="中共成立、国民革命、土地革命、长征",
        keywords=["中共", "国民革命", "土地革命", "长征", "南昌起义"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH8-01",
        name="中国共产党的诞生",
        level=4,
        parent_code="HIST-C1-CH8",
        description="马克思主义传播、中共一大(1921/上海)、中共二大(民主革命纲领)、工人运动高潮",
        keywords=["中共一大", "马克思主义", "陈独秀", "李大钊", "民主革命纲领"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH8-02",
        name="国民革命",
        level=4,
        parent_code="HIST-C1-CH8",
        description="国共第一次合作(1924)、黄埔军校、北伐战争(1926-1927)、四一二与七一五反革命政变",
        keywords=["国共合作", "黄埔军校", "北伐战争", "四一二政变", "国民革命"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH8-03",
        name="土地革命与红军长征",
        level=4,
        parent_code="HIST-C1-CH8",
        description="南昌起义(1927)、秋收起义、井冈山革命根据地、工农武装割据、红军长征(1934-1936/遵义会议)",
        keywords=["南昌起义", "秋收起义", "井冈山", "工农武装割据", "长征", "遵义会议"],
    ),

    # ── 第九章: 抗日战争与解放战争 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH9",
        name="抗日战争与解放战争",
        level=3,
        parent_code="HIST-C1",
        description="抗日战争(局部抗战/全面抗战)、解放战争(重庆谈判/三大战役/渡江战役)",
        keywords=["抗日战争", "解放战争", "国共内战"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH9-01",
        name="抗日战争",
        level=4,
        parent_code="HIST-C1-CH9",
        description="局部抗战(九一八/一二八/华北事变)、全面抗战(卢沟桥事变/国共第二次合作)、正面战场与敌后战场、抗战胜利",
        keywords=["九一八事变", "卢沟桥事变", "全面抗战", "正面战场", "敌后战场", "抗战胜利"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH9-02",
        name="解放战争",
        level=4,
        parent_code="HIST-C1-CH9",
        description="重庆谈判与双十协定、全面内战爆发、三大战役(辽沈/淮海/平津)、渡江战役与南京解放",
        keywords=["重庆谈判", "三大战役", "辽沈战役", "淮海战役", "渡江战役", "南京解放"],
    ),

    # ── 第十章: 中华人民共和国的成立与社会主义建设 ─────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH10",
        name="中华人民共和国的成立与社会主义建设",
        level=3,
        parent_code="HIST-C1",
        description="新中国成立、社会主义制度确立、社会主义建设探索与曲折",
        keywords=["新中国", "社会主义改造", "大跃进", "文化大革命"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH10-01",
        name="新中国的成立与巩固",
        level=4,
        parent_code="HIST-C1-CH10",
        description="开国大典(1949)、土地改革、抗美援朝、国民经济恢复",
        keywords=["开国大典", "土地改革", "抗美援朝", "国民经济恢复"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH10-02",
        name="社会主义制度的确立",
        level=4,
        parent_code="HIST-C1-CH10",
        description="一五计划(1953-1957/工业化)、三大改造(农业/手工业/资本主义工商业)、1954年宪法",
        keywords=["一五计划", "三大改造", "社会主义制度", "1954年宪法", "工业化"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH10-03",
        name="社会主义建设的探索与曲折",
        level=4,
        parent_code="HIST-C1-CH10",
        description="中共八大(正确分析)、大跃进与人民公社化运动、三年困难时期、文化大革命(1966-1976)",
        keywords=["中共八大", "大跃进", "人民公社", "文化大革命", "四人帮"],
    ),

    # ── 第十一章: 改革开放与社会主义现代化建设 ─────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C1-CH11",
        name="改革开放与社会主义现代化建设",
        level=3,
        parent_code="HIST-C1",
        description="十一届三中全会、改革开放的进程、社会主义市场经济体制建立",
        keywords=["改革开放", "十一届三中全会", "邓小平", "经济特区", "市场经济", "建国"]
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH11-01",
        name="伟大的历史转折",
        level=4,
        parent_code="HIST-C1-CH11",
        description="十一届三中全会(1978/拨乱反正/改革开放)、家庭联产承包责任制、经济特区的设立",
        keywords=["十一届三中全会", "拨乱反正", "家庭联产承包", "经济特区", "深圳"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C1-CH11-02",
        name="改革开放的深入发展",
        level=4,
        parent_code="HIST-C1-CH11",
        description="城市经济体制改革、社会主义市场经济体制目标确立(1992)、加入WTO(2001)、全面建设小康社会",
        keywords=["城市改革", "市场经济", "邓小平南方谈话", "WTO", "小康社会"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  HIST-C2: 中外历史纲要(下)
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 古代文明的产生与发展 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C2-CH1",
        name="古代文明的产生与发展",
        level=3,
        parent_code="HIST-C2",
        description="古代两河流域、古埃及、古印度、古希腊、古罗马文明",
        keywords=["古代文明", "两河流域", "古埃及", "古希腊", "古罗马"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH1-01",
        name="古代亚非文明",
        level=4,
        parent_code="HIST-C2-CH1",
        description="两河流域文明(楔形文字/汉谟拉比法典)、古埃及(金字塔/象形文字)、古印度(种姓制度/佛教)",
        keywords=["两河流域", "汉谟拉比法典", "古埃及", "金字塔", "种姓制度", "佛教"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH1-02",
        name="古代欧洲文明",
        level=4,
        parent_code="HIST-C2-CH1",
        description="古希腊城邦(雅典民主制/斯巴达)、古罗马(共和制→帝制/罗马法)、希腊罗马文化",
        keywords=["古希腊", "雅典民主", "斯巴达", "古罗马", "罗马法", "共和制", "中世纪", "罗马"]
    ),

    # ── 第二章: 中古时期的世界 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C2-CH2",
        name="中古时期的世界",
        level=3,
        parent_code="HIST-C2",
        description="中古欧洲(封建庄园/基督教会)、中古亚洲(阿拉伯帝国/日本幕府)、非洲美洲文明",
        keywords=["中世纪", "封建", "基督教会", "阿拉伯", "日本幕府", "专制", "古代", "小农经济"]
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH2-01",
        name="中古时期的欧洲",
        level=4,
        parent_code="HIST-C2-CH2",
        description="西欧封建制度(封君封臣/庄园经济/农奴制)、基督教会的统治地位、城市复兴与大学兴起",
        keywords=["封建制度", "封君封臣", "庄园", "基督教会", "城市复兴", "大学"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH2-02",
        name="中古时期的亚洲与非洲美洲",
        level=4,
        parent_code="HIST-C2-CH2",
        description="阿拉伯帝国(伊斯兰教/文化交流)、奥斯曼帝国、日本(大化改新/幕府政治)、非洲美洲古文明",
        keywords=["阿拉伯帝国", "伊斯兰教", "奥斯曼帝国", "日本幕府", "大化改新"],
    ),

    # ── 第三章: 走向整体的世界 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C2-CH3",
        name="走向整体的世界",
        level=3,
        parent_code="HIST-C2",
        description="新航路开辟、早期殖民扩张、全球联系的初步建立",
        keywords=["新航路", "地理大发现", "殖民扩张", "哥伦布"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH3-01",
        name="新航路的开辟",
        level=4,
        parent_code="HIST-C2-CH3",
        description="新航路开辟的背景(商品经济发展/奥斯曼阻断商路)、迪亚士/达伽马/哥伦布/麦哲伦、地理大发现的影响",
        keywords=["新航路", "哥伦布", "达伽马", "麦哲伦", "地理大发现", "商业革命"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH3-02",
        name="早期殖民扩张与全球联系",
        level=4,
        parent_code="HIST-C2-CH3",
        description="西班牙葡萄牙的殖民扩张、荷兰英国法国的殖民竞争、三角贸易、全球物种交换(哥伦布大交换)",
        keywords=["殖民扩张", "三角贸易", "奴隶贸易", "哥伦布大交换", "价格革命"],
    ),

    # ── 第四章: 资本主义制度的确立 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C2-CH4",
        name="资本主义制度的确立",
        level=3,
        parent_code="HIST-C2",
        description="文艺复兴与宗教改革、启蒙运动、资产阶级革命(英/美/法)",
        keywords=["文艺复兴", "宗教改革", "启蒙运动", "资产阶级革命"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH4-01",
        name="文艺复兴与宗教改革",
        level=4,
        parent_code="HIST-C2-CH4",
        description="文艺复兴(人文主义/但丁/达芬奇/莎士比亚)、宗教改革(路德/加尔文/英国国教)",
        keywords=["文艺复兴", "人文主义", "但丁", "达芬奇", "宗教改革", "路德"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH4-02",
        name="启蒙运动",
        level=4,
        parent_code="HIST-C2-CH4",
        description="启蒙运动的核心(理性主义)、代表人物(伏尔泰/孟德斯鸠/卢梭/康德)、启蒙思想的影响",
        keywords=["启蒙运动", "理性主义", "伏尔泰", "孟德斯鸠", "卢梭", "社会契约"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH4-03",
        name="资产阶级革命与资本主义制度确立",
        level=4,
        parent_code="HIST-C2-CH4",
        description="英国资产阶级革命(光荣革命/权利法案)、美国独立战争(独立宣言)、法国大革命(人权宣言)",
        keywords=["英国革命", "权利法案", "美国独立", "法国大革命", "人权宣言"],
    ),

    # ── 第五章: 工业革命与马克思主义的诞生 ─────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C2-CH5",
        name="工业革命与马克思主义的诞生",
        level=3,
        parent_code="HIST-C2",
        description="第一次工业革命、第二次工业革命、马克思主义的诞生与传播",
        keywords=["工业革命", "蒸汽机", "电气化", "马克思主义"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH5-01",
        name="两次工业革命",
        level=4,
        parent_code="HIST-C2-CH5",
        description="第一次工业革命(蒸汽机/纺织/铁路)、第二次工业革命(电力/内燃机/化工)、工业化的影响",
        keywords=["蒸汽机", "珍妮纺纱机", "电力", "内燃机", "工业化", "城市化"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH5-02",
        name="马克思主义的诞生与传播",
        level=4,
        parent_code="HIST-C2-CH5",
        description="空想社会主义、马克思与恩格斯、《共产党宣言》(1848)、巴黎公社(1871)",
        keywords=["马克思主义", "共产党宣言", "空想社会主义", "巴黎公社", "恩格斯"],
    ),

    # ── 第六章: 世界殖民体系与民族独立运动 ─────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C2-CH6",
        name="世界殖民体系与民族独立运动",
        level=3,
        parent_code="HIST-C2",
        description="世界殖民体系的形成、亚非拉民族独立运动",
        keywords=["殖民体系", "民族独立", "亚非拉"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH6-01",
        name="世界殖民体系的形成",
        level=4,
        parent_code="HIST-C2-CH6",
        description="工业革命后的殖民扩张、帝国主义瓜分世界(非洲/亚洲)、殖民体系的特点与影响",
        keywords=["殖民体系", "帝国主义", "瓜分非洲", "殖民掠夺"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH6-02",
        name="亚非拉民族独立运动",
        level=4,
        parent_code="HIST-C2-CH6",
        description="拉美独立运动(玻利瓦尔)、亚洲觉醒(印度/中国/土耳其)、非洲独立浪潮",
        keywords=["拉美独立", "玻利瓦尔", "印度民族运动", "非洲独立", "不结盟运动"],
    ),

    # ── 第七章: 两次世界大战与十月革命 ─────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C2-CH7",
        name="两次世界大战与十月革命",
        level=3,
        parent_code="HIST-C2",
        description="第一次世界大战、俄国十月革命、第二次世界大战",
        keywords=["一战", "十月革命", "二战", "法西斯"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH7-01",
        name="第一次世界大战与十月革命",
        level=4,
        parent_code="HIST-C2-CH7",
        description="一战原因(帝国主义矛盾/同盟国vs协约国)、战争过程与结果、俄国十月革命(1917/社会主义国家)",
        keywords=["一战", "萨拉热窝", "同盟国", "协约国", "十月革命", "列宁"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH7-02",
        name="第二次世界大战",
        level=4,
        parent_code="HIST-C2-CH7",
        description="法西斯上台(德日意)、绥靖政策、二战爆发与扩大、反法西斯同盟、二战胜利与影响",
        keywords=["法西斯", "绥靖政策", "珍珠港", "斯大林格勒", "诺曼底", "原子弹"],
    ),

    # ── 第八章: 20世纪下半叶世界的新变化 ───────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C2-CH8",
        name="20世纪下半叶世界的新变化",
        level=3,
        parent_code="HIST-C2",
        description="冷战格局、战后资本主义世界经济体系、社会主义的发展与变化",
        keywords=["冷战", "两极格局", "马歇尔计划", "苏联", "世界大战", "多极化"]
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH8-01",
        name="冷战与两极格局",
        level=4,
        parent_code="HIST-C2-CH8",
        description="冷战的起源(杜鲁门主义/马歇尔计划/北约vs华约)、冷战的演变(柏林危机/古巴导弹危机)、冷战结束(苏联解体)",
        keywords=["冷战", "杜鲁门主义", "马歇尔计划", "北约", "华约", "苏联解体"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH8-02",
        name="战后资本主义世界经济体系",
        level=4,
        parent_code="HIST-C2-CH8",
        description="布雷顿森林体系(美元/IMF/世界银行)、关贸总协定(GATT)、欧洲一体化(欧共体→欧盟)",
        keywords=["布雷顿森林", "IMF", "世界银行", "GATT", "欧盟", "欧洲一体化"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH8-03",
        name="社会主义国家的发展与变化",
        level=4,
        parent_code="HIST-C2-CH8",
        description="苏联模式(斯大林模式)、赫鲁晓夫改革、东欧剧变(1989)、苏联解体(1991)",
        keywords=["斯大林模式", "赫鲁晓夫", "东欧剧变", "苏联解体", "戈尔巴乔夫"],
    ),

    # ── 第九章: 当代世界发展的特点与趋势 ───────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-C2-CH9",
        name="当代世界发展的特点与趋势",
        level=3,
        parent_code="HIST-C2",
        description="世界多极化趋势、经济全球化、信息技术革命、和平与发展",
        keywords=["多极化", "全球化", "信息技术", "和平与发展"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH9-01",
        name="世界多极化与经济全球化",
        level=4,
        parent_code="HIST-C2-CH9",
        description="多极化趋势(美国/欧盟/日本/俄罗斯/中国/发展中国家)、经济全球化(WTO/跨国公司)、区域经济集团化",
        keywords=["多极化", "全球化", "WTO", "跨国公司", "区域集团化"],
    ),
    KnowledgeTreeSeed(
        code="HIST-C2-CH9-02",
        name="和平与发展的时代主题",
        level=4,
        parent_code="HIST-C2-CH9",
        description="和平与发展是当今时代主题、全球性问题(环境/恐怖主义/贫富差距)、构建人类命运共同体",
        keywords=["和平与发展", "恐怖主义", "环境问题", "人类命运共同体", "联合国"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  HIST-S1: 选必一 · 国家制度与社会治理
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 政治制度 ─────────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S1-CH1",
        name="政治制度",
        level=3,
        parent_code="HIST-S1",
        description="中国古代政治制度的演变、西方政治制度的形成与发展、近代以来中国的政治制度",
        keywords=["政治制度", "中央集权", "君主立宪", "共和制"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH1-01",
        name="中国古代政治制度的演变",
        level=4,
        parent_code="HIST-S1-CH1",
        description="从分封制到郡县制、三省六部制、内阁制与军机处、君主专制的强化趋势",
        keywords=["分封制", "郡县制", "三省六部", "内阁", "军机处", "君主专制"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH1-02",
        name="西方政治制度的形成与发展",
        level=4,
        parent_code="HIST-S1-CH1",
        description="雅典民主制、罗马共和制、英国君主立宪制、美国联邦制共和制、法国共和制",
        keywords=["雅典民主", "罗马共和", "君主立宪", "联邦制", "三权分立"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH1-03",
        name="近代以来中国的政治制度",
        level=4,
        parent_code="HIST-S1-CH1",
        description="民国时期的民主共和尝试、新中国的政治制度(人民代表大会/多党合作/民族区域自治)",
        keywords=["民国政治", "人民代表大会", "多党合作", "民族区域自治"],
    ),

    # ── 第二章: 官员的选拔与管理 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S1-CH2",
        name="官员的选拔与管理",
        level=3,
        parent_code="HIST-S1",
        description="中国古代官员选拔(察举/九品中正/科举)、西方文官制度",
        keywords=["科举制", "察举制", "文官制度", "选官"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH2-01",
        name="中国古代官员的选拔与管理",
        level=4,
        parent_code="HIST-S1-CH2",
        description="察举制(汉代)、九品中正制(魏晋)、科举制(隋唐至明清)、官员考核与监察制度",
        keywords=["察举制", "九品中正制", "科举制", "监察", "考核"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH2-02",
        name="西方的文官制度",
        level=4,
        parent_code="HIST-S1-CH2",
        description="英国文官制度的建立(19世纪)、美国公务员制度、西方文官制度的特点与影响",
        keywords=["文官制度", "英国", "美国", "考试录用", "政治中立"],
    ),

    # ── 第三章: 法律与教化 ───────────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S1-CH3",
        name="法律与教化",
        level=3,
        parent_code="HIST-S1",
        description="中国古代的法治与教化、近代西方法律制度、当代中国的法治建设",
        keywords=["法律", "教化", "法治", "礼治"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH3-01",
        name="中国古代的法治与教化",
        level=4,
        parent_code="HIST-S1-CH3",
        description="先秦法家(商鞅/韩非)与儒家(礼治/德治)、秦汉法律(秦律/汉承秦制)、唐律疏议、礼法结合",
        keywords=["法家", "儒家", "秦律", "唐律疏议", "礼法结合", "德主刑辅"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH3-02",
        name="近代西方法律制度与当代中国法治",
        level=4,
        parent_code="HIST-S1-CH3",
        description="英美法系与大陆法系、近代中国法律变革、新中国的法治建设(宪法/依法治国)",
        keywords=["英美法系", "大陆法系", "宪法", "依法治国", "民法典"],
    ),

    # ── 第四章: 民族关系与国家关系 ───────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S1-CH4",
        name="民族关系与国家关系",
        level=3,
        parent_code="HIST-S1",
        description="中国古代的民族关系与对外关系、近代西方民族国家的形成、现代国际关系",
        keywords=["民族关系", "对外关系", "民族国家", "国际关系"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH4-01",
        name="中国古代的民族关系与对外关系",
        level=4,
        parent_code="HIST-S1-CH4",
        description="历代民族政策(和亲/册封/改土归流)、朝贡体系、丝绸之路与海上丝绸之路",
        keywords=["和亲", "册封", "改土归流", "朝贡体系", "丝绸之路"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH4-02",
        name="近代以来的国际关系",
        level=4,
        parent_code="HIST-S1-CH4",
        description="威斯特伐利亚体系、维也纳体系、凡尔赛-华盛顿体系、雅尔塔体系、当代国际关系",
        keywords=["威斯特伐利亚", "维也纳体系", "凡尔赛", "雅尔塔", "联合国"],
    ),

    # ── 第五章: 货币与赋税制度 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S1-CH5",
        name="货币与赋税制度",
        level=3,
        parent_code="HIST-S1",
        description="中国古代货币的演进、中国古代赋税制度、世界货币体系的形成",
        keywords=["货币", "赋税", "白银", "金本位"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH5-01",
        name="中国古代的货币与赋税",
        level=4,
        parent_code="HIST-S1-CH5",
        description="货币演进(贝币/铜钱/纸币/白银)、赋税制度(租庸调/两税法/一条鞭法/摊丁入亩)",
        keywords=["铜钱", "交子", "白银", "租庸调", "两税法", "一条鞭法", "摊丁入亩"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH5-02",
        name="世界货币体系的形成",
        level=4,
        parent_code="HIST-S1-CH5",
        description="金本位制、布雷顿森林体系(美元与黄金挂钩)、牙买加体系、欧元与人民币国际化",
        keywords=["金本位", "布雷顿森林", "美元", "欧元", "人民币国际化"],
    ),

    # ── 第六章: 基层治理与社会保障 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S1-CH6",
        name="基层治理与社会保障",
        level=3,
        parent_code="HIST-S1",
        description="中国古代基层治理、西方基层治理、社会保障制度的发展",
        keywords=["基层治理", "社会保障", "户籍", "里甲"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH6-01",
        name="中国古代的基层治理",
        level=4,
        parent_code="HIST-S1-CH6",
        description="户籍制度(编户齐民)、基层组织(里甲/保甲)、乡绅治理、社会救济(常平仓/义仓)",
        keywords=["户籍", "里甲制", "保甲制", "乡绅", "常平仓", "社会救济"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S1-CH6-02",
        name="西方基层治理与社会保障",
        level=4,
        parent_code="HIST-S1-CH6",
        description="西方社区自治传统、现代社会保障制度(德国俾斯麦/英国福利国家)、新中国社会保障体系",
        keywords=["社区自治", "福利国家", "社会保障", "俾斯麦", "医疗保障"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  HIST-S2: 选必二 · 经济与社会生活
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 食物生产与社会劳作 ───────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S2-CH1",
        name="食物生产与社会劳作",
        level=3,
        parent_code="HIST-S2",
        description="农业的起源与发展、劳作方式的演变(从集体劳作到机器生产)",
        keywords=["农业起源", "劳作方式", "农耕", "畜牧"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH1-01",
        name="农业的起源与发展",
        level=4,
        parent_code="HIST-S2-CH1",
        description="农业的起源(新石器时代/三大农业起源中心)、古代农业的发展(精耕细作/水利工程)",
        keywords=["农业起源", "精耕细作", "水利工程", "都江堰", "铁犁牛耕"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH1-02",
        name="劳作方式的演变",
        level=4,
        parent_code="HIST-S2-CH1",
        description="从集体劳作到个体农耕、手工业的发展、工业革命后的机器生产、现代农业",
        keywords=["集体劳作", "个体农耕", "手工业", "机器生产", "现代农业"],
    ),

    # ── 第二章: 生产工具与劳作方式 ───────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S2-CH2",
        name="生产工具与劳作方式",
        level=3,
        parent_code="HIST-S2",
        description="古代生产工具的改进、手工业的进步、近代工业生产方式的确立",
        keywords=["生产工具", "手工业", "工业革命", "工厂制"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH2-01",
        name="古代生产工具与手工业",
        level=4,
        parent_code="HIST-S2-CH2",
        description="石器/青铜器/铁器的演进、中国古代手工业(纺织/陶瓷/冶金)、官营与民营手工业",
        keywords=["青铜器", "铁器", "纺织", "陶瓷", "官营手工业"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH2-02",
        name="近代工业生产方式的确立",
        level=4,
        parent_code="HIST-S2-CH2",
        description="工厂制取代手工工场、机器大生产、流水线生产、信息技术与智能制造",
        keywords=["工厂制", "机器大生产", "流水线", "智能制造"],
    ),

    # ── 第三章: 商业贸易与日常生活 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S2-CH3",
        name="商业贸易与日常生活",
        level=3,
        parent_code="HIST-S2",
        description="古代商业贸易的发展、近代世界市场的形成、现代商业与消费",
        keywords=["商业", "贸易", "市场", "货币"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH3-01",
        name="古代商业贸易的发展",
        level=4,
        parent_code="HIST-S2-CH3",
        description="中国古代商业(市坊制度/交子/商帮)、丝绸之路与海上丝绸之路、古代商业政策(重农抑商)",
        keywords=["市坊", "交子", "商帮", "丝绸之路", "重农抑商"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH3-02",
        name="世界市场的形成与现代商业",
        level=4,
        parent_code="HIST-S2-CH3",
        description="新航路与世界市场雏形、工业革命与世界市场扩展、20世纪世界贸易体系、电子商务",
        keywords=["世界市场", "WTO", "自由贸易", "电子商务", "全球化"],
    ),

    # ── 第四章: 村落城镇与居住环境 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S2-CH4",
        name="村落城镇与居住环境",
        level=3,
        parent_code="HIST-S2",
        description="古代村落与城镇的形成、城市化进程、居住条件的变迁",
        keywords=["村落", "城镇", "城市化", "居住环境"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH4-01",
        name="古代村落与城镇",
        level=4,
        parent_code="HIST-S2-CH4",
        description="古代村落的形成(农业定居)、古代城市的兴起(政治/军事/经济功能)、中国古代城市特征",
        keywords=["村落", "城市起源", "坊市制", "政治中心"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH4-02",
        name="城市化进程与居住环境",
        level=4,
        parent_code="HIST-S2-CH4",
        description="近代城市化(工业革命推动)、现代城市化(发展中国家加速)、城市问题与宜居城市",
        keywords=["城市化", "工业化", "城市问题", "宜居城市", "棚户区"],
    ),

    # ── 第五章: 交通与社会变迁 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S2-CH5",
        name="交通与社会变迁",
        level=3,
        parent_code="HIST-S2",
        description="古代交通(驿站/丝绸之路)、近代交通变革(铁路/轮船/汽车/飞机)、现代交通",
        keywords=["交通", "铁路", "轮船", "汽车", "航空"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH5-01",
        name="古代交通",
        level=4,
        parent_code="HIST-S2-CH5",
        description="古代陆路交通(驰道/驿站)、古代水路交通(运河/航海)、交通对经济文化交流的促进",
        keywords=["驰道", "驿站", "大运河", "郑和下西洋", "丝绸之路"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH5-02",
        name="近代以来的交通变革",
        level=4,
        parent_code="HIST-S2-CH5",
        description="蒸汽机车与铁路、轮船与海运、汽车与公路、飞机与航空、交通变革对社会的影响",
        keywords=["铁路", "蒸汽机车", "轮船", "汽车", "飞机", "高铁"],
    ),

    # ── 第六章: 医疗与公共卫生 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S2-CH6",
        name="医疗与公共卫生",
        level=3,
        parent_code="HIST-S2",
        description="古代医疗成就、近代医学的发展、现代公共卫生体系",
        keywords=["医疗", "公共卫生", "中医药", "疫苗"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH6-01",
        name="古代医疗与公共卫生",
        level=4,
        parent_code="HIST-S2-CH6",
        description="中医药成就(伤寒杂病论/本草纲目)、古代防疫措施、西方古代医学(希波克拉底)",
        keywords=["中医药", "伤寒杂病论", "本草纲目", "希波克拉底", "防疫"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S2-CH6-02",
        name="近代以来医学与公共卫生的发展",
        level=4,
        parent_code="HIST-S2-CH6",
        description="近代医学(细菌学/疫苗/抗生素)、公共卫生体系的建立(检疫/清洁/免疫)、现代医学与健康中国",
        keywords=["细菌学", "疫苗", "抗生素", "公共卫生", "免疫接种", "健康中国"],
    ),

    # ═══════════════════════════════════════════════════════════════════════════════
    #  HIST-S3: 选必三 · 文化交流与传播
    # ═══════════════════════════════════════════════════════════════════════════════

    # ── 第一章: 中华优秀传统文化的内涵与特点 ───────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S3-CH1",
        name="中华优秀传统文化的内涵与特点",
        level=3,
        parent_code="HIST-S3",
        description="中华优秀传统文化的内涵(儒道法思想)、特点(连续性/包容性)、价值",
        keywords=["传统文化", "儒家", "道家", "文化内涵"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH1-01",
        name="中华优秀传统文化的内涵",
        level=4,
        parent_code="HIST-S3-CH1",
        description="儒家思想(仁/礼/中庸)、道家思想(道法自然/无为)、法家思想(法治/集权)、中华文化的核心理念",
        keywords=["儒家", "道家", "法家", "仁", "礼", "中庸", "天人合一"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH1-02",
        name="中华优秀传统文化的特点与价值",
        level=4,
        parent_code="HIST-S3-CH1",
        description="连续性/包容性/多样性、传统文化的当代价值、创造性转化与创新性发展",
        keywords=["连续性", "包容性", "创造性转化", "创新性发展", "文化自信"],
    ),

    # ── 第二章: 世界文化的多样性 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S3-CH2",
        name="世界文化的多样性",
        level=3,
        parent_code="HIST-S3",
        description="古代世界文化(两河/埃及/印度/希腊)、中古文化(伊斯兰/基督教)、近现代文化",
        keywords=["文化多样性", "古希腊文化", "伊斯兰文化", "基督教文化"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH2-01",
        name="古代世界文化",
        level=4,
        parent_code="HIST-S3-CH2",
        description="两河流域文化(楔形文字/法律)、古埃及文化(宗教/建筑)、古印度文化(宗教/哲学)、古希腊文化(民主/哲学/艺术)",
        keywords=["楔形文字", "金字塔", "佛教", "希腊哲学", "民主"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH2-02",
        name="中古至近现代世界文化",
        level=4,
        parent_code="HIST-S3-CH2",
        description="伊斯兰文化(科学/艺术)、基督教文化(经院哲学/哥特建筑)、文艺复兴与启蒙运动的文化遗产",
        keywords=["伊斯兰文化", "基督教文化", "文艺复兴", "启蒙运动", "启蒙", "工业革命"]
    ),

    # ── 第三章: 人口迁徙与文化交融 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S3-CH3",
        name="人口迁徙与文化交融",
        level=3,
        parent_code="HIST-S3",
        description="古代人口迁徙(游牧民族/民族大迁徙)、近代移民与文化交融、现代人口流动",
        keywords=["人口迁徙", "民族融合", "移民", "文化交融"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH3-01",
        name="古代人口迁徙与文化交融",
        level=4,
        parent_code="HIST-S3-CH3",
        description="游牧民族的迁徙(匈奴/鲜卑/蒙古)、欧洲民族大迁徙(日耳曼人)、文化交融的结果",
        keywords=["匈奴", "鲜卑", "蒙古", "日耳曼人", "民族大迁徙", "文化融合"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH3-02",
        name="近现代人口迁徙与文化交融",
        level=4,
        parent_code="HIST-S3-CH3",
        description="近代殖民移民(欧洲→美洲/大洋洲)、劳工移民(华工/印度劳工)、现代国际移民与多元文化",
        keywords=["殖民移民", "华工", "多元文化", "国际移民", "文化认同"],
    ),

    # ── 第四章: 商路贸易与文化交流 ─────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S3-CH4",
        name="商路贸易与文化交流",
        level=3,
        parent_code="HIST-S3",
        description="丝绸之路与文化交流、新航路与文化交融、近现代贸易与文化输出",
        keywords=["丝绸之路", "新航路", "贸易", "文化交流"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH4-01",
        name="古代商路与文化交流",
        level=4,
        parent_code="HIST-S3-CH4",
        description="陆上丝绸之路(张骞通西域/佛教东传)、海上丝绸之路(瓷器/茶叶/香料传播)、阿拉伯商人的中介作用",
        keywords=["丝绸之路", "张骞", "佛教东传", "海上丝绸之路", "瓷器"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH4-02",
        name="近现代贸易与文化输出",
        level=4,
        parent_code="HIST-S3-CH4",
        description="新航路后的全球贸易与文化传播、工业革命后的商品与文化输出、当代文化贸易与软实力",
        keywords=["全球贸易", "文化输出", "软实力", "文化产业", "文化贸易"],
    ),

    # ── 第五章: 战争与文化交锋 ───────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S3-CH5",
        name="战争与文化交锋",
        level=3,
        parent_code="HIST-S3",
        description="古代战争与文化交融(亚历山大/蒙古)、近代殖民战争与文化冲突、两次世界大战与文化",
        keywords=["战争", "文化交锋", "殖民", "文化冲突"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH5-01",
        name="古代战争与文化交融",
        level=4,
        parent_code="HIST-S3-CH5",
        description="亚历山大东征(希腊化)、蒙古西征(东西方交流)、十字军东征(东西方碰撞)",
        keywords=["亚历山大东征", "希腊化", "蒙古西征", "十字军东征"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH5-02",
        name="近现代战争与文化",
        level=4,
        parent_code="HIST-S3-CH5",
        description="殖民战争与文化侵略、两次世界大战对文化的冲击、战后文化反思与和平文化",
        keywords=["殖民战争", "文化侵略", "战争反思", "和平文化"],
    ),

    # ── 第六章: 文化的传承与保护 ─────────────────────────────────────────────────
    KnowledgeTreeSeed(
        code="HIST-S3-CH6",
        name="文化的传承与保护",
        level=3,
        parent_code="HIST-S3",
        description="文化遗产的保护、非物质文化遗产、博物馆与文化传承",
        keywords=["文化遗产", "非物质文化遗产", "博物馆", "传承保护"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH6-01",
        name="世界文化遗产的保护",
        level=4,
        parent_code="HIST-S3-CH6",
        description="世界文化遗产的认定(UNESCO)、代表性文化遗产(长城/故宫/金字塔)、保护的意义与措施",
        keywords=["UNESCO", "世界文化遗产", "长城", "故宫", "保护"],
    ),
    KnowledgeTreeSeed(
        code="HIST-S3-CH6-02",
        name="非物质文化遗产与文化传承",
        level=4,
        parent_code="HIST-S3-CH6",
        description="非物质文化遗产(传统技艺/民俗/表演艺术)、博物馆与档案馆、数字化保护、活态传承",
        keywords=["非物质文化遗产", "传统技艺", "博物馆", "数字化保护", "活态传承"],
    ),
]
