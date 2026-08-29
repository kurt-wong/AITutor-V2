"""
English question type seed data.

Source: QUESTION_TYPE_TREE.md -- 全国新高考 + 北京高考 2026
Subject code: ENG
"""

from __future__ import annotations

from ..types import QuestionTypeSeed

# ═══ Level 1: Major categories ════════════════════════════════════════════════

_L1 = [
    QuestionTypeSeed(
        code="ENG-LISTEN",
        name="听力",
        level=1,
        parent_code=None,
        description="听力理解能力考查",
        keywords=["听力", "listening", "听力理解"],
    ),
    QuestionTypeSeed(
        code="ENG-READ",
        name="阅读理解",
        level=1,
        parent_code=None,
        description="阅读理解能力考查，含A-D篇与七选五",
        keywords=["阅读理解", "reading comprehension", "阅读"],
    ),
    QuestionTypeSeed(
        code="ENG-USE",
        name="语言运用",
        level=1,
        parent_code=None,
        description="语言知识运用能力考查，含完形填空与语法填空",
        keywords=["语言运用", "language use", "完形填空", "语法填空"],
    ),
    QuestionTypeSeed(
        code="ENG-WRITE",
        name="写作",
        level=1,
        parent_code=None,
        description="书面表达能力考查，含应用文与读后续写",
        keywords=["写作", "writing", "书面表达"],
    ),
    # -- 北京卷特有：听说机考（50分，与笔试分离，计算机考试，一年两考）
    QuestionTypeSeed(
        code="ENG-SPEAK",
        name="听说机考",
        level=1,
        parent_code=None,
        description="北京卷特有：英语听说计算机考试（满分50分），含听后选择、听后记录、听后转述、短文朗读、回答问题",
        keywords=["听说机考", "speaking test", "computer-based test", "口语考试"],
    ),
]

# ═══ Level 2: Subcategories ══════════════════════════════════════════════════

_L2 = [
    # -- Listening subtypes
    QuestionTypeSeed(
        code="ENG-LISTEN-DETAIL",
        name="获取事实细节",
        level=2,
        parent_code="ENG-LISTEN",
        description="从听力材料中获取具体事实信息",
        keywords=["事实细节", "factual details", "信息获取"],
    ),
    QuestionTypeSeed(
        code="ENG-LISTEN-MAIN",
        name="主旨要义",
        level=2,
        parent_code="ENG-LISTEN",
        description="理解听力材料的主旨大意",
        keywords=["主旨要义", "main idea", "中心思想"],
    ),
    QuestionTypeSeed(
        code="ENG-LISTEN-INFER",
        name="推理判断",
        level=2,
        parent_code="ENG-LISTEN",
        description="根据听力材料进行推理和判断",
        keywords=["推理判断", "inference", "推断"],
    ),
    # -- Reading subtypes
    QuestionTypeSeed(
        code="ENG-READ-STD",
        name="A-D篇",
        level=2,
        parent_code="ENG-READ",
        description="传统阅读理解四篇文章",
        keywords=["A-D篇", "standard passages", "阅读四篇"],
    ),
    QuestionTypeSeed(
        code="ENG-READ-7TO5",
        name="七选五",
        level=2,
        parent_code="ENG-READ",
        description="七选五补全短文，考查篇章逻辑与衔接",
        keywords=["七选五", "gap-fill", "补全短文", "seven-choice"],
    ),
    # -- Language Use subtypes
    QuestionTypeSeed(
        code="ENG-USE-CLOZE",
        name="完形填空",
        level=2,
        parent_code="ENG-USE",
        description="完形填空，考查词汇辨析与语篇逻辑",
        keywords=["完形填空", "cloze test", "完形"],
    ),
    QuestionTypeSeed(
        code="ENG-USE-GRAMMAR",
        name="语法填空",
        level=2,
        parent_code="ENG-USE",
        description="语法填空，分有提示词与无提示词两类",
        keywords=["语法填空", "grammar fill-in", "语法"],
    ),
    # -- Writing subtypes
    QuestionTypeSeed(
        code="ENG-WRITE-PRACTICAL",
        name="应用文",
        level=2,
        parent_code="ENG-WRITE",
        description="应用文写作，如建议信、申请信、邀请信、通知等",
        keywords=["应用文", "practical writing", "书信", "通知"],
    ),
    QuestionTypeSeed(
        code="ENG-WRITE-CONTINUE",
        name="读后续写",
        level=2,
        parent_code="ENG-WRITE",
        description="读后续写，根据前文续写故事",
        keywords=["读后续写", "continuation writing", "续写"],
    ),
    # -- 北京卷特有：听说机考子题型
    QuestionTypeSeed(
        code="ENG-SPEAK-LC",
        name="听后选择",
        level=2,
        parent_code="ENG-SPEAK",
        description="听录音后选择正确答案",
        keywords=["听后选择", "listen & choose"],
    ),
    QuestionTypeSeed(
        code="ENG-SPEAK-LR",
        name="听后记录",
        level=2,
        parent_code="ENG-SPEAK",
        description="听录音后记录关键信息",
        keywords=["听后记录", "listen & record"],
    ),
    QuestionTypeSeed(
        code="ENG-SPEAK-LRTELL",
        name="听后转述",
        level=2,
        parent_code="ENG-SPEAK",
        description="听录音后转述内容",
        keywords=["听后转述", "listen & retell"],
    ),
    QuestionTypeSeed(
        code="ENG-SPEAK-READ",
        name="短文朗读",
        level=2,
        parent_code="ENG-SPEAK",
        description="朗读指定短文",
        keywords=["短文朗读", "passage reading", "朗读"],
    ),
    QuestionTypeSeed(
        code="ENG-SPEAK-QA",
        name="回答问题",
        level=2,
        parent_code="ENG-SPEAK",
        description="根据所听内容回答问题",
        keywords=["回答问题", "question & answer"],
    ),
]

# ═══ Level 3: Specific types ═════════════════════════════════════════════════

_L3 = [
    # -- A-D篇细分
    QuestionTypeSeed(
        code="ENG-READ-DETAIL",
        name="细节理解",
        level=3,
        parent_code="ENG-READ-STD",
        description="从文章中查找和理解具体细节信息",
        keywords=["细节理解", "detail understanding", "细节题"],
    ),
    QuestionTypeSeed(
        code="ENG-READ-INFER",
        name="推理判断",
        level=3,
        parent_code="ENG-READ-STD",
        description="根据文章内容进行推理和判断",
        keywords=["推理判断", "inference & judgment", "推断题"],
    ),
    QuestionTypeSeed(
        code="ENG-READ-MAIN",
        name="主旨要义",
        level=3,
        parent_code="ENG-READ-STD",
        description="概括文章主旨大意或段落大意",
        keywords=["主旨要义", "main idea", "主旨题"],
    ),
    QuestionTypeSeed(
        code="ENG-READ-VOCAB",
        name="词义猜测",
        level=3,
        parent_code="ENG-READ-STD",
        description="根据上下文推测生词或短语的含义",
        keywords=["词义猜测", "vocabulary guessing", "猜词"],
    ),
    # -- 七选五细分
    QuestionTypeSeed(
        code="ENG-READ-7TO5-COHESION",
        name="篇章逻辑与衔接",
        level=3,
        parent_code="ENG-READ-7TO5",
        description="考查段落间的逻辑关系与衔接手段",
        keywords=["篇章逻辑", "cohesion", "衔接", "逻辑关系"],
    ),
    # -- 完形填空细分
    QuestionTypeSeed(
        code="ENG-USE-CLOZE-VOCAB",
        name="词汇辨析",
        level=3,
        parent_code="ENG-USE-CLOZE",
        description="完形填空中考查近义词、词组辨析",
        keywords=["词汇辨析", "vocabulary discrimination", "词义辨析"],
    ),
    QuestionTypeSeed(
        code="ENG-USE-CLOZE-LOGIC",
        name="语篇逻辑",
        level=3,
        parent_code="ENG-USE-CLOZE",
        description="完形填空中考查上下文逻辑连贯",
        keywords=["语篇逻辑", "discourse logic", "上下文逻辑"],
    ),
    # -- 语法填空细分
    QuestionTypeSeed(
        code="ENG-USE-GRAMMAR-CUED",
        name="有提示词",
        level=3,
        parent_code="ENG-USE-GRAMMAR",
        description="给出词根提示，考查时态、非谓语、词形转换等",
        keywords=["有提示词", "with cues", "时态", "非谓语", "词形转换"],
    ),
    QuestionTypeSeed(
        code="ENG-USE-GRAMMAR-UNCUED",
        name="无提示词",
        level=3,
        parent_code="ENG-USE-GRAMMAR",
        description="无提示词，考查冠词、介词、连词、关系词等",
        keywords=["无提示词", "without cues", "冠词", "介词", "连词", "关系词"],
    ),
    # -- 应用文细分
    QuestionTypeSeed(
        code="ENG-WRITE-PRACTICAL-LETTER",
        name="建议信/申请信/邀请信",
        level=3,
        parent_code="ENG-WRITE-PRACTICAL",
        description="各类书信类应用文写作",
        keywords=["建议信", "申请信", "邀请信", "letter"],
    ),
    QuestionTypeSeed(
        code="ENG-WRITE-PRACTICAL-NOTICE",
        name="通知/投稿",
        level=3,
        parent_code="ENG-WRITE-PRACTICAL",
        description="通知、投稿等非书信类应用文写作",
        keywords=["通知", "投稿", "notice", "submission"],
    ),
    # -- 读后续写细分
    QuestionTypeSeed(
        code="ENG-WRITE-CONTINUE-PLOT",
        name="情节衔接",
        level=3,
        parent_code="ENG-WRITE-CONTINUE",
        description="续写部分与原文情节的自然衔接",
        keywords=["情节衔接", "plot connection", "情节发展"],
    ),
    QuestionTypeSeed(
        code="ENG-WRITE-CONTINUE-CHARACTER",
        name="人物刻画",
        level=3,
        parent_code="ENG-WRITE-CONTINUE",
        description="续写中的人物形象塑造与性格展现",
        keywords=["人物刻画", "character depiction", "人物描写"],
    ),
    QuestionTypeSeed(
        code="ENG-WRITE-CONTINUE-THEME",
        name="主题呼应",
        level=3,
        parent_code="ENG-WRITE-CONTINUE",
        description="续写内容与原文主题的呼应与深化",
        keywords=["主题呼应", "theme echo", "主题升华"],
    ),
    QuestionTypeSeed(
        code="ENG-WRITE-CONTINUE-STRUCTURE",
        name="高级句式",
        level=3,
        parent_code="ENG-WRITE-CONTINUE",
        description="续写中运用高级句式和修辞手法",
        keywords=["高级句式", "advanced structures", "修辞", "句式升级"],
    ),
]

ENGLISH_QUESTION_TYPES: list[QuestionTypeSeed] = _L1 + _L2 + _L3
