"""科目专用 Prompt 模块。

每个科目包含该科目的典型题型和特殊规则：
- 英语：完形填空、七选五、语法填空、阅读理解、写作
- 数学：选择题组、解答题、证明题
- 语文：现代文阅读、文言文、诗歌、写作
- 理科（物理/化学/生物）：实验题、计算题、综合题
- 社科（政治/历史/地理）：材料分析题
"""

from ..registry import PromptModule


class EnglishRules(PromptModule):
    """英语专用规则。"""

    def __init__(self):
        super().__init__(
            name="english",
            version="1.0",
            description="英语试卷专用规则",
        )

    def get_rules(self) -> str:
        return """#### 英语典型题型

**完形填空（cloze）：**
- 共享文章 + 多个空位（通常 10-15 个）
- 合并为综合题，每个空位是子题
- 子题题型为 single_choice（A/B/C/D 四选一）

**七选五（seven_to_five）：**
- 共享文章 + 5 个空位 + 7 个选项（A-G，2 个多余）
- 合并为综合题，每个空位是子题
- 子题题型为 single_choice

**语法填空（grammar_fill）：**
- 按 A/B/C 分组，每组共享一篇短文
- 每组独立为一个综合题（如 A 组 11-13、B 组 14-17、C 组 18-20）
- 子题题型为 fill_in（无选项，直接填词）

**选词填空（wordbank_fill）：**
- 方框中的单词保存到 word_bank 字段（如 ["pack", "confuse", "equal"]）
- 每个句子是子题，子题题型为 fill_in
- 合并为综合题，容器 stem 包含任务说明（如"A. 请用方框中的单词完成句子。B. 请用方框中单词的正确形式完成句子。"）

**阅读理解（reading）：**
- 每篇文章独立为一个综合题（如 A 篇 26-28、B 篇 29-32、C 篇 33-36）
- 共享文章保存到 shared_material
- 每道选择题是子题，子题题型为 single_choice

**阅读表达（reading_expression）：**
- 共享文章 + 多道简答题（通常 4-5 题）
- 合并为综合题，每道简答是子题
- 子题题型为 short_answer

**写作（essay/writing）：**
- 独立题，不合并
- 题型为 essay（内部按 short_answer 处理）
- 示例作文保存到 answer

#### 英语专用规则
1. 独立带题号的句子（无共享文章）→ 保持独立题
2. 选词填空/词汇填空：多个句子共享同一个词库 → 合并为综合题，word_bank 字段必须填入方框单词
3. ❌ 不得仅因为题型相同或题号连续就合并
4. 容器 stem 只放任务说明/指令（如"第一节(共10小题;每小题1.5分，共15分) 阅读下面短文..."），不放文章内容
5. 文章/材料内容只放 shared_material，不放 stem
6. **七选五（seven_to_five）必须保留**：七选五是 is_composite=true 的综合题，必须输出为一道题，不能吞掉或跳过。子题保留 A-G 选项完整性和各自的 sub_questions

#### 综合题子题展示字段要求

**每个子题对象必须包含以下字段：**
- qno: 子题编号
- question_type: 子题题型
- answer: 子题答案
- stem_line_ids: 子题题干行号（必填，禁止空数组）
- answer_line_ids: 子题答案行号（从答案区提取，如无法确定输出 []）
- explanation_line_ids: 子题详解行号（从详解区提取，如无法确定输出 []）
- scoring_standard: 子题评分标准（如"每空1分"，如无法确定输出 null）
- answer_images: 子题答案图片（如无图片输出 []）

**父题必须包含：**
- scoring_standard: **必填**，整体评分标准（如"共10小题，每空1.5分，共15分"），从试卷评分说明中提取
"""


class MathRules(PromptModule):
    """数学专用规则。"""

    def __init__(self):
        super().__init__(
            name="math",
            version="1.0",
            description="数学试卷专用规则",
        )

    def get_rules(self) -> str:
        return """#### 数学典型题型

**单选题（single_choice）：**
- 通常 8 题，每题 5 分
- 独立题，不合并

**多选题（multiple_choice）：**
- 通常 4 题，每题 5 分（部分选对得 2 分）
- 独立题，不合并

**填空题（fill_in）：**
- 通常 4 题，每题 5 分
- 独立题，不合并

**解答题（short_answer）：**
- 通常 6 题，分值 10-14 分不等
- 包含多个小问（(1)(2)(3)），合并为综合题
- 每个小问是子题

**选择题组（共享题图）：**
- "读图完成 18—20 题"的 18/19/20
- 共享题图 → 合并为综合题
- 每道选择题是子题

#### 数学专用规则
1. 公式和符号优先使用 PP-StructureV3（视觉识别更准确）
2. 结构签名（structure_signature）可选：object, task, method, condition
3. 多个小问的解答题，每个小问的最终结果行单独记录
"""


class ChineseRules(PromptModule):
    """语文专用规则。"""

    def __init__(self):
        super().__init__(
            name="chinese",
            version="1.0",
            description="语文试卷专用规则",
        )

    def get_rules(self) -> str:
        return """#### 语文典型题型

**现代文阅读：**
- 信息类文本：论述文/科普文/新闻访谈
- 文学类文本：小说/散文
- 共享选段 + 多道选择题/简答题 → 合并为综合题

**古诗文阅读：**
- 文言文阅读：共享原文 + 翻译/简答
- 古代诗歌阅读：共享诗歌 + 赏析/简答
- 默写题：多个空位，合并为综合题

**语言文字运用：**
- 修辞判断、语句补写、语病修改、句式变换
- 通常为独立题

**写作：**
- 材料议论文（主流）
- 任务驱动型（书信/演讲稿等）
- 独立题，不合并

#### 语文专用规则
1. 文言文注释单独保存为 shared_material_notes
2. 表格类答案使用 answer_structure
3. 默写题评分标准保存到 scoring_standard
"""


class ScienceRules(PromptModule):
    """理科专用规则（物理/化学/生物）。"""

    def __init__(self):
        super().__init__(
            name="science",
            version="1.0",
            description="理科试卷专用规则（物理/化学/生物）",
        )

    def get_rules(self) -> str:
        return """#### 理科典型题型

**实验题：**
- 实验装置描述 + 多个小问
- 合并为综合题，每个小问是子题
- stem 包含实验装置描述和实验条件

**计算题：**
- 多个小问（(1)(2)(3)）
- 合并为综合题，每个小问是子题

**综合题（工艺流程/实验综合）：**
- 共享流程图/实验描述 + 多道题
- 合并为综合题

#### 理科专用规则
1. 公式和符号优先使用 PP-StructureV3
2. 化学式标准化：Cl₂、OH⁻、Fe₃O₄
3. 题图中的图片绑定到对应 images
4. 答案区中的图片保存到 answer_images
"""


class GenericRules(PromptModule):
    """通用规则（政治/历史/地理/未知科目）。"""

    def __init__(self):
        super().__init__(
            name="generic",
            version="1.0",
            description="通用试卷专用规则",
        )

    def get_rules(self) -> str:
        return """#### 通用题型

**材料分析题：**
- 共享材料 + 多道选择题/简答题
- 合并为综合题

**选择题：**
- 独立题，不合并

**简答题/论述题：**
- 独立题或综合题子题

#### 通用规则
1. 按语义判断是否合并，不按题号机械合并
2. 共享材料/题图/前提条件 → 合并
3. 每道题引用各自独立的图/材料 → 保持独立
"""


# 创建全局实例
english_rules = EnglishRules()
math_rules = MathRules()
chinese_rules = ChineseRules()
science_rules = ScienceRules()
generic_rules = GenericRules()
