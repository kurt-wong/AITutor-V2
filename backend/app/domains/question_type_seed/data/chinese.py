"""
Chinese question type seed data.

Source: QUESTION_TYPE_TREE.md -- 全国新高考 + 北京高考 2026
Subject code: CHN
"""

from __future__ import annotations

from ..types import QuestionTypeSeed

# ═══ Level 1: Major categories ════════════════════════════════════════════════

_L1 = [
    QuestionTypeSeed(
        code="CHN-MODERN",
        name="现代文阅读",
        level=1,
        parent_code=None,
        description="现代文阅读理解能力考查，含信息类与文学类文本",
        keywords=["现代文阅读", "modern reading", "阅读理解"],
    ),
    QuestionTypeSeed(
        code="CHN-ANCIENT",
        name="古诗文阅读",
        level=1,
        parent_code=None,
        description="古诗文阅读与鉴赏能力考查",
        keywords=["古诗文", "ancient poetry & prose", "文言文", "古诗"],
    ),
    QuestionTypeSeed(
        code="CHN-LANG",
        name="语言文字运用",
        level=1,
        parent_code=None,
        description="语言文字运用能力考查",
        keywords=["语言文字运用", "language application", "语用"],
    ),
    QuestionTypeSeed(
        code="CHN-WRITE",
        name="写作",
        level=1,
        parent_code=None,
        description="写作能力考查，含材料议论文、记叙文与任务驱动型",
        keywords=["写作", "writing", "作文"],
    ),
    # -- 北京卷特有
    QuestionTypeSeed(
        code="CHN-BOOK",
        name="整本书阅读",
        level=1,
        parent_code=None,
        description="北京卷特有：整本书阅读考查（如《红楼梦》），考查对主要人物、事件的整体把握",
        keywords=["整本书阅读", "whole book reading", "红楼梦", "名著阅读"],
    ),
]

# ═══ Level 2: Subcategories ══════════════════════════════════════════════════

_L2 = [
    # -- 现代文阅读
    QuestionTypeSeed(
        code="CHN-MODERN-INFO",
        name="信息类文本",
        level=2,
        parent_code="CHN-MODERN",
        description="论述文/科普文/新闻访谈等信息类文本阅读",
        keywords=["信息类文本", "informational text", "论述文", "科普文"],
    ),
    QuestionTypeSeed(
        code="CHN-MODERN-LIT",
        name="文学类文本",
        level=2,
        parent_code="CHN-MODERN",
        description="小说/散文等文学类文本阅读",
        keywords=["文学类文本", "literary text", "小说", "散文"],
    ),
    # -- 北京卷特有
    QuestionTypeSeed(
        code="CHN-MODERN-MULTI",
        name="多文本阅读",
        level=2,
        parent_code="CHN-MODERN",
        description="北京卷特有：多则材料对比阅读，客观题4道+主观题1道",
        keywords=["多文本阅读", "multi-text reading", "多材料阅读", "非连续性文本"],
    ),
    # -- 古诗文阅读
    QuestionTypeSeed(
        code="CHN-ANCIENT-PROSE",
        name="文言文阅读",
        level=2,
        parent_code="CHN-ANCIENT",
        description="文言文阅读理解",
        keywords=["文言文", "classical Chinese prose", "文言"],
    ),
    QuestionTypeSeed(
        code="CHN-ANCIENT-POEM",
        name="古代诗歌阅读",
        level=2,
        parent_code="CHN-ANCIENT",
        description="古代诗歌鉴赏",
        keywords=["古代诗歌", "ancient poetry", "古诗鉴赏"],
    ),
    QuestionTypeSeed(
        code="CHN-ANCIENT-DICT",
        name="名篇名句默写",
        level=2,
        parent_code="CHN-ANCIENT",
        description="情境式理解默写",
        keywords=["默写", "dictation", "名句名篇", "情境默写"],
    ),
    # -- 写作
    QuestionTypeSeed(
        code="CHN-WRITE-ARGUE",
        name="材料议论文",
        level=2,
        parent_code="CHN-WRITE",
        description="材料驱动的议论文写作（主流题型）",
        keywords=["材料议论文", "argumentative essay", "议论文"],
    ),
    QuestionTypeSeed(
        code="CHN-WRITE-TASK",
        name="任务驱动型",
        level=2,
        parent_code="CHN-WRITE",
        description="任务驱动型写作，含书信、演讲稿、倡议书、通知等",
        keywords=["任务驱动型", "task-driven writing", "书信", "演讲稿"],
    ),
    # -- 北京卷特有
    QuestionTypeSeed(
        code="CHN-WRITE-NARR",
        name="记叙文",
        level=2,
        parent_code="CHN-WRITE",
        description="北京卷特有：大作文二选一中的记叙文选项",
        keywords=["记叙文", "narrative essay", "叙事散文"],
    ),
]

# ═══ Level 3: Specific types ═════════════════════════════════════════════════

_L3 = [
    # -- 信息类文本
    QuestionTypeSeed(
        code="CHN-MODERN-INFO-ARG",
        name="论证分析",
        level=3,
        parent_code="CHN-MODERN-INFO",
        description="论证结构、论证方法分析",
        keywords=["论证分析", "argumentation analysis", "论证结构", "论证方法"],
    ),
    QuestionTypeSeed(
        code="CHN-MODERN-INFO-INF",
        name="内容推断",
        level=3,
        parent_code="CHN-MODERN-INFO",
        description="整合材料进行推理和现实应用",
        keywords=["内容推断", "content inference", "整合材料"],
    ),
    QuestionTypeSeed(
        code="CHN-MODERN-INFO-CHART",
        name="图文解读",
        level=3,
        parent_code="CHN-MODERN-INFO",
        description="结合图表数据作答",
        keywords=["图文解读", "chart & text integration", "图表"],
    ),
    # -- 文学类文本
    QuestionTypeSeed(
        code="CHN-MODERN-LIT-CHAR",
        name="人物形象",
        level=3,
        parent_code="CHN-MODERN-LIT",
        description="性格概括、心理变化分析",
        keywords=["人物形象", "character analysis", "性格概括", "心理变化"],
    ),
    QuestionTypeSeed(
        code="CHN-MODERN-LIT-RHET",
        name="手法鉴赏",
        level=3,
        parent_code="CHN-MODERN-LIT",
        description="修辞/视角/结构赏析",
        keywords=["手法鉴赏", "rhetoric & technique", "修辞", "赏析"],
    ),
    QuestionTypeSeed(
        code="CHN-MODERN-LIT-THEME",
        name="意蕴探究",
        level=3,
        parent_code="CHN-MODERN-LIT",
        description="标题含义、结尾作用、多重主旨探究",
        keywords=["意蕴探究", "theme exploration", "主旨", "标题含义"],
    ),
    # -- 文言文阅读
    QuestionTypeSeed(
        code="CHN-ANCIENT-PROSE-TRANS",
        name="句子翻译",
        level=3,
        parent_code="CHN-ANCIENT-PROSE",
        description="实词/虚词/特殊句式翻译",
        keywords=["句子翻译", "translation", "实词", "虚词", "特殊句式"],
    ),
    QuestionTypeSeed(
        code="CHN-ANCIENT-PROSE-QA",
        name="内容简答",
        level=3,
        parent_code="CHN-ANCIENT-PROSE",
        description="事件因果、人物品性、观点比较",
        keywords=["内容简答", "short answer", "事件因果", "人物品性"],
    ),
    # -- 古代诗歌阅读
    QuestionTypeSeed(
        code="CHN-ANCIENT-POEM-TECH",
        name="手法赏析",
        level=3,
        parent_code="CHN-ANCIENT-POEM",
        description="借景抒情/用典/对比等手法赏析",
        keywords=["手法赏析", "technique appreciation", "借景抒情", "用典"],
    ),
    QuestionTypeSeed(
        code="CHN-ANCIENT-POEM-EMO",
        name="情感主旨",
        level=3,
        parent_code="CHN-ANCIENT-POEM",
        description="概括情感、观点态度",
        keywords=["情感主旨", "emotion & theme", "情感概括"],
    ),
    QuestionTypeSeed(
        code="CHN-ANCIENT-POEM-LANG",
        name="语言风格",
        level=3,
        parent_code="CHN-ANCIENT-POEM",
        description="炼字、风格流派分析",
        keywords=["语言风格", "language style", "炼字", "风格流派"],
    ),
    # -- 名篇名句默写
    QuestionTypeSeed(
        code="CHN-ANCIENT-DICT-CTX",
        name="情境式理解默写",
        level=3,
        parent_code="CHN-ANCIENT-DICT",
        description="在语言运用情境中灵活调用经典诗文",
        keywords=["情境默写", "contextual memorization", "理解默写"],
    ),
    # -- 材料议论文
    QuestionTypeSeed(
        code="CHN-WRITE-ARGUE-DIAL",
        name="辩证分析",
        level=3,
        parent_code="CHN-WRITE-ARGUE",
        description="辩证思维分析，多角度论证",
        keywords=["辩证分析", "dialectical analysis", "辩证思维"],
    ),
    QuestionTypeSeed(
        code="CHN-WRITE-ARGUE-THESIS",
        name="论点论证",
        level=3,
        parent_code="CHN-WRITE-ARGUE",
        description="确立论点并进行论证",
        keywords=["论点论证", "thesis & evidence", "论点", "论证"],
    ),
    # -- 任务驱动型
    QuestionTypeSeed(
        code="CHN-WRITE-TASK-FORMATS",
        name="书信/演讲稿/倡议书/通知",
        level=3,
        parent_code="CHN-WRITE-TASK",
        description="各类任务驱动型应用文格式",
        keywords=["书信", "演讲稿", "倡议书", "通知", "letters", "speeches"],
    ),
    # -- 语言文字运用 (level 2 作为叶子节点)
    QuestionTypeSeed(
        code="CHN-LANG-RHET",
        name="修辞判断",
        level=2,
        parent_code="CHN-LANG",
        description="比喻/拟人/排比等修辞效果判断",
        keywords=["修辞判断", "rhetoric identification", "比喻", "拟人", "排比"],
    ),
    QuestionTypeSeed(
        code="CHN-LANG-SENT",
        name="语句补写",
        level=2,
        parent_code="CHN-LANG",
        description="根据上下文逻辑衔接补写语句",
        keywords=["语句补写", "sentence completion", "上下文衔接"],
    ),
    QuestionTypeSeed(
        code="CHN-LANG-ERR",
        name="语病修改",
        level=2,
        parent_code="CHN-LANG",
        description="病句辨析与修改",
        keywords=["语病修改", "error correction", "病句"],
    ),
    QuestionTypeSeed(
        code="CHN-LANG-TRANS",
        name="句式变换",
        level=2,
        parent_code="CHN-LANG",
        description="压缩/扩写/重组等句式变换",
        keywords=["句式变换", "sentence transformation", "压缩", "扩写"],
    ),
]

CHINESE_QUESTION_TYPES: list[QuestionTypeSeed] = _L1 + _L2 + _L3
