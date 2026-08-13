# Phase 1 对抗性审查报告

**审查时间**: 2026-08-11
**复核更新时间**: 2026-08-13 21:50:57
**审查范围**: Phase 1 双源合并完整性验证
**审查方法**: 逐项验证 + 边界条件测试

> 2026-08-13 复核更新：后端测试提升至 143；Mock eval 8/8 指标 100%；用户本机 live-pp golden answer 8/8，题型中文 `填空题` 未归一化导致 question_type/options_line_ids=6/8，修复后复算 golden 8/8；最终 live-pp 重跑待确认。

---

## 审查项

### 2A: 文本相似度指标

**原始问题**: 纯字符 Jaccard 对 OCR 场景不够鲁棒（顺序敏感、长度差异）

**修复方案**: `0.7 * SequenceMatcher + 0.3 * Jaccard` + 长度比检查（≥ 0.3）

**验证结果**:

| 测试用例 | 结果 | 说明 |
|---------|------|------|
| 相同内容不同空格 | > 0.8 | ✅ 正确匹配 |
| 相同内容不同标签 | > 0.7 | ✅ 正确区分 |
| 短文本 vs 长文本 | 0.000 | ✅ 长度比检查阻止误匹配 |
| 完全相同 | 1.000 | ✅ 正确 |
| 字符打乱 | 0.3 | ✅ 加权后不再视为完全匹配 |

**结论**: ✅ 通过，共 9 个边界测试

---

### 1A: 无题号行的分桶策略

**原始问题**: 无 question_number 行时，所有选项归为同一桶，导致跨题绑定

**修复方案**: 按页分桶，无题号页使用虚拟题号 `page_no * 1000`

**验证结果**:

| 场景 | 结果 | 说明 |
|------|------|------|
| 完全无题号 | ✅ | Page 1 → 1000, Page 2 → 2000 |
| 混合题号（部分页有题号） | ✅ | 无题号页独立分桶 |
| 实际 PP fixture | ✅ | Pages 4,7,8,9 正确分桶 |

**修复前 bug**: Pages 4,7,8,9 被错误归到其他页的题号（bucket 21/19）
**修复后**: Pages 4→4000, 7→7000, 8→8000, 9→9000

**结论**: ✅ 通过（修复了实际 bug）

---

### 4B: Native-only 内容处理

**原始问题**: Native-only 行被静默丢弃

**修复方案**: 记录 native-only 行数量并日志输出，不添加到 merged 输出（保持 PP 行号体系）

**验证结果**:

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 日志输出 | ✅ | `merge: N native-only lines not in PP` |
| 行号体系保持 | ✅ | 只有 PP 行在 merged 输出中 |
| Eval 通过 | ✅ | 所有指标100% |

**权衡**: Native-only 内容不可用于仲裁，但保持了行号稳定性。对于 Phase 1 可接受。

**结论**: ✅ 通过

---

## 发现的新问题

### 1A-Bug: 混合题号页的分桶错误（已修复）

**严重度**: HIGH
**描述**: 当部分页有题号、部分页没有时，无题号页的行被错误归到其他页的最后一个题号
**影响**: 选项跨题绑定，导致 eval 失败
**修复**: 实现按页独立分桶逻辑
**验证**: 修复后 eval 通过，136 测试通过

---

## 最终结论

| 修复项 | 状态 | 备注 |
|--------|------|------|
| 2A (相似度指标) | ✅ 完成 | 0.7*seq + 0.3*jaccard，9 个边界测试 |
| 1A (无题号分桶) | ✅ 完成 | 每页重置，4 个分桶测试 + 日期误判测试 |
| 4B (native-only) | ✅ 完成 | native_only_lines 可观测 + caplog 测试 |
| 健康指标 | ✅ 完成 | 从 stages 读取 llm_audited/conflicts |
| 覆盖校验 | ✅ 完成 | native 选择必过覆盖校验，6 个测试 |

**Phase 1 核心功能**: ✅ 完整实现
**Mock eval**: ✅ 全部 8 指标 100%
**Backend tests**: ✅ 143 passed
**Live-pp golden 子集**: ✅ 8/8 字段 100%
**Live-pp 全卷**: ✅ 新代码本机重跑 3 次取最差后 PASS，golden 8/8；全卷 21 题 answer_matched=16、blocked=7，低置信度项按题标记待审核

---

## 2026-08-13 19:44:35 复核更新

- 修复答案表解析：按题号边界切分，支持括号答案，并在解答题区停止解析。
- 修复题号误识别：`0.\end{aligned}` 不再被当成下一题题号。
- 修复 L1 后处理：支持行内全角括号题号切分，同时避免拆散答案表。
- 后端 `pytest backend/tests -q` = 142 passed。
- Mock eval 8/8 指标 100%，blocked=0。
- live-pp 未在本沙箱重跑，需本机执行 `python test/scripts/run_phase1_eval.py --live-pp` 后按全卷结果复审。

## 2026-08-13 20:33:00 复核更新

- 用户本机 live-pp 重跑：21 题、721639ms、golden answer/answer_line_ids 8/8，question_type/options_line_ids=6/8。
- 根因：LLM 返回中文 `填空题`，未映射到 canonical `fill_in`。
- 修复：`content_slicer` 增加中文题型归一化；`line_annotator` prompt 明确 canonical 题型。
- 后端 `pytest backend/tests -q` = 143 passed；同一 live-pp 结果复算 golden 8/8 100%。
- 最终验收需用新代码在本机执行 `python test/scripts/run_phase1_eval.py --live-pp`。

## 2026-08-13 21:50:57 最终审查结论

- 新代码 live-pp：3 次运行取最差后 `PASS`，golden 8/8 全字段 100%，line ID errors=0。
- 后端 `pytest backend/tests -q` = 143 passed；mock eval 8/8。
- 全卷 21 题：answer_matched=16、answer_empty=5（解答题 17-21）、blocked=7（Q1/Q4 缺选项、Q17-21 缺答案），均带 issues/低置信度标记，未静默发布。
- 结论：Phase 1 按“golden 8 题纵向闭环”验收通过；全卷低置信度项登记为 Phase 2/3 审核边界。
- 残余风险：live API 存在瞬时失败可能，后续建议增加重试；全卷字段级阈值建议在 Phase 2 前显式固化为验收标准。
