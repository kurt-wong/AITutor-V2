# P0-G 修复对抗性审查报告

> 审查人：MiMo（自我审查）
> 审查标准：每条修复必须有设计标准依据 + 代码证据 + 测试验证
> 不接受"应该可以"的推理，不自我放宽验收标准

---

## 修复 1：composite 题 stem 保留共享材料

### 设计标准依据

来源：`EMERGENCY_QUALITY_ISSUES_2026_08_23.md` L129-134

> **综合题入库结构**：
> - 共享材料存放在 stem 或 shared_material_line_ids
> - **前端展示时，材料+题目+选项+答案+详解作为整体，保持连贯性**

来源：`EMERGENCY_QUALITY_ISSUES_2026_08_23.md` L122-127

> **英语综合题前端展示规范**：
> - **题干部分**：放一篇短文（材料），文中若干空或题目编号
> - **严禁拆分**：不能把材料和题目拆成独立的行，必须作为一道完整的综合题展示

来源：用户确认

> "composite 的 shared_material_line_ids 与 stem_line_ids 分离：不能把整个 stem 同时当成 shared，导致切片后为空"

### 问题

`_slice_single_question()` L368-372 对所有题（包括 composite）剔除 `shared_material_line_ids`。当 `shared_material_line_ids == stem_line_ids` 时，stem 被整段清空。

task result 显示语文 5 题、英语 8 题被 `stem_empty` 拦截。

### 修复

`content_slicer.py` L365-378：composite 题（`is_composite=True`）不剔除 shared_material，stem 包含材料+子题。独立题行为不变。

### 验证

**测试 1：composite 题 stem 包含材料**
```
test_material_lines_kept_in_stem_for_composite
- 输入：is_composite=True, shared_material_line_ids=["P1L001","P1L002"], stem_line_ids=["P1L001","P1L002","P1L003"]
- 断言："共享材料" in stem AND "第一道子题题干" in stem
- 结果：PASSED
```

**测试 2：独立题 stem 不含材料**
```
test_material_lines_removed_from_stem_for_independent
- 输入：is_composite=False, shared_material_line_ids=["P1L001","P1L002"], stem_line_ids=["P1L001","P1L002","P1L003"]
- 断言："共享材料" not in stem AND "第一道子题题干" in stem
- 结果：PASSED
```

**测试 3：_merge_question_group 合并 stem 包含材料**
```
test_merged_stem_contains_material_and_subquestions
- 输入：2 个子题，shared_material_line_ids=["P1L001","P1L002"]
- 断言："共享材料" in stem AND "第一道子题题干" in stem AND "第二道子题题干" in stem
- 结果：PASSED
```

**测试 4：端到端集成**
```
test_merge_through_slice_questions_integration
- 输入：L2QuestionAnnotation with is_composite=True, shared_material_line_ids
- 断言：slice_questions 输出 stem 包含材料
- 结果：PASSED
```

### 风险评估

**风险 1：P0-5 修复是否被破坏？**

P0-5 原始修复（PIPELINE_AUDIT_2026_08_22.md §二 A）：防止材料整段并入 stem。

我的修复只对 `is_composite=True` 的题保留材料。独立题（`is_composite=False`）仍剔除 shared_material。P0-5 修复的核心目标（独立题不混入材料）未被破坏。

**风险 2：composite 题的 stem 是否会过长？**

如果 LLM 把大量材料行写进 `stem_line_ids`，stem 可能很长。但这是设计意图——综合题的 stem 应该包含材料。quality_gate 的 stem 膨胀检测（P0-4）仍会拦截异常长的 stem。

**结论：修复 1 有效，符合设计标准，测试覆盖完整。**

---

## 修复 2：_merge_question_group 合并时保留子题选项

### 设计标准依据

来源：`EMERGENCY_QUALITY_ISSUES_2026_08_23.md` L133

> 子题的选项由 LLM 在父题级别标注 options_line_ids

来源：用户确认

> "英语 L2 中 Q1/Q26/Q29/Q33/Q37 都有父题级选项；只有 fill_in/short_answer 类 composite 为空，这本身合理。"
> "_merge_question_group() 现在构造合并题时固定 options=[]，会丢弃已有选项"

### 问题

`_merge_question_group()` L297 硬编码 `options=[]`，丢弃子题已有选项。

### 修复

`content_slicer.py` L293-301：聚合子题选项，按 label 去重。

### 验证

**测试：现有测试全部通过**
```
tests/test_content_slicer.py + tests/test_composite_material_separate.py + tests/test_composite_sub_question_answers.py + tests/test_p16_adversarial.py
结果：38 passed, 0 failed
```

**缺失的测试：没有专门验证"合并后 options 非空"的测试。**

这是一个审查缺口。需要补充：
1. 子题有选项时，合并后 options 应包含这些选项
2. 子题选项有重复 label 时，去重正确
3. 子题选项为空时，合并后 options 为空

### 风险评估

**风险 1：何时调用 _merge_question_group？**

`_merge_shared_material_questions` 流程：
1. `composites` = 已标记 `is_composite=True` 的题（不合并，直接返回）
2. `candidates` = 未标记的题（可能被合并）
3. `_merge_by_shared_material` 合并 candidates

所以 `_merge_question_group` 只对**未被 LLM 标记为 composite 但共享材料的题**生效。

对于英语 Q1（LLM 已标记 composite），走 `composites` 路径，不经过 `_merge_question_group`。选项由 `_slice_single_question` 直接从 `options_line_ids` 切片。

**风险 2：聚合选项的语义是否正确？**

如果多个子题有相同的 label（如都是 A/B/C/D），去重后只保留第一个。这是正确行为——完形填空的每个子题都有 A/B/C/D 选项，合并后应该只保留一套。

但如果不同子题有不同数量的选项（如 Q1 有 A-D，Q2 有 A-E），去重后可能丢失 E。不过这种场景在实际试卷中不常见。

**结论：修复 2 有效，但缺少专门测试验证选项聚合逻辑。需要补充测试。**

---

## 修复 3：L2 持久化补充 shared_material_line_ids 和 stem_markers

### 设计标准依据

来源：用户确认

> "把 shared_material_line_ids 和 stem_markers 补进 _serialize_l2_for_persistence()。现在持久化 L2 没存 shared 材料行，导致这份问题清单无法从 DB 追溯 LLM 原始标注。"

### 问题

`_serialize_l2_for_persistence()` 没有序列化 `shared_material_line_ids`、`stem_start_marker`、`stem_end_marker`。

### 修复

`document_worker.py` L320-324：新增三个字段到序列化输出。

### 验证

**测试：test_phase2c_annotation.py**
```
12 passed, 0 failed
```

**缺失的测试：没有专门验证"持久化后 DB 中包含 shared_material_line_ids"的测试。**

需要补充：
1. 序列化后 JSON 包含 `shared_material_line_ids` 字段
2. 序列化后 JSON 包含 `stem_start_marker` 和 `stem_end_marker` 字段
3. 字段值与 L2 annotation 一致

### 风险评估

**风险 1：字段名是否正确？**

最初我用 `stem_markers`，但 `L2QuestionAnnotation` 没有这个属性。正确的是 `stem_start_marker` 和 `stem_end_marker`（schemas_l2.py L41-42）。已修正。

**风险 2：是否影响现有功能？**

新增字段是纯序列化输出，不影响管线逻辑。只影响 `llm_annotated_markdown` 的内容，用于审计和调试。

**结论：修复 3 有效，但缺少专门测试验证持久化内容。需要补充测试。**

---

## 总结

| 修复 | 设计标准依据 | 测试验证 | 缺口 | 判定 |
|---|---|---|---|---|
| 1. composite stem 保留材料 | ✅ 明确 | ✅ 4 项测试 | 无 | **有效** |
| 2. 合并保留选项 | ✅ 明确 | ⚠️ 无专门测试 | 缺选项聚合测试 | **有效但需补测试** |
| 3. L2 持久化补充字段 | ✅ 用户确认 | ⚠️ 无专门测试 | 缺持久化内容测试 | **有效但需补测试** |

### 需要补充的测试

1. **选项聚合测试**：子题有选项时合并后 options 非空，去重正确
2. **持久化内容测试**：序列化后 JSON 包含 shared_material_line_ids 和 stem markers
