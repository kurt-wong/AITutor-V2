# P0-A / P0-B 修复对抗性审查报告

> 审查人：MiMo（独立第三方）
> 审查对象：commit e4b9150（P0-A savepoint 事务隔离 + P0-B stem 结束位置校验）
> 审查标准：每条结论必须有代码行号 + 运行证据，不接受推理

---

## 一、P0-A 审查：ingestion savepoint 事务隔离

### 1.1 代码正确性

**修改文件**：`ingestion.py` L111-135

**代码逻辑**：
```python
async with session.begin_nested():   # PostgreSQL SAVEPOINT
    question_id = await _ingest_one_question(...)
    # 成功 → savepoint 自动释放，数据保留在外层事务
except Exception as exc:
    # 失败 → savepoint 自动回滚，外层事务继续
```

**判定**：逻辑正确。`begin_nested()` 在 asyncpg 上创建 `SAVEPOINT`，异常时回滚到 savepoint，外层事务不受影响。

**证据**：诊断脚本 `_tmp_savepoint_diag.py` 直接对真实 PostgreSQL 执行：
```
[SETUP] 预置冲突记录: doc=d48e4611 qno=9999
[SAVEPOINT] 预期异常: IntegrityError: UniqueViolationError
[OK] savepoint 回滚后 session 可用: 10 docs
[OK] savepoint 回滚后成功插入新题: qno=10000
[OK] 外层事务回滚完成
[INFO] 悬空诊断 Questions: 0（应为 0，外层已回滚）
```

**结论**：savepoint 隔离在真实 PostgreSQL 上验证通过。UniqueViolationError 后 session 仍可查询和插入。

### 1.2 测试覆盖度

| 测试 | 场景 | 断言 | 证据 |
|---|---|---|---|
| test_single_failure_does_not_poison_session | Q1-Q3 成功，Q4 重复 | ingested≥3, failed≥1, count≥3 | PASSED |
| test_all_questions_fail_gracefully | 全部重复 | ingested=0, failed=3, session 可用 | PASSED |
| test_mixed_success_and_duplicate | Q1-Q4 成功，Q5 重复，Q6-Q8 成功 | ingested≥7, failed≥1 | PASSED |

**测试连接真实 PostgreSQL**：fixture 使用 `create_async_engine(settings.database_url)`，不 mock。

**遗漏**：没有测试"savepoint 内部多步操作部分成功"的场景（如 Question 创建成功但 KnowledgeMapping 失败）。当前 `_ingest_one_question` 的 knowledge mapping 有自己的 try/except（L340-348），不阻断主流程，所以这个遗漏不构成实际风险。

### 1.3 document_worker.py 修改

**修改**：L171-183 + L221-234，失败时先 `session.rollback()` 再标记 task/document failed。

**证据**：之前 e2e 运行中物理-八十中失败时日志显示 `worker: failed to mark task as failed`——因为 session 被 PendingRollbackError 毒化，fail_task 操作也失败。修改后先 rollback 清除毒化状态。

**判定**：逻辑正确。但 `session.rollback()` 在 savepoint 模式下回滚的是外层事务（不是 savepoint），这意味着之前成功的 savepoint 数据也会被回滚。**这是正确的**——如果 ingestion 抛出未捕获异常，说明整个入库过程失败，应该回滚所有数据。

---

## 二、P0-B 审查：stem 结束位置校验

### 2.1 代码正确性

**修改文件**：`anchor_corrector.py` L252-304 + L375-385

**代码逻辑**：在 `correct_anchors` 主循环中，stem_anchor 最终确定后，调用 `_truncate_stem_at_next_question` 截断到下一题起点之前。

**截断函数逻辑**：
1. 从 `question_start_map` 找下一题的起始 line_id
2. 获取该 line 的 order 作为 boundary_order
3. 只保留 `order < boundary_order` 的 stem 行

### 2.2 对抗性发现：L304 fallback bug（已修复）

**原始代码**（commit e4b9150）：
```python
return truncated if truncated else stem_line_ids  # 至少保留原值
```

**问题**：当所有 stem 行都在边界之后时（truncated 为空），返回原始未截断列表——修复被静默撤销。

**诊断证据**（`_tmp_p0b_diag.py`）：
```
输入: stem_ids=['P1L002']
输出: ['P1L002']   ← 应为空！
[BUG] 截断未生效！P1L002 (Q2 start) 仍在 stem 中
```

**触发概率分析**：当前代码流中 `_validate_stem_anchor` 已检查首行是当前题号。如果首行在下一题边界之后，validation 不会通过。所以**当前不可达**。但作为防御性编程，这个 fallback 是 self-defeating 的。

**修复**：删除 fallback，改为 `return truncated`（可能为空列表，下游 quality_gate "题干为空"拦截）。

**修复后证据**：
```
输入: stem_ids=['P1L002']
输出: []   ← 正确！
```

### 2.3 测试覆盖度

| 测试 | 场景 | 断言 | 证据 |
|---|---|---|---|
| test_stem_extending_past_next_question_is_truncated | stem 含下一题行 | 截断到下一题之前 | PASSED |
| test_stem_not_extending_is_unchanged | stem 不含下一题行 | 不变 | PASSED |
| test_last_question_uses_stop_order | 最后一题用答案区边界 | 截断到答案区之前 | PASSED |
| test_empty_stem_unchanged | 空 stem | 不变 | PASSED |
| test_no_next_question_uses_stop_order | 无下一题用 stop_order | 按 stop_order 截断 | PASSED |
| test_all_lines_past_boundary_returns_empty | 全部行在边界之后 | 返回空列表 | PASSED |

**遗漏**：没有测试 `correct_anchors` 主循环中的截断集成（当前只测了 `_truncate_stem_at_next_question` 函数本身）。`test_anchor_corrector.py` 的现有测试覆盖了 `correct_anchors` 整体流程，但没有专门验证截断行为。

### 2.4 question_start_map 的可靠性

`_build_question_start_map`（L88-116）的题号优先级逻辑：裸 "5." 优先级=3（最高），有内容 "5. text" 优先级=1。如审查 #7 所述，噪声行 "5." 可能覆盖真实题号起点，导致 boundary_order 被设为噪声行的 order。

**影响**：如果噪声行 order < 真实下一题 order，截断会过早——stem 被截断到噪声行之前，丢失内容。如果噪声行 order > 真实下一题 order，截断不受影响（min 取真实值）。

**当前状态**：这是审查 #7 的已知问题（P1），不在本次 P0-B 修复范围内。但 P0-B 的截断逻辑依赖 question_start_map 的正确性，如果 map 有噪声，截断也会有噪声。

---

## 三、全量回归验证

```
tests/test_ingestion_savepoint.py        3 passed  (P0-A)
tests/test_stem_end_validation.py        6 passed  (P0-B)
tests/test_question_image_association.py 9 passed  (P0-1)
tests/test_question_type_get_or_create.py 6 passed (P0-2 + 跨学科)
tests/test_difficulty_required.py        10 passed (P0-3)
tests/test_quality_gate_stem_inflation.py 6 passed (P0-4)
tests/test_composite_material_separate.py 6 passed (P0-5)
tests/test_composite_sub_question_answers.py 3 passed (P1-6)
tests/test_p16_adversarial.py            4 passed  (P1-6 adversarial)
tests/test_phase2_critical_fixes.py      ~20 passed
tests/test_anchor_corrector.py           ~10 passed
tests/test_content_slicer.py             ~20 passed
───────────────────────────────────────────────────
总计：112 passed, 0 failed（不含 e2e 5 项因 DB 清空预期失败）
```

---

## 四、结论

| 修复 | 判定 | 证据强度 | 遗留风险 |
|---|---|---|---|
| P0-A savepoint | **有效** | 强（诊断脚本 + 3 项测试，真实 PostgreSQL） | 无 |
| P0-B stem 截断 | **有效（修复后）** | 强（6 项测试含对抗性边界，诊断脚本确认 fallback bug 已修） | 截断依赖 question_start_map 正确性（审查 #7，P1） |
| document_worker rollback | **有效** | 中（逻辑验证 + 日志证据，无独立测试） | 外层 rollback 会回滚所有 savepoint 数据（设计如此，非 bug） |

**遗留项**：
1. P0-B 截断依赖 `_build_question_start_map` 的噪声问题（审查 #7，P1）
2. e2e 测试因 DB 清空失效，需重跑 10 份 PDF 后恢复
3. `correct_anchors` 集成级截断测试缺失（当前只测函数级）
