"""
语文知识树 V2 (新课标教材单元对齐) — 4 级深度

模块结构 (6 大模块):
  CHN-BXS   必修上册 (7 单元: 青春/劳动/诗意/家园/乡土/学习/自然)
  CHN-BXX   必修下册 (5 单元: 文明/戏剧/科学/信息/使命)
  CHN-XBS   选择性必修上册 (3 单元: 革命/诸子/外国小说)
  CHN-XBZ   选择性必修中册 (2 单元: 科学论著/现当代作品)
  CHN-XBX   选择性必修下册 (2 单元: 古典诗词/传统文化)
  CHN-YUZI  语言知识与表达 (5 章: 字音/字形/词语/病句/修辞)

编码体系:
  L2 = CHN-{MODULE}             e.g. CHN-BXS
  L3 = CHN-{MODULE}-{UNIT}      e.g. CHN-BXS-01
  L4 = CHN-{MODULE}-{UNIT}-{PT} e.g. CHN-BXS-01-01

不与 chinese.py (CHN-READ/CHN-ANCI/CHN-LANG/CHN-WRITE) 重复。
"""

from __future__ import annotations

from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed

CHINESE_KNOWLEDGE_TREE_V2: list[KnowledgeTreeSeed] = [

    # ═══ Level 2: 课程模块 (6) ═══════════════════════════════════════════════════

    KnowledgeTreeSeed(
        code="CHN-BXS", name="必修上册", level=2, parent_code="CHN",
        description="高中语文必修上册，涵盖现代诗歌、新闻通讯、古诗词、散文、学术著作、文言文等",
        keywords=[
            "必修上册",
            "必修上",
            "现代诗歌",
            "古诗词",
            "散文",
            "文言文",
            "乡土中国",
            "新闻通讯",
            "任务驱动",
            "偏题",
            "准确立意",
            "切题",
            "命题作文",
            "审题",
            "新材料作文",
            "新颖立意",
            "材料作文",
            "深刻立意",
            "漫画作文",
            "立意",
            "话题作文",
            "题意",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX", name="必修下册", level=2, parent_code="CHN",
        description="高中语文必修下册，涵盖先秦诸子、戏剧、科普文章、跨媒介阅读、演讲等",
        keywords=["必修下册", "必修下", "诸子散文", "戏剧", "科普", "演讲",
                  "跨媒介"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBS", name="选择性必修上册", level=2, parent_code="CHN",
        description="选择性必修上册，涵盖革命传统作品、先秦诸子散文、外国小说研习",
        keywords=["选必上册", "选必上", "革命传统", "诸子散文", "外国小说",
                  "论语", "孟子"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBZ", name="选择性必修中册", level=2, parent_code="CHN",
        description="选择性必修中册，涵盖科学与文化论著研习、中国现当代作家作品研习",
        keywords=["选必中册", "选必中", "学术论文", "现当代文学", "逻辑论证",
                  "文学流派"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBX", name="选择性必修下册", level=2, parent_code="CHN",
        description="选择性必修下册，涵盖古典诗词研习、中国传统文化经典研习",
        keywords=["选必下册", "选必下", "诗词格律", "诗词流派", "古代文论",
                  "文化经典"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI", name="语言知识与表达", level=2, parent_code="CHN",
        description="语言基础知识，涵盖字音、字形、词语辨析、病句修改、修辞手法",
        keywords=[
            "语言知识",
            "字音",
            "字形",
            "词语",
            "病句",
            "修辞",
            "成语",
            "近义词",
            "多音字",
            "书写规范",
            "借古讽今",
            "借景抒情",
            "准确",
            "卷面",
            "卷面整洁",
            "句式",
            "句式灵活",
            "善用修辞",
            "山水田园",
            "得体",
            "怀古伤今",
            "思想感情",
            "托物言志",
            "抒情方式",
            "文采",
            "有文采",
            "标点",
            "标点正确",
            "生动",
            "用典",
            "直接抒情",
            "简明",
            "羁旅思乡",
            "虚实结合",
            "表现手法",
            "表达",
            "表达技巧",
            "衬托",
            "语言",
            "语言流畅",
            "语言生动",
            "边塞征战",
            "连贯",
            "送别怀人",
            "间接抒情",
        ]
    ),

    # ═══ CHN-BXS: 必修上册 (L3: 7 单元) ══════════════════════════════════════════

    KnowledgeTreeSeed(
        code="CHN-BXS-01", name="第一单元 青春与理想", level=3, parent_code="CHN-BXS",
        description="现代诗歌阅读与鉴赏，体会青春主题的诗意表达",
        keywords=["青春", "理想", "现代诗歌", "诗歌鉴赏", "意象"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-02", name="第二单元 劳动最美丽", level=3, parent_code="CHN-BXS",
        description="新闻通讯阅读与人物通讯写作，理解劳动价值",
        keywords=["劳动", "新闻通讯", "人物通讯", "劳动价值", "通讯写作"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-03", name="第三单元 生命的诗意", level=3, parent_code="CHN-BXS",
        description="古诗词诵读与鉴赏，涵盖魏晋诗歌、唐诗宋词",
        keywords=["生命", "诗意", "古诗词", "魏晋诗歌", "唐诗宋词", "意境"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-04", name="第四单元 我们的家园", level=3, parent_code="CHN-BXS",
        description="散文阅读，写景抒情散文与乡土文化主题",
        keywords=["家园", "散文", "写景抒情", "乡土文化", "散文阅读"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-05", name="第五单元 乡土的中国", level=3, parent_code="CHN-BXS",
        description="学术著作《乡土中国》阅读，学习概念梳理与学术文本分析",
        keywords=["乡土中国", "费孝通", "学术著作", "概念梳理", "学术文本"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-06", name="第六单元 学习之道", level=3, parent_code="CHN-BXS",
        description="文言文阅读，议论说理类文言文与古今学习观比较",
        keywords=["学习之道", "文言文", "议论说理", "学习观", "古今比较"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-07", name="第七单元 自然情怀", level=3, parent_code="CHN-BXS",
        description="散文阅读与鉴赏，写景抒情手法与人与自然主题",
        keywords=["自然", "情怀", "散文鉴赏", "写景抒情", "人与自然"],
    ),

    # ─── CHN-BXS-01: 青春与理想 (L4: 3) ─────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXS-01-01", name="现代诗歌阅读与鉴赏", level=4, parent_code="CHN-BXS-01",
        description="现代诗歌的节奏韵律、意象运用、情感表达的阅读与鉴赏方法",
        keywords=[
            "现代诗歌",
            "诗歌鉴赏",
            "节奏",
            "韵律",
            "情感表达",
            "不正确",
            "不正确的一项是",
            "元曲",
            "古代诗歌",
            "古诗",
            "唐诗",
            "宋词",
            "对这首词",
            "对这首诗",
            "思想感情",
            "意境",
            "意象",
            "炼字",
            "理解和赏析",
            "表达技巧",
            "诗歌",
            "诗词",
            "赏析",
            "鉴赏",
            "阅读下面这首",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-01-02", name="诗歌意象分析", level=4, parent_code="CHN-BXS-01",
        description="分析诗歌中意象的选择、组合与象征意义",
        keywords=["意象", "象征", "意象分析", "诗歌意象", "意象组合"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-01-03", name="青春主题表达", level=4, parent_code="CHN-BXS-01",
        description="诗歌中青春、理想、奋斗等主题的表达方式与情感基调",
        keywords=["青春主题", "理想", "奋斗", "情感基调", "主题表达"],
    ),

    # ─── CHN-BXS-02: 劳动最美丽 (L4: 3) ─────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXS-02-01", name="新闻通讯阅读", level=4, parent_code="CHN-BXS-02",
        description="新闻通讯的文体特征、结构方式与阅读方法",
        keywords=[
            "新闻通讯",
            "通讯",
            "新闻阅读",
            "文体特征",
            "新闻结构",
            "传记",
            "图表",
            "多则材料",
            "实用类",
            "新闻",
            "新闻报告",
            "材料",
            "科普",
            "访谈",
            "调查报告",
            "非连续",
            "非连续性文本",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-02-02", name="人物通讯写作", level=4, parent_code="CHN-BXS-02",
        description="人物通讯的选材、叙事角度、细节描写与写作技巧",
        keywords=["人物通讯", "通讯写作", "细节描写", "叙事角度", "选材"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-02-03", name="劳动价值主题", level=4, parent_code="CHN-BXS-02",
        description="理解劳动的意义与价值，体会劳动者的奉献精神",
        keywords=["劳动价值", "劳动者", "奉献精神", "劳动光荣", "敬业"],
    ),

    # ─── CHN-BXS-03: 生命的诗意 (L4: 4) ─────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXS-03-01", name="古诗词诵读", level=4, parent_code="CHN-BXS-03",
        description="古诗词的朗读节奏、韵律美感与背诵积累方法",
        keywords=["古诗词", "诵读", "朗读", "背诵", "韵律", "名句", "名篇名句", "填空默写", "理解性默写", "补写", "补写出下列句子", "默写"]
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-03-02", name="魏晋诗歌", level=4, parent_code="CHN-BXS-03",
        description="曹操、陶渊明等魏晋诗人的代表作品与诗歌风格",
        keywords=["魏晋诗歌", "曹操", "陶渊明", "建安风骨", "田园诗"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-03-03", name="唐诗宋词", level=4, parent_code="CHN-BXS-03",
        description="唐诗宋词的经典作品、流派特征与艺术成就",
        keywords=["唐诗", "宋词", "李白", "杜甫", "苏轼", "辛弃疾"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-03-04", name="诗词意境鉴赏", level=4, parent_code="CHN-BXS-03",
        description="意境的营造手法、意境类型(雄浑/婉约/清新/萧瑟)与鉴赏方法",
        keywords=[
            "意境",
            "意境鉴赏",
            "情景交融",
            "雄浑",
            "婉约",
            "一字统摄",
            "事物形象",
            "人物形象",
            "含蓄",
            "形象",
            "意象",
            "景物形象",
            "最生动传神",
            "沉郁",
            "清新",
            "炼字",
            "词眼",
            "诗眼",
            "语言风格",
            "豪放",
            "质朴",
        ]
    ),

    # ─── CHN-BXS-04: 我们的家园 (L4: 3) ─────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXS-04-01", name="散文阅读", level=4, parent_code="CHN-BXS-04",
        description="散文的文体特征、阅读方法与鉴赏角度",
        keywords=[
            "散文",
            "散文阅读",
            "文体特征",
            "鉴赏",
            "阅读方法",
            "下列对",
            "下列有关",
            "主题",
            "人物",
            "人物形象",
            "人物描写",
            "以小见大",
            "伏笔",
            "修辞手法",
            "借景抒情",
            "关于",
            "内容和艺术特色",
            "写作手法",
            "分析",
            "加点的词",
            "加点词",
            "动作描写",
            "发展",
            "叙述视角",
            "古代诗歌",
            "古诗文",
            "寓情于景",
            "小说",
            "开端",
            "形散神聚",
            "心理描写",
            "悬念",
            "情景交融",
            "情节",
            "意境",
            "感情线索",
            "托物言志",
            "文学作品",
            "文学文本",
            "文学类",
            "文言",
            "文言文",
            "断句",
            "景物描写",
            "概括",
            "欲扬先抑",
            "照应",
            "环境",
            "环境描写",
            "现代文",
            "理解不正确",
            "理解与分析",
            "理解正确",
            "线索",
            "结局",
            "翻译",
            "肖像描写",
            "艺术特色",
            "表现手法",
            "表达技巧",
            "表达效果",
            "解释不正确",
            "解释正确",
            "论述",
            "词",
            "诗歌",
            "语言描写",
            "象征",
            "赏析",
            "铺垫",
            "阅读",
            "阅读下面",
            "阅读理解",
            "高潮",
            "默写",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-04-02", name="写景抒情散文", level=4, parent_code="CHN-BXS-04",
        description="写景抒情散文的景物描写手法、情景关系与抒情方式",
        keywords=["写景抒情", "景物描写", "情景关系", "借景抒情", "寓情于景"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-04-03", name="乡土文化主题", level=4, parent_code="CHN-BXS-04",
        description="散文中乡土文化的表现、乡愁情感与文化认同",
        keywords=["乡土文化", "乡愁", "文化认同", "故土", "家园意识"],
    ),

    # ─── CHN-BXS-05: 乡土的中国 (L4: 3) ─────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXS-05-01", name="学术著作阅读", level=4, parent_code="CHN-BXS-05",
        description="《乡土中国》等学术著作的整体把握与阅读策略",
        keywords=["学术著作", "乡土中国", "费孝通", "阅读策略", "整体把握"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-05-02", name="概念理解与梳理", level=4, parent_code="CHN-BXS-05",
        description="学术文本中核心概念的提取、定义理解与逻辑梳理",
        keywords=["概念", "概念梳理", "核心概念", "定义", "逻辑梳理"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-05-03", name="学术文本分析方法", level=4, parent_code="CHN-BXS-05",
        description="学术论文的论证结构、论据类型与分析方法",
        keywords=[
            "学术文本",
            "论证结构",
            "论据",
            "分析方法",
            "学术写作",
            "一材多用",
            "举例",
            "事例",
            "事实论据",
            "人物素材",
            "典型事例",
            "古今中外",
            "名言",
            "引用",
            "积累",
            "素材",
            "联系实际",
            "道理论据",
        ]
    ),

    # ─── CHN-BXS-06: 学习之道 (L4: 3) ──────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXS-06-01", name="文言文阅读", level=4, parent_code="CHN-BXS-06",
        description="文言文的字词理解、句式分析与整体阅读能力",
        keywords=[
            "文言文",
            "文言阅读",
            "字词理解",
            "句式",
            "阅读能力",
            "一词多义",
            "下列对文中",
            "下定义",
            "与",
            "且",
            "为",
            "为……所",
            "主动句",
            "主谓倒装",
            "乃",
            "之",
            "乎",
            "也",
            "于",
            "以",
            "仿写",
            "何",
            "倒装句",
            "其",
            "则",
            "判断句",
            "加点的字",
            "加点的词",
            "加点词解释",
            "加点词语",
            "压缩",
            "变换",
            "古今异义",
            "句子翻译",
            "因",
            "定语后置",
            "实词",
            "宾语前置",
            "对文中",
            "意义和用法不同",
            "意义和用法相同",
            "意译",
            "所",
            "扩写",
            "把文中画横线",
            "提取关键词",
            "散句",
            "整句",
            "文中加点词",
            "文中画波浪线",
            "文中画线",
            "文言文阅读",
            "断句",
            "概括内容",
            "焉",
            "状语后置",
            "直译",
            "省略句",
            "短句",
            "翻译",
            "翻译成现代汉语",
            "者",
            "者……也",
            "而",
            "若",
            "虚词",
            "被动句",
            "解释不正确",
            "解释正确",
            "词义",
            "词的意义和用法",
            "词类活用",
            "译为",
            "通假字",
            "重组句子",
            "长句",
            "阅读下面的文言文",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-06-02", name="议论说理文言文", level=4, parent_code="CHN-BXS-06",
        description="文言文中议论说理类文章的论证方法与逻辑分析",
        keywords=[
            "议论说理",
            "文言议论",
            "论证方法",
            "说理文",
            "荀子",
            "韩愈",
            "不符合原文意思",
            "信息筛选",
            "关于原文",
            "原文内容",
            "根据原文",
            "理解和分析",
            "理解和分析不正确",
            "理解和推断",
            "社科文",
            "科技文",
            "符合原文意思",
            "论据",
            "论点",
            "论述文",
            "论述类",
            "说法不正确",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-06-03", name="古今学习观比较", level=4, parent_code="CHN-BXS-06",
        description="古代学习观与现代学习理念的异同分析与思考",
        keywords=["学习观", "古今比较", "学习方法", "劝学", "师说"],
    ),

    # ─── CHN-BXS-07: 自然情怀 (L4: 3) ──────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXS-07-01", name="散文阅读与鉴赏", level=4, parent_code="CHN-BXS-07",
        description="自然主题散文的阅读方法与艺术鉴赏",
        keywords=["散文鉴赏", "自然散文", "阅读方法", "艺术特色", "散文阅读"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-07-02", name="写景抒情手法", level=4, parent_code="CHN-BXS-07",
        description="散文中写景抒情的常见手法：白描、工笔、动静结合、虚实相生",
        keywords=["写景抒情", "白描", "工笔", "动静结合", "虚实相生"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXS-07-03", name="人与自然主题", level=4, parent_code="CHN-BXS-07",
        description="散文中人与自然和谐共处的主题表达与哲理思考",
        keywords=["人与自然", "和谐共处", "自然哲理", "生态意识", "敬畏自然"],
    ),

    # ═══ CHN-BXX: 必修下册 (L3: 5 单元) ══════════════════════════════════════════

    KnowledgeTreeSeed(
        code="CHN-BXX-01", name="第一单元 中华文明之光", level=3, parent_code="CHN-BXX",
        description="先秦诸子散文与儒家经典选读，感受中华文明的思想光辉",
        keywords=["中华文明", "先秦诸子", "儒家经典", "历史散文", "诸子百家"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-02", name="第二单元 良知与悲悯", level=3, parent_code="CHN-BXX",
        description="中外戏剧阅读，分析戏剧冲突与人物台词",
        keywords=["戏剧", "良知", "悲悯", "戏剧冲突", "台词赏析"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-03", name="第三单元 探索与发现", level=3, parent_code="CHN-BXX",
        description="科普文章阅读与说明文写作，培养科学精神",
        keywords=["科普", "探索", "发现", "说明文", "科学精神"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-04", name="第四单元 信息时代的语文生活", level=3, parent_code="CHN-BXX",
        description="跨媒介阅读与交流，信息筛选整合与媒介素养",
        keywords=["信息时代", "跨媒介", "媒介素养", "信息筛选", "语文生活"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-05", name="第五单元 使命与抱负", level=3, parent_code="CHN-BXX",
        description="演讲词阅读与演讲稿写作，培养社会责任感",
        keywords=["使命", "抱负", "演讲", "演讲稿", "社会责任"],
    ),

    # ─── CHN-BXX-01: 中华文明之光 (L4: 3) ────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXX-01-01", name="先秦诸子散文", level=4, parent_code="CHN-BXX-01",
        description="先秦诸子散文的代表作品、思想内涵与文学特色",
        keywords=["先秦诸子", "诸子散文", "百家争鸣", "思想内涵", "文学特色"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-01-02", name="儒家经典选读", level=4, parent_code="CHN-BXX-01",
        description="《论语》《孟子》《荀子》等儒家经典篇章的阅读与理解",
        keywords=["儒家", "论语", "孟子", "荀子", "仁义礼智"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-01-03", name="历史散文", level=4, parent_code="CHN-BXX-01",
        description="《左传》《史记》等历史散文的叙事艺术与人物刻画",
        keywords=["历史散文", "左传", "史记", "叙事艺术", "人物刻画"],
    ),

    # ─── CHN-BXX-02: 良知与悲悯 (L4: 3) ─────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXX-02-01", name="中外戏剧阅读", level=4, parent_code="CHN-BXX-02",
        description="中外经典戏剧作品的阅读方法与戏剧文体特征",
        keywords=["戏剧阅读", "戏剧", "话剧", "悲剧", "喜剧", "窦娥冤"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-02-02", name="戏剧冲突分析", level=4, parent_code="CHN-BXX-02",
        description="戏剧冲突的类型、设置方式与推动情节发展的作用",
        keywords=["戏剧冲突", "矛盾冲突", "情节发展", "人物冲突", "戏剧结构"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-02-03", name="人物台词赏析", level=4, parent_code="CHN-BXX-02",
        description="戏剧台词的语言特色、潜台词分析与人物性格塑造",
        keywords=["台词", "潜台词", "人物性格", "语言特色", "台词赏析"],
    ),

    # ─── CHN-BXX-03: 探索与发现 (L4: 3) ─────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXX-03-01", name="科普文章阅读", level=4, parent_code="CHN-BXX-03",
        description="科普文章的文体特征、说明方法与信息提取能力",
        keywords=["科普文章", "科普阅读", "说明方法", "信息提取", "科学知识"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-03-02", name="说明文写作", level=4, parent_code="CHN-BXX-03",
        description="说明文的写作方法：说明顺序、说明方法、语言准确性",
        keywords=[
            "说明文",
            "说明文写作",
            "说明顺序",
            "说明方法",
            "准确性",
            "作文",
            "写作",
            "大作文",
            "审题",
            "微写作",
            "立意",
            "素材",
            "议论文",
            "记叙文",
            "论证",
            "话题作文",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-03-03", name="科学精神主题", level=4, parent_code="CHN-BXX-03",
        description="科学精神的内涵：求真、质疑、实证、创新",
        keywords=["科学精神", "求真", "质疑", "实证", "创新"],
    ),

    # ─── CHN-BXX-04: 信息时代的语文生活 (L4: 3) ─────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXX-04-01", name="跨媒介阅读与交流", level=4, parent_code="CHN-BXX-04",
        description="不同媒介(文字/图像/视频/音频)的阅读理解与信息转换",
        keywords=["跨媒介", "媒介阅读", "多媒体", "信息转换", "读图时代"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-04-02", name="信息筛选与整合", level=4, parent_code="CHN-BXX-04",
        description="从多种信息来源中筛选关键信息并进行有效整合",
        keywords=["信息筛选", "信息整合", "信息来源", "关键信息", "信息处理"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-04-03", name="媒介素养", level=4, parent_code="CHN-BXX-04",
        description="媒介信息的辨识、批判性思考与负责任的信息传播",
        keywords=["媒介素养", "信息辨识", "批判性思考", "虚假信息", "网络传播"],
    ),

    # ─── CHN-BXX-05: 使命与抱负 (L4: 3) ─────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-BXX-05-01", name="演讲词阅读", level=4, parent_code="CHN-BXX-05",
        description="经典演讲词的阅读分析：结构、修辞、说服力",
        keywords=["演讲词", "演讲阅读", "说服力", "演讲结构", "经典演讲"],
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-05-02", name="演讲稿写作", level=4, parent_code="CHN-BXX-05",
        description="演讲稿的写作技巧：开头吸引、逻辑清晰、结尾有力",
        keywords=[
            "演讲稿",
            "演讲写作",
            "开头",
            "结尾",
            "逻辑清晰",
            "举例论证",
            "凤头",
            "因果论证",
            "对比论证",
            "对照式",
            "并列式",
            "引用论证",
            "引论",
            "总分式",
            "本论",
            "比喻论证",
            "猪肚",
            "结构",
            "结论",
            "论证",
            "豹尾",
            "递进式",
            "道理论证",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHN-BXX-05-03", name="社会责任感", level=4, parent_code="CHN-BXX-05",
        description="青年的社会责任与使命担当，家国情怀的表达",
        keywords=["社会责任", "使命担当", "家国情怀", "青年责任", "报国"],
    ),

    # ═══ CHN-XBS: 选择性必修上册 (L3: 3 单元) ════════════════════════════════════

    KnowledgeTreeSeed(
        code="CHN-XBS-01", name="第一单元 中国革命传统作品研习", level=3, parent_code="CHN-XBS",
        description="革命回忆录与红色经典阅读，传承革命精神",
        keywords=["革命传统", "红色经典", "革命回忆录", "革命精神", "革命文学"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBS-02", name="第二单元 先秦诸子散文研习", level=3, parent_code="CHN-XBS",
        description="《论语》《孟子》《老子》《庄子》等诸子经典的深入研习",
        keywords=["先秦诸子", "论语", "孟子", "老子", "庄子", "诸子散文"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBS-03", name="第三单元 外国小说研习", level=3, parent_code="CHN-XBS",
        description="外国短篇小说的叙事技巧分析与跨文化理解",
        keywords=["外国小说", "短篇小说", "叙事技巧", "跨文化", "外国文学"],
    ),

    # ─── CHN-XBS-01: 中国革命传统作品研习 (L4: 3) ───────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-XBS-01-01", name="革命回忆录", level=4, parent_code="CHN-XBS-01",
        description="革命回忆录的文体特征、叙事视角与历史价值",
        keywords=["革命回忆录", "回忆录", "叙事视角", "历史价值", "纪实"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBS-01-02", name="红色经典阅读", level=4, parent_code="CHN-XBS-01",
        description="红色经典文学作品的阅读方法与思想内涵",
        keywords=["红色经典", "革命文学", "思想内涵", "阅读方法", "经典作品"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBS-01-03", name="革命精神主题", level=4, parent_code="CHN-XBS-01",
        description="革命精神的内涵：坚定信念、艰苦奋斗、无私奉献",
        keywords=["革命精神", "坚定信念", "艰苦奋斗", "无私奉献", "革命传统"],
    ),

    # ─── CHN-XBS-02: 先秦诸子散文研习 (L4: 3) ──────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-XBS-02-01", name="《论语》选读", level=4, parent_code="CHN-XBS-02",
        description="《论语》核心篇章的精读，理解孔子的仁学思想与教育理念",
        keywords=["论语", "孔子", "仁", "教育思想", "论语选读"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBS-02-02", name="《孟子》选读", level=4, parent_code="CHN-XBS-02",
        description="《孟子》核心篇章的精读，理解性善论与仁政思想",
        keywords=["孟子", "性善论", "仁政", "民本思想", "孟子选读"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBS-02-03", name="《老子》《庄子》选读", level=4, parent_code="CHN-XBS-02",
        description="道家经典选读，理解道法自然、无为而治的哲学思想",
        keywords=["老子", "庄子", "道家", "道法自然", "无为而治", "逍遥游"],
    ),

    # ─── CHN-XBS-03: 外国小说研习 (L4: 3) ──────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-XBS-03-01", name="外国短篇小说", level=4, parent_code="CHN-XBS-03",
        description="莫泊桑、契诃夫、欧亨利等经典短篇小说的阅读与鉴赏",
        keywords=["短篇小说", "莫泊桑", "契诃夫", "欧亨利", "外国文学"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBS-03-02", name="叙事技巧分析", level=4, parent_code="CHN-XBS-03",
        description="外国小说的叙事视角、叙事顺序、悬念设置等技巧分析",
        keywords=["叙事技巧", "叙事视角", "叙事顺序", "悬念", "叙事结构"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBS-03-03", name="跨文化理解", level=4, parent_code="CHN-XBS-03",
        description="通过外国小说理解不同文化背景下的价值观与人文精神",
        keywords=["跨文化", "文化差异", "人文精神", "价值观", "文化理解"],
    ),

    # ═══ CHN-XBZ: 选择性必修中册 (L3: 2 单元) ════════════════════════════════════

    KnowledgeTreeSeed(
        code="CHN-XBZ-01", name="第一单元 科学与文化论著研习", level=3, parent_code="CHN-XBZ",
        description="学术论文的阅读方法与逻辑论证分析",
        keywords=["科学论著", "文化论著", "学术论文", "逻辑论证", "论著研习"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBZ-02", name="第二单元 中国现当代作家作品研习", level=3, parent_code="CHN-XBZ",
        description="现当代小说与散文的阅读，了解文学流派与风格",
        keywords=["现当代文学", "现当代小说", "现当代散文", "文学流派", "文学风格"],
    ),

    # ─── CHN-XBZ-01: 科学与文化论著研习 (L4: 2) ─────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-XBZ-01-01", name="学术论文阅读", level=4, parent_code="CHN-XBZ-01",
        description="学术论文的结构把握、论点提取与论证过程分析",
        keywords=["学术论文", "论文阅读", "论点提取", "论证过程", "论文结构"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBZ-01-02", name="逻辑论证分析", level=4, parent_code="CHN-XBZ-01",
        description="学术文本中的逻辑推理方法、论证有效性与常见逻辑谬误",
        keywords=["逻辑论证", "逻辑推理", "论证有效性", "逻辑谬误", "推理方法"],
    ),

    # ─── CHN-XBZ-02: 中国现当代作家作品研习 (L4: 3) ─────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-XBZ-02-01", name="现当代小说", level=4, parent_code="CHN-XBZ-02",
        description="鲁迅、沈从文、老舍等现当代小说家的代表作品与艺术特色",
        keywords=["现当代小说", "鲁迅", "沈从文", "老舍", "小说艺术"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBZ-02-02", name="现当代散文", level=4, parent_code="CHN-XBZ-02",
        description="朱自清、冰心、余秋雨等现当代散文家的代表作品与风格",
        keywords=["现当代散文", "朱自清", "冰心", "余秋雨", "散文风格"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBZ-02-03", name="文学流派与风格", level=4, parent_code="CHN-XBZ-02",
        description="现当代文学的主要流派(现实主义/浪漫主义/现代主义)与风格特征",
        keywords=["文学流派", "现实主义", "浪漫主义", "现代主义", "文学风格"],
    ),

    # ═══ CHN-XBX: 选择性必修下册 (L3: 2 单元) ════════════════════════════════════

    KnowledgeTreeSeed(
        code="CHN-XBX-01", name="第一单元 古典诗词研习", level=3, parent_code="CHN-XBX",
        description="诗词格律基础知识与诗词流派比较",
        keywords=["古典诗词", "诗词格律", "诗词流派", "诗词研习", "格律诗"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBX-02", name="第二单元 中国传统文化经典研习", level=3, parent_code="CHN-XBX",
        description="古代文论选读与文化经典的深入解读",
        keywords=["传统文化", "古代文论", "文化经典", "经典解读", "国学"],
    ),

    # ─── CHN-XBX-01: 古典诗词研习 (L4: 2) ──────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-XBX-01-01", name="诗词格律基础", level=4, parent_code="CHN-XBX-01",
        description="近体诗的平仄、押韵、对仗规则与词牌格律",
        keywords=["格律", "平仄", "押韵", "对仗", "词牌", "律诗", "绝句"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBX-01-02", name="诗词流派比较", level=4, parent_code="CHN-XBX-01",
        description="豪放派与婉约派、山水田园与边塞诗等流派的风格比较",
        keywords=["诗词流派", "豪放派", "婉约派", "山水田园", "边塞诗"],
    ),

    # ─── CHN-XBX-02: 中国传统文化经典研习 (L4: 2) ──────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-XBX-02-01", name="古代文论选读", level=4, parent_code="CHN-XBX-02",
        description="《文心雕龙》《典论·论文》等古代文论名篇的阅读与理解",
        keywords=["古代文论", "文心雕龙", "典论论文", "文学批评", "文论"],
    ),
    KnowledgeTreeSeed(
        code="CHN-XBX-02-02", name="文化经典解读", level=4, parent_code="CHN-XBX-02",
        description="《大学》《中庸》《礼记》等文化经典的篇章解读与思想理解",
        keywords=["文化经典", "大学", "中庸", "礼记", "经典解读", "国学经典"],
    ),

    # ═══ CHN-YUZI: 语言知识与表达 (L3: 5 章) ═════════════════════════════════════

    KnowledgeTreeSeed(
        code="CHN-YUZI-01", name="字音", level=3, parent_code="CHN-YUZI",
        description="汉字读音知识，多音字辨析与易读错字纠正",
        keywords=["字音", "读音", "多音字", "易错字音", "拼音"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-02", name="字形", level=3, parent_code="CHN-YUZI",
        description="汉字书写规范，易写错字辨析与形近字区分",
        keywords=["字形", "书写", "易错字", "形近字", "汉字规范"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-03", name="词语", level=3, parent_code="CHN-YUZI",
        description="词语运用能力，近义词辨析与成语的正确使用",
        keywords=["词语", "近义词", "成语", "词语辨析", "词语运用"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-04", name="病句修改", level=3, parent_code="CHN-YUZI",
        description="常见语病类型识别与修改：语序不当、搭配不当、成分残缺等",
        keywords=[
            "病句",
            "语病",
            "病句修改",
            "语序",
            "搭配",
            "成分残缺",
            "不合逻辑",
            "修改病句",
            "句式杂糅",
            "搭配不当",
            "有语病",
            "歧义",
            "残缺",
            "没有语病",
            "表意不明",
            "语序不当",
            "赘余",
            "重复累赘",
        ]
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-05", name="修辞手法", level=3, parent_code="CHN-YUZI",
        description="常见修辞手法的认识与运用：比喻、拟人、排比、对偶、反问等",
        keywords=[
            "修辞",
            "修辞手法",
            "比喻",
            "拟人",
            "排比",
            "对偶",
            "反问",
            "互文",
            "借代",
            "准确",
            "反复",
            "回环",
            "夸张",
            "对比",
            "得体",
            "比拟",
            "生动",
            "简明",
            "设问",
            "语言表达",
            "连贯",
            "通感",
            "顶真",
            "鲜明",
        ]
    ),

    # ─── CHN-YUZI-01: 字音 (L4: 2) ──────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-YUZI-01-01", name="多音字", level=4, parent_code="CHN-YUZI-01",
        description="常见多音字在不同语境中的正确读音辨别",
        keywords=["多音字", "语境辨音", "读音辨别", "多音多义", "字音"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-01-02", name="易读错字", level=4, parent_code="CHN-YUZI-01",
        description="日常生活中容易读错的字词的正确读音",
        keywords=["易读错字", "误读", "正确读音", "字音纠正", "读音规范"],
    ),

    # ─── CHN-YUZI-02: 字形 (L4: 2) ──────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-YUZI-02-01", name="易写错字", level=4, parent_code="CHN-YUZI-02",
        description="日常书写中容易写错的字词的正确写法",
        keywords=["易写错字", "错别字", "书写规范", "字形纠正", "正字"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-02-02", name="形近字", level=4, parent_code="CHN-YUZI-02",
        description="字形相近容易混淆的汉字的辨析与区分方法",
        keywords=["形近字", "字形辨析", "形似字", "偏旁区别", "字形区分"],
    ),

    # ─── CHN-YUZI-03: 词语 (L4: 2) ──────────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-YUZI-03-01", name="近义词辨析", level=4, parent_code="CHN-YUZI-03",
        description="近义词在语义、用法、语体色彩等方面的细微差异辨析",
        keywords=["近义词", "词语辨析", "语义差异", "用法区别", "语体色彩"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-03-02", name="成语运用", level=4, parent_code="CHN-YUZI-03",
        description="成语的正确理解与运用，避免望文生义、用错对象等常见错误",
        keywords=[
            "成语",
            "成语运用",
            "望文生义",
            "用错对象",
            "褒贬失当",
            "使用不恰当",
            "使用恰当",
            "依次填入",
            "俗语",
            "加点的成语",
            "恰当的一组",
            "成语使用",
            "歇后语",
            "熟语",
            "褒贬",
            "词语",
            "词语填空",
            "词语选用",
            "辨析",
            "近义词",
        ]
    ),

    # ─── CHN-YUZI-04: 病句修改 (L4: 3) ──────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-YUZI-04-01", name="语序不当", level=4, parent_code="CHN-YUZI-04",
        description="定语、状语、关联词等语序不当的识别与修改",
        keywords=["语序不当", "定语语序", "状语语序", "关联词语序", "语序"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-04-02", name="搭配不当", level=4, parent_code="CHN-YUZI-04",
        description="主谓搭配、动宾搭配、主宾搭配等不当的识别与修改",
        keywords=["搭配不当", "主谓搭配", "动宾搭配", "主宾搭配", "修饰搭配"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-04-03", name="成分残缺", level=4, parent_code="CHN-YUZI-04",
        description="句子成分(主语/谓语/宾语)残缺或赘余的识别与修改",
        keywords=["成分残缺", "缺主语", "缺谓语", "缺宾语", "成分赘余"],
    ),

    # ─── CHN-YUZI-05: 修辞手法 (L4: 5) ──────────────────────────────────────────

    KnowledgeTreeSeed(
        code="CHN-YUZI-05-01", name="比喻", level=4, parent_code="CHN-YUZI-05",
        description="明喻、暗喻、借喻的识别、理解与运用",
        keywords=["比喻", "明喻", "暗喻", "借喻", "本体", "喻体"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-05-02", name="拟人", level=4, parent_code="CHN-YUZI-05",
        description="拟人修辞的特征、表达效果与运用方法",
        keywords=["拟人", "拟人化", "人格化", "表达效果", "生动形象"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-05-03", name="排比", level=4, parent_code="CHN-YUZI-05",
        description="排比句的结构特征、节奏感与增强语势的表达效果",
        keywords=["排比", "排比句", "语势", "节奏感", "增强气势"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-05-04", name="对偶", level=4, parent_code="CHN-YUZI-05",
        description="对偶句的结构对称、音韵和谐与凝练表达",
        keywords=["对偶", "对仗", "对称", "音韵和谐", "凝练"],
    ),
    KnowledgeTreeSeed(
        code="CHN-YUZI-05-05", name="反问", level=4, parent_code="CHN-YUZI-05",
        description="反问句的语气强化作用与设问的区别",
        keywords=["反问", "反问句", "设问", "语气强化", "无疑而问"],
    ),
]
