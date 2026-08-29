# AI Tutor 题库展示与切片契约

Version: 0.4
Status: 当前固化基线；后续问题按 LOG 更新
Date: 2026-08-29
用途：根据用户提供的英语、理科、语文展示期望，定义入库题目在 golden、API 与前端展示中应保留的结构。

## 0. 已确认决策

1. 展示标记统一为“题干区/答案区/详解区/配图锚点”。
2. 标记只作为 golden 校验和切片入库元数据，不进入前端页面渲染。
3. 英语和语文试卷默认按“综合题 + 子题”建模；没有共享材料/情境的题才建模为独立题。
4. 写作参考范文放 `answer`。
5. 理科化学式统一使用标准化显示：`Cl₂`、`OH⁻`、`Fe₃O₄`；OCR 原文中的 `Cl(2)` 只作为 provenance。
6. 配图锚点统一为“配图锚点”；`配图起始点`、`配图位置锚点`、`配图锚点指示` 作为兼容输入，归一化后保存为 `配图锚点`。
7. golden 不约束题量、组数、子题数；只作为题型种类与展示结构样例，不作为数量验收标准。
8. golden 答案比较必须忽略全半角、引号样式、题号前缀、常见分隔符和 OCR 转义噪音；格式差异不视为内容不匹配。

## 1. 核心原则

1. 题目内容按“题干区、答案区、详解区、配图区”结构化保存，不依赖原始文本中的“开始/结束”标记做最终渲染。
2. 同一篇文章/词库/情境材料只保存一次，作为 `shared_material`，各子题引用它。
3. 每道题的答案必须独立、干净，不得把多个题答案拼在一个字符串里。
4. 配图和答案图必须保留来源、页码、位置和锚点。
5. 综合题的子题必须有完整独立的 stem/options/answer/explanation 数据，父题不拼接子题选项。
6. 评分标准与答案分开保存，例如“任选其中三道小题作答”“每空1分”“言之成理即可”。

## 2. 统一展示标记

| 语义 | 标准标记 | 兼容输入 |
|---|---|---|
| 题干区开始 | `题干区开始` | `题干开始` |
| 题干区结束 | `题干区结束` | `题干结束` |
| 答案区开始 | `答案区开始` | `答案开始` |
| 答案区结束 | `答案区结束` | `答案结束` |
| 详解区开始 | `详解区开始` | `详解开始` |
| 详解区结束 | `详解区结束` | `详解结束` |
| 配图锚点 | `配图锚点` | `配图起始点` / `配图位置锚点` / `配图锚点指示` |

这些标记不写入前端展示文本，只用于 golden 校验、切片边界识别和人工核对。

## 3. 通用题目结构

```json
{
  "question_number": "1",
  "question_type": "single_choice",
  "section_id": "单项选择题_1",
  "stem": "题干文本",
  "stem_line_ids": ["P1L005"],
  "stem_region": {"start": "题干区开始", "end": "题干区结束"},
  "shared_material": null,
  "shared_material_line_ids": [],
  "options": [
    {"label": "A", "text": "选项文本"}
  ],
  "options_line_ids": {"A": ["P1L006"]},
  "answer": "D",
  "answer_line_ids": ["P5L003"],
  "answer_region": {"start": "答案区开始", "end": "答案区结束"},
  "explanation": "详解文本",
  "explanation_line_ids": ["P12L022"],
  "explanation_region": {"start": "详解区开始", "end": "详解区结束"},
  "scoring_standard": "每空1分，任选3小题完成",
  "images": [
    {
      "image_key": "object_key",
      "page_no": 3,
      "bbox": {"x1": 0, "y1": 0, "x2": 100, "y2": 100},
      "placement": "stem",
      "source": "ppsv3",
      "anchor": "配图锚点",
      "url": "https://..."
    }
  ],
  "answer_images": [],
  "is_composite": false,
  "sub_questions": [],

  "shared_material_notes": null,
  "shared_material_notes_line_ids": [],
  "word_bank": null,
  "answer_structure": null,
  "answer_source": "document_answer_table",
  "explanation_source": "document_inline_explanation",
  "score": 5,
  "difficulty": 1
}
```

## 4. 各题型要求

### 4.1 单项选择题

- `stem` 必须完整。
- `options` 必须 A-D 等完整列表。
- `answer` 只保存单题答案，例如 `D`。
- 禁止保存 `"A43.B44.D"`、`"D2.C3.A4"` 这类跨题答案串。
- 分值不要混入答案，例如 `"B (2分)"` 应拆为 `answer="B"` + `score=2`。

### 4.2 多项选择题

- `question_type` 使用 `multiple_choice` 或对应题型树 code。
- `answer` 建议保存为数组或紧邻字母，例如 `["A", "B", "D"]` 或 `"ABD"`。
- 每个选项仍保留独立的 `options_line_ids`。

### 4.3 完形填空

- 整篇文章作为 `shared_material`。
- 10 个空位建模为同一综合题的 `sub_questions`。
- 子题 `stem` 可只保留题号/空位信息，选项和答案归属子题。
- 父题 `options` 置空，禁止把 10 个题的选项拼接在父题上。

### 4.4 语法填空

- 每篇短文作为一个共享材料组。
- 同一篇下的空位是 `sub_questions`，例如 `11-13`、`14-17`、`18-20` 各一组。
- 子题 `answer` 必须是该空位的独立答案，例如 `itself`、`to`、`to stay`。
- 提示词原文可作为子题 stem 的补充信息。

### 4.5 选词填空 / 词库

- 方框单词保存为 `word_bank`。
- 每个句子作为独立子题或独立题目。
- `word_bank` 示例：

```json
{
  "title": "请用方框中单词的正确形式完成句子。",
  "words": ["pack", "confuse", "equal", "contribute", "athlete"],
  "line_ids": ["P3L001", "P3L002", "P3L003", "P3L004", "P3L005"]
}
```

### 4.6 阅读理解

- 整篇文章作为 `shared_material`。
- 每道小题是独立 `single_choice` 或对应题型。
- 每道小题保留自己的 `stem_line_ids`、`options_line_ids`、`answer_line_ids`。
- 禁止把同一篇文章的所有答案拼进某一题的 answer。

### 4.7 七选五

- 整篇文章作为 `shared_material`。
- A-G 七个选项作为共享选项区，或按子题引用。
- 每个空位是 `sub_questions` 中的一个子题。
- 子题 answer 只保存对应选项字母，例如 `B`。
- 需要保留“选项中有两项多余”的元数据：`extra_options=2`。

### 4.8 阅读表达

- 整篇文章作为 `shared_material`。
- 42-45 等小题保存为 `sub_questions` 或独立 `short_answer`。
- 题干中的作答横线可保留为 stem 的一部分。
- 答案必须保存参考作答，不是空字符串。

### 4.9 写作

- 题目要求作为 `stem`。
- 示例作文作为 `answer` 完整保存，禁止只存 `"例文"`。
- `answer_region` 应包含完整参考范文。
- 若题目提供多个写作选项，父题保存共同要求，每个写作选项作为独立子题。

### 4.10 理科综合题 / 实验题

- `(1)(2)(3)(4)` 子问建模为 `sub_questions`。
- 每个子问保留独立 `stem`、`answer`、`explanation`。
- 题干/子问中的图片绑定到对应 `images`。
- 答案区中的图片保存到 `answer_images`。
- 如果答案是“见试题解答内容”，该文本可保留，但要同时有 `answer_source` 和完整 `explanation`。

### 4.11 语文题型

语文试卷按“综合题 + 子题”为主建模。

#### 4.11.1 语文基础知识选择

- 没有共享材料或共享材料很短的题可以建模为独立 `single_choice` / `multiple_choice`。
- 例如成语解说、加点词意思、语句理解等，直接保存题干、选项、答案、详解。

#### 4.11.2 默写题

- 题目说明保存为父题 `stem`，例如“任选其中三道小题作答”。
- 每个空位是 `sub_questions` 的子题。
- 每个子题保存独立 `answer`。
- 评分标准保存到 `scoring_standard`，例如“每空1分，任选3小题完成，若全选按前3小题计分”。

#### 4.11.3 现代文阅读 / 名著阅读

- 整篇选段作为 `shared_material`。
- 选择题、标点题、简答题均作为独立子题或题目。
- 表格题使用 `answer_structure` 保存表格行/列结构。
- 多选/不定项保存独立 `answer`，例如 `["B", "C"]` 或 `"BC"`。

#### 4.11.4 文言文阅读

- 文言原文和注释整体保存为 `shared_material`。
- 文言注释可保存为 `shared_material_notes`。
- 选择题、分析题、表格题、综合问答均作为 `sub_questions`。
- 表格类答案使用 `answer_structure`。

#### 4.11.5 综合研学任务 / 任务式大题

- 父题保存总说明和任务要求。
- `task 1 / task 2 / task 3` 分别建模为 `sub_questions`。
- 示例答案保存为对应子题 `answer`，可包含路线、阐释、导游词等结构化文本。

#### 4.11.6 语文写作

- 父题保存写作总要求。
- 小写作中“任务一/任务二/任务三”这类必做任务建模为 `sub_questions`，每个任务保存独立 `answer`。
- 大写作直接按一道题建模，不拆 `choices`。
- 若题目给出多个写作选项，把所有条件和要求统一保存到该题 `stem`。
- 示例作文完整保存到 `answer`；如果有多篇示例，可保留多篇并在 `answer` 内分段区分。
- 字数要求、文体要求等保存到 `scoring_standard` 或 `stem`。

### 4.12 语文表格 `answer_structure` 示例

`answer_structure` 用于表达无法用纯文本展示的表格答案，例如标点题表格、人物形象表格。

标点题示例：

```json
{
  "type": "table",
  "title": "标点符号及理由",
  "columns": [
    {"key": "position", "title": "标点符号"},
    {"key": "reason", "title": "理由"}
  ],
  "rows": [
    {
      "position": "①",
      "answer": "！",
      "reason": "四叔对祥林嫂死在祝福之夜非常愤慨，语气强烈。"
    },
    {
      "position": "②",
      "answer": "？",
      "reason": "“我”突闻祥林嫂死讯，感到惊诧，不敢相信。"
    },
    {
      "position": "③",
      "answer": "？",
      "reason": "短工对祥林嫂的死因毫不感到意外，使用反问语气。"
    }
  ]
}
```

人物形象表格示例：

```json
{
  "type": "table",
  "title": "人物形象特点",
  "columns": [
    {"key": "character", "title": "人物"},
    {"key": "detail", "title": "细节描写"},
    {"key": "trait", "title": "形象特点"}
  ],
  "rows": [
    {
      "character": "店主人",
      "detail": "成目视主人，主人色不动……请主人自取之，主人不受",
      "trait": "镇定自若；精明；善良；不贪财"
    },
    {
      "character": "大亲王",
      "detail": "王呼曰“鹑人来，鹑人来！实给六百，肯则售，否则已耳。”",
      "trait": "沉迷玩物；精明"
    },
    {
      "character": "老祖母",
      "detail": "妪早起，使成督耕，妇督织；稍惰，辄诃之。",
      "trait": "勤快；严教儿孙；治家有方"
    }
  ]
}
```

表格类答案仍可保留 `answer` 为便于检索的汇总文本，但展示必须优先读取 `answer_structure`。

## 5. golden 校验规则

golden 必须包含上述展示结构，不能只有 `expected_content` 和 `expected_anchor`。

必查项：

- 每题 `answer` 干净独立，无跨题答案串。
- 综合题有 `is_composite=true` 且有非空 `sub_questions`。
- 共享材料只保存在 `shared_material`，子题不重复复制整篇文章。
- 文言注释单独保存为 `shared_material_notes`，不混入题干。
- 配图有 `page/bbox/placement/source/anchor`。
- 答案图有 `answer_images`。
- 写作答案完整，不能是 `"例文"`。
- 大写作直接按一道题建模，不拆 `choices`，也不当作必做 `sub_questions`。
- 理科公式标准化后仍保留 OCR 原文 provenance。
- 七选五保留 A-G 和 extra_options。
- 词库题保留 `word_bank`。
- 默写、表格题、任务题保留 `scoring_standard` 和 `answer_structure`。

## 6. 已确认/建议结论

1. 有整篇选段的语文阅读统一建模为综合题。
2. 评分标准放 `scoring_standard`。
3. 表格题 `answer_structure` 示例见 §4.12。
4. 小写作必做任务建模为 `sub_questions`；大写作直接按一道题建模，不引入 `choices`。
5. 文言注释单独保存为 `shared_material_notes`。
