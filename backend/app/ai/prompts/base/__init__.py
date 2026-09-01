"""基础 Prompt 模块 — 所有科目共享的总则。

包含：
- JSON 输出规范
- 行号规范
- 难度判断标准
- 综合题识别规则
- 答案/详解提取规则
"""

from ..registry import PromptModule


class JsonOutputRules(PromptModule):
    """JSON 输出规范。"""

    def __init__(self):
        super().__init__(
            name="json_output",
            version="1.0",
            description="JSON 输出格式规范",
        )

    def get_rules(self) -> str:
        return """### JSON 输出规范
1. 严格输出 JSON 对象，不要输出其他内容
2. 每个题目必须包含：question_number, question_type, section_id, stem_line_ids, options_line_ids, answer_line_ids, explanation_line_ids, scoring_standard
3. question_type 使用 canonical 枚举：single_choice / multiple_choice / fill_in / true_false / short_answer
4. 英语写作/书面表达必须输出 essay（内部按 short_answer 处理，但入库必须保留 essay 原始题型）
5. 可选字段：score, knowledge_points, answer, word_bank, answer_structure, structure_signature, answer_images
6. stem_markers 是语义定界标记：start 必须是该题题干在文档中的真实开头子串，end 必须是题干在文档中的真实结尾子串
7. structure_signature 是 Annotation（LLM 解释），不是事实，随 prompt 版本变化。无法可靠判断时输出 null，禁止编造
8. scoring_standard：评分标准，从试卷中的评分说明中提取。
   - 综合题父题：输出本组的 per-question 评分（如"共3小题，每空1分，共3分"），❌ 不要输出整节 header（如"第二节(共10小题;每小题1分，共10分）"）
   - 独立题：输出该题评分（如"每空1.5分"）
   - 子题：输出单题评分（如"每空1分"）
   - 判断规则：如果试卷中有"共N小题，每小题X分，共Y分"格式，提取该格式作为父题 scoring_standard；如果只有整节 header（如"第二节(共10小题;每小题1分，共10分）"），则从中提取"每小题1分"作为 per-question 评分
   - 无评分标准时输出 null
9. answer_images：答案区的图片列表，格式为 [{"page_no": 1, "bbox": {"x1": 0, "y1": 0, "x2": 100, "y2": 100}, "description": "图1"}]，无图片输出 []
"""


class LineIdRules(PromptModule):
    """行号规范。"""

    def __init__(self):
        super().__init__(
            name="line_id",
            version="1.0",
            description="行号引用规范",
        )

    def get_rules(self) -> str:
        return """### 行号规范
1. 行号必须是文档中实际存在的行号（格式如 P1L001、N1L001）
2. stem_line_ids：题干行号（含题号行、题干正文、图注说明）
3. options_line_ids：选项行号，key 是选项标签（A/B/C/D），value 是行号列表
4. answer_line_ids：答案行号，只指向最终结果所在行
5. explanation_line_ids：详解行号，指向解题过程所在行
6. shared_material_line_ids：共享材料行号（综合题）
7. ❌ 禁止把推导、变换、证明、中间计算过程行放入 answer_line_ids
"""


class DifficultyRules(PromptModule):
    """难度判断标准。"""

    def __init__(self):
        super().__init__(
            name="difficulty",
            version="1.0",
            description="难度判断标准",
        )

    def get_rules(self) -> str:
        return """### 难度判断标准
1. difficulty 为必填字段，取值 1-5 整数
2. 判断依据：
   - 1=基础：考查单一概念的直接套用
   - 2=简单：需一步推理
   - 3=中等：需两步以上推理或综合两个知识点
   - 4=较难：涉及多知识点综合、复杂计算或易错陷阱
   - 5=困难：压轴题、强综合、非常规思路
3. 若确实无法判断，输出 3（中等），不得输出 null
"""


class CompositeRules(PromptModule):
    """综合题识别规则。"""

    def __init__(self):
        super().__init__(
            name="composite",
            version="1.0",
            description="综合题识别规则",
        )

    def get_rules(self) -> str:
        return """### 综合题识别规则

对于共享同一段材料/文章/实验描述/题图/前提条件的若干子题，必须输出为一道综合题，不要拆成独立题目。

**共享即合并（不依赖能否独立作答）：**
- 只要多道题共享同一份材料/文章/题图/图表/前提条件，就合并为一道综合题
- 共享信号：卷面标识（"读图完成 N—M 题"）、题干引用同一图表、shared_material_line_ids 重叠

**英语试卷分组注意（按语义判断，不按题号机械合并）：**
- 多个小题只有在共享同一篇材料/文章/短文时才合并为综合题
- 独立带题号的句子，去掉材料后仍能独立作答，必须保持独立题
- ❌ 不得仅因为题型相同或题号连续就合并

**综合题容器字段标准：**

容器（分组题头）不是独立题目，只是承载统一材料和子题分组。

容器应该输出：
- is_composite = true
- question_number = 分组标识（如 "1-10"）
- question_type = 综合题类型（如 cloze / grammar_fill / reading）
- stem = 统一任务说明/指令（只放说明，不放文章内容）
- stem_line_ids = 任务说明行号（只指向说明行，不指向文章行）
- shared_material_line_ids = 材料全文行号（文章/短文/词库）
- scoring_standard = 整个分组的评分标准
- sub_questions = 子题元数据数组

**⚠️ stem 与 shared_material 的区分：**
- stem = 任务说明/指令（如"阅读下面短文，掌握其大意，从每题所给的 A、B、C、D 四个选项中..."）
- shared_material = 文章/材料内容（如 "The Ultimate Goal\nI sat in the dressing room..."）
- ❌ 禁止把文章内容放入 stem
- ❌ 禁止把任务说明放入 shared_material

**⚠️ stem 与 scoring_standard 的区分（section header 归属）：**
- stem 只放任务说明/指令本身，❌ 不放 section header（如"第一节(共10小题;每小题1.5分，共15分）"）
- section header 中的评分信息放入 scoring_standard
- 示例：看到"第一节(共10小题;每小题1.5分，共15分) 阅读下面短文，掌握其大意..."
  - stem = "阅读下面短文，掌握其大意..."（只保留任务指令）
  - scoring_standard = "共10小题，每小题1.5分，共15分"（提取评分信息）
- 子节（A/B/C 等）同理：stem 只包含子节标签 + 任务说明
- 也❌ 不要把"并在答题卡上将该项涂黑""请在答题卡指定区域作答"等考试操作指令放入 stem

**容器不应该输出（设为 null 或 []）：**
- answer = null（答案只在子题中）
- answer_line_ids = []
- answer_region = null
- answer_images = []
- explanation = null（详解只在子题中）
- explanation_line_ids = []
- explanation_region = null
- options = null（选项只在子题中）
- options_line_ids = {}

**⚠️ 子题 stem_line_ids 必须给出：**
- 填空类子题：指向含该题号/空位的那一行
- 选择题组子题：指向各题题干行
- 禁止输出空数组
"""


class AnswerRules(PromptModule):
    """答案/详解提取规则。"""

    def __init__(self):
        super().__init__(
            name="answer",
            version="1.0",
            description="答案和详解提取规则",
        )

    def get_rules(self) -> str:
        return """### 答案/详解提取规则

**answer 字段：**
1. 仅用于 single_choice / multiple_choice / true_false
2. 值为答案表或题后答案中该题的短答案（如 "C"、"AB"）
3. 其他题型输出 null
4. ❌ 不要输出题干、选项、详解或解题过程原文

**answer_line_ids 字段：**
1. 只指向该题最终结果所在的实际 L1 行
2. 选择题/填空题：指向答案表或题后答案行
3. 解答题：按小题指向每个小题的最终结果行
4. ❌ 禁止把推导、变换、证明、中间计算过程行放入 answer_line_ids

**explanation_line_ids 字段：**
1. 指向该题详解/解题过程所在的实际 L1 行
2. 找不到详解输出 []
"""


# 创建全局实例
json_output_rules = JsonOutputRules()
line_id_rules = LineIdRules()
difficulty_rules = DifficultyRules()
composite_rules = CompositeRules()
answer_rules = AnswerRules()
