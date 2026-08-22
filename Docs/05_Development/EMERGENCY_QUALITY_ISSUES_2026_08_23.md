# 管线入库质量紧急问题清单

> 日期：2026-08-23
> 来源：用户审核页面实际核对
> 状态：待逐条分析修复

---

## 通病

### T-1：科目标签关联错误
- 现象：审核页面/学生页面点击科目标签，显示的题目与科目无关（点语文出数学）
- 可能根因：
  1. 文件名 URL 编码（`2026%E5%8C%97...`）导致 subject 字段解析错误
  2. subject 字段在上传时由 API Form 参数设置，但 DB 中 filename 是乱码，前端按 filename 过滤时匹配失败
  3. 前端按 `document.subject` 过滤但 subject 字段可能为空或不一致
- 需要验证：前端查询 API 的 subject 过滤逻辑

---

## 语文试卷问题

### Y-1：Q1-Q7 材料可见，题干+选项全部丢失
- 现象：材料一二能看到，7 道选择题的题干和选项全部丢失，答案能看到，详解正确
- 可能根因：
  1. LLM 标注时 stem_line_ids 指向了材料行而非题目行
  2. content_slicer 切片时 stem 文本为空（行号不对）
  3. 综合题合并逻辑把题目合并到了材料中

### Y-2：Q8-Q13 同 Y-1
- 现象：材料完整，题干全部丢失，答案详解正常
- 与 Y-1 同一根因

### Y-3：Q17 被单独拆出 + 连带 Q18 材料
- 现象：Q17 作为独立题目，且切入了 Q18 的材料部分
- 可能根因：
  1. LLM 对 Q17/Q18 的题号边界判断错误
  2. _build_question_start_map 裸题号优先级导致边界偏移（审查 #7）
  3. P0-B stem 截断逻辑可能截断位置不对

### Y-4：Q18-Q21, Q22-Q24 同 Y-1
- 现象：材料完整，题干丢失
- 与 Y-1 同一根因

### 语文总结
- 材料识别正确，题干/选项全部丢失
- 这不是边界问题，是**题干行号根本没指向正确位置**
- 需要读 L1 原文 + L2 标注对比

---

## 英语试卷问题

### E-1：Q1-Q10 完形填空
- 现象：材料可见，答案可见，10 道题的题干全部丢失
- 可能根因：同 Y-1，stem_line_ids 指向错误

### E-2：Q11-Q20 填空
- 现象：材料 A 只在共享材料栏，B/C 在题干栏。答案选项乱套
- Q11-Q13 答案切到 Q11，Q14-Q17 切到 Q14，Q18-Q20 切到 Q18
- 可能根因：
  1. 答案匹配逻辑把多题答案合并到一道题（answer_matcher 的答案表解析问题）
  2. 综合题子题答案分配错误

### E-3：Q21-Q25 用词语完成句子
- 现象：题干材料全部丢失，答案完整
- 同 Y-1

### E-4：Q26-Q36 阅读理解
- 现象：三篇材料 10 道选择题全部混乱
- 题干选项答案匹配混乱

### E-5：Q37-Q41 七选五
- 现象：选项全部放到子题里，题干缺失
- 可能根因：七选五题型归一化为 single_choice，但实际结构是"一篇材料 + 5 个填空位置 + 7 个选项"

---

## 根因假设

### 假设 1：LLM 标注输出的 stem_line_ids 大面积指向错误行
- 证据：材料可见但题干丢失，说明材料行号正确但题目行号不对
- 验证方法：读 L2 标注 JSON，对比 stem_line_ids 与 L1 原文

### 假设 2：content_slicer 的 stem 切片逻辑有系统性缺陷
- 证据：即使 LLM 标注正确，slicer 可能切出空文本
- 验证方法：读 SlicedQuestion 的 stem 字段

### 假设 3：综合题合并吞掉了独立题目
- 证据：语文 Q1-Q7 共享材料，7 道题可能被合并为 1 道综合题
- 验证方法：检查 questions 表中语文文档的 is_composite 和 sub_questions

---

## 实测数据分析（2026-08-23）

### 语文试卷（2026北京朝阳高一（上）期末语文（教师版）.pdf）

**OCR 原文**：415 行，结构清晰（材料一 L007-L013，材料二 L014-L019，题目 L020+）

**L2 标注**：仅 8 题（应有 24 题）

| L2 题号 | type | composite | stem_ids | options | sub_questions | 问题 |
|---|---|---|---|---|---|---|
| Q1 | single_choice | True | 13 | 0 | 7 | 选项行号为空！|
| Q8 | classical_reading | True | 4 | 0 | 6 | |
| Q14 | poetry_reading | True | 5 | 0 | 3 | |
| Q17 | short_answer | False | 19 | 0 | 0 | |
| Q18 | prose_reading | True | 8 | 0 | 4 | |
| Q22 | language_basics | True | 2 | 0 | **130** | 子题数爆炸！|
| Q23 | short_answer | False | 8 | 0 | 4 | |
| Q24 | short_answer | False | 0 | 0 | 0 | stem_ids 为空 |

**入库结果**：仅 3 题（Q17, Q22, Q23）

| 入库题号 | stem_len | options | answer | composite | sub_questions | 问题 |
|---|---|---|---|---|---|---|
| Q17 | 1840 | 4 | ①.何时可掇②.别时茫茫... | False | 4 | stem 过长，含材料 |
| Q22 | 15 | 4 | （1）B（2）B | True | **130** | 子题数爆炸！|
| Q23 | 391 | 4 | 例文：安全过春节倡议书... | False | 4 | |

**根因分析**：
1. LLM 标注 Q1 为 composite（7 子题），但 options_line_ids=0 → 选项丢失
2. Q22 子题数 130 明显错误——可能是 LLM 把每行都标为子题
3. Q1-Q7（7 道选择题）被合并为 Q1 的 7 个子题，但子题的选项没有被提取
4. Q8-Q13, Q14-Q16, Q18-Q21, Q22-Q24 的题干在 L2 中没有独立的 stem_line_ids

---

### 英语试卷（2026北京东城高一（上）期末英语（教师版）.pdf）

**OCR 原文**：298 行

**L2 标注**：仅 11 题（应有 46+ 题）

| L2 题号 | type | composite | stem | options | sub_questions | 问题 |
|---|---|---|---|---|---|---|
| Q1 | single_choice | True | 6 | 4 | 10 | 完形填空，正确 |
| Q11 | fill_in | True | 13 | 0 | 3 | |
| Q14 | fill_in | True | 10 | 0 | 4 | |
| Q18 | fill_in | True | 7 | 0 | 3 | |
| Q21 | fill_in | True | 1 | 0 | 5 | stem_ids=1（仅标题行）|
| Q26 | single_choice | True | 26 | 4 | 3 | |
| Q29 | single_choice | True | 5 | 4 | 4 | |
| Q33 | single_choice | True | 11 | 4 | 4 | |
| Q37 | single_choice | True | 6 | 7 | 5 | 七选五，7 选项 |
| Q42 | short_answer | True | 7 | 0 | 4 | |
| Q46 | short_answer | False | 0 | 0 | 0 | stem_ids 为空 |

**入库结果**：仅 3 题（Q11, Q14, Q18）

| 入库题号 | stem_len | options | answer | sub_questions | 问题 |
|---|---|---|---|---|---|
| Q11 | 1221 | 4 | itself | **186** | 子题数爆炸！|
| Q14 | 755 | 4 | when | **257** | 子题数爆炸！|
| Q18 | 104 | 4 | was awarded | **191** | 子题数爆炸！|

**根因分析**：
1. Q1（完形填空 10 子题）标注正确但未入库——可能被 quality_gate 拒绝
2. Q11/Q14/Q18 子题数 186/257/191 明显错误——L2 标注的 sub_questions 字段被错误填充
3. Q21-Q25（用词语完成句子）stem_ids=1，只有标题行
4. Q26-Q36（阅读理解）标注了但未入库
5. Q37-Q41（七选五）标注了但未入库

---

## 根因总结（基于实测数据）

### 核心问题 1：LLM 标注质量极差

L2 标注只有 8-11 题（语文应 24 题，英语应 46+ 题），说明 **LLM 漏标了大量题目**。

对于标注的题目：
- composite=True 但 options_line_ids=0（语文 Q1-Q7）
- stem_line_ids 指向材料行而非题目行
- sub_questions 数量爆炸（130/186/257/191）

### 核心问题 2：综合题子题处理崩溃

sub_questions 数量 130-257 是明显错误。可能原因：
1. LLM 把材料的每一行都标为一个子题
2. content_slicer 的 `_merge_question_group` 逻辑有 bug，把不相关的行合并为子题
3. L2 标注的 sub_questions 字段本身就被错误填充

### 核心问题 3：入库过滤过于激进

L2 标注 8-11 题，入库仅 3 题。5-8 题被 quality_gate 或 ingestion 拒绝。可能原因：
1. 选项缺失 → quality_gate 扣分 → confidence < 0.8
2. stem 为空 → ingestion 跳过
3. 答案缺失 → reviewing 状态但不入库

### 核心问题 4：科目标签关联错误（T-1）

文件名 URL 编码导致 `documents.filename` 存储的是 `%E5%8C%97...`。前端按 subject 过滤时，如果依赖 filename 解析，会匹配失败。

---

## 修复优先级（紧急）

| 优先级 | 问题 | 修复方向 |
|---|---|---|
| **P0-G** | LLM 漏标大量题目（8-11/24-46） | 两阶段 prompt，第一阶段只标核心锚点 |
| **P0-H** | sub_questions 数量爆炸（130-257） | 检查 L2 标注解析和 content_slicer 合并逻辑 |
| **P0-I** | composite 题 options_line_ids=0 | prompt 要求 composite 子题也标选项行号 |
| **P1-E** | 文件名 URL 编码 | 上传脚本修复（P2-C 升级为 P1） |
| **P1-F** | 管线效率（LLM 300-450s + 4/5 重试） | 两阶段 prompt + 减少重试 |

### 第一阶段：核心入库字段
- question_number, question_type, section_id, is_composite
- shared_material_line_ids, stem_line_ids, stem_markers
- options_line_ids, answer_line_ids, explanation_line_ids

### 第二阶段：异步富化
- difficulty, score, knowledge_points, structure_signature

### 优势
- prompt 从 5900 字降到核心字段，LLM 出错面变小
- difficulty 不再第一轮强制默认 3
- knowledge_points/structure_signature 失败不阻断入库

### 注意事项
1. 持久化原始 L1 和第一轮标注
2. 富化任务幂等，不覆盖人工修改
3. 统计 API 加"富化覆盖率"指标
4. 复用 worker/task 模式，不阻塞入库 worker
5. answer_line_ids/explanation_line_ids 可拆到 answer_extractor.py
