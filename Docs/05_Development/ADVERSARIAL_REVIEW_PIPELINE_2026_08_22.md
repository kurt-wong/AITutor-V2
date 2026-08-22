# 文档解析管线对抗性审查 — 独立第三方意见

> 依据：Claude 深度审计（8 条问题）+ Codex 复核（逐条核实）+ 本人对源码的独立验证
> + **刚刚完成的真实 e2e 全量运行（10 份 PDF，9 成功 / 1 整份失败）**
> 日期：2026-08-22

---

## 〇、总体判断

**三方结论一致的部分是对的**：管线是真实实现，LLM 行号精度是系统性天花板，锚点校正确实只校首行不校尾行。

**但 Claude 审计与 Codex 复核都漏掉了当前最致命的问题** —— 我们刚在真实 e2e 运行中实测暴露的 **重复题号 → 整份文档入库级联失败**。这是唯一直接阻断"真实文件全量入库流程"的 bug，优先级高于双方列出的所有 P0。

同时，Claude 有多处**夸大或事实错误**（难度分布、合并触发条件、禁止自动发布语义），Codex 的纠偏基本正确但**没有上升到根因**。

---

## 一、逐条核实：对 Claude 8 条问题的独立判定

| # | Claude 主张 | 判定 | 我的独立证据/补充 |
|---|---|---|---|
| 1 | Prompt 过度复杂（2500字/28条规则） | **属实，量化错误** | Codex 实测 5899字/157行/16条是对的。但"复杂度是病"值得反驳：16 条规则配 3 个示例，对需要 15+ 字段的单次标注不算失控。**真病是单次 pass 读噪声 OCR 文本**，拆两阶段是经验假设不是证明。**难度兜底=3 的结论被 e2e 数据推翻**：真实库 level2=72、level3=46（71.5% 集中在 2-3 级，但非"大部分=3"）。Claude 说"统计分析价值为零"是夸大 |
| 2 | 锚点校正不校验 stem 结束位置 | **属实（真正的 P0）** | `_validate_stem_anchor`（anchor_corrector.py L119-192）只查：行号有效、首行在答案区前、首行是当前题号。**无任何结束边界检查**。补充：semantic_anchor.resolve_stem_range（L296-318）在 LLM 给了 marker 时会算"下一题起点"边界——所以风险集中在 **LLM 无 marker 的路径**（resolve 返回 None → 退回裸 LLM 行号 + 仅首行校验）。修复成本低：correct_anchors 里用已有的 `_build_question_start_map` 把 stem 行号上限截到下一题起点 |
| 3 | cloze/reading/seven_to_five 映射 single_choice 是架构级错误 | **属实（代码事实），但"架构级"夸大，修复方向我不同意** | Codex 说"是设计决策、测试主动断言"——对。第一性原理：canonical 化的**目的**是 quality_gate 选项数检查 + 统计。完形填空每空确实有 4 个选项，单选检查**不失效**；阅读理解 MCQ 每题也有 4 选项。真正的损失是**统计无法区分完形/单选/阅读**。Claude 建议"保留原始题型"会直接破坏 quality_gate 选项检查（需要连带改造），**不是低成本 P0**。低风险方案：保留映射，给 SlicedQuestion 加 `raw_type` 字段透传原始题型供统计/搜索用 |
| 4 | ≥1 行重叠就合并，OCR 噪声会误合并 | **触发条件部分错误，风险转移** | **`_merge_by_shared_material`（content_slicer.py L139-195）只合并带 `shared_material_line_ids` 的题目（L156）**，这些行号来自 LLM 标注。"两道独立题恰在同一行有文本重叠就被合并"**不成立**——必须先有 LLM 显式标记共享材料。风险从"OCR 噪声误触发"变成"LLM 误标共享材料后误触发"，仍然存在但触发门槛更高。Codex 说"不可逆夸大、L2 JSON 可重跑"——对，但更深一层：这个合并是**安全网**不是激进规则。降级为 P2 观察 |
| 5 | 答案表无条件覆盖 LLM | **属实，但这是 V1_LESSONS 3.17 显式设计** | Codex 确认测试固化了此行为。第一性原理：答案表是选择题最可靠信号（V1 经验），覆盖是**有意的优先级**。风险（答案表错配）确实存在，但选择题答案短，quality_gate 的"答案可疑"兜底能拦住空/可疑值。P2 合理，不必升 P1 |
| 6 | quality_gate 阈值过松，带"禁止自动发布"仍会入库 | **错误（Claude 事实错误）** | **ingestion.py L168-191：`is_blocked = any("禁止自动发布" in i ...)`，有标记 → status="reviewing" 而非 approved**。Codex 确认真实库 0 条低置信度被自动批准。Claude 的深层点值得保留：**reviewing 题也在 questions 表里，学生端 API 如果不按 status 过滤，这些错题会暴露给学生**——这是真风险，不是"自动批准" |
| 7 | 裸题号优先级过高，答案区题号被收录 | **属实，且影响被我低估** | `_build_question_start_map`（anchor_corrector.py L88-116，裸 "5." 优先 3）**不只是漏题检测——它被 `semantic_anchor.resolve_stem_range` 当作下一题边界**。复现场景：Q4 stem → 噪声行 "5." → Q4 continuation → 真实 Q5。map 把噪声 "5." 当 Q5 起点，Q4 的 corrected stem 被截断为 `['P1L001']`，continuation 丢失。所以裸题号优先级**直接污染切片内容**，不只是虚假重试。合法 P1 |
| 8 | _parse_answer_table 脆弱，pending_qnums 被清空 | **属实** | `_ANSWER_DETAIL_STOP_RE` 清空 pending_qnums，英语卷答案/详解交替出现时会丢答案；table_keys 阻止后续修正。合法 P1-P2。与 #5 相互作用：答案表解析错了，覆盖逻辑会把错误带进库 |

---

## 二、双方都没发现的问题（我的独立贡献）

### 🔴 问题 A（P0，最高优先级）：重复题号 → 整份文档入库级联失败

**刚在真实 e2e 运行中实测**：物理-八十中整份文档 0 题入库，worker 日志满屏：

```
ingestion failed for Q6..Q20:
UniqueViolationError: duplicate key value violates unique constraint "ix_question_instances_doc_qno"
DETAIL: Key (document_id, source_question_number)=(4ae383a6..., 4) already exists.
```

**根因链**：
1. `content_slicer` 对未合并的综合题子题（如 4(1)、4(2)、4(3)）产出**多个 question_number="4" 的 SlicedQuestion**（LLM 子题号归一化 `line_annotator.py:192` 覆盖不完整，部分 LLM 输出格式命中不了，或 LLM 直接重复输出 "4" 而无子题后缀）
2. `ingestion._ingest_one_question` 为每个 SlicedQuestion 插一条 `source_question_number='4'` 的 QuestionInstance
3. 部分唯一索引 `ix_question_instances_doc_qno (document_id, source_question_number)` 拒绝第二次插入
4. **SQLAlchemy session 进入 PendingRollbackError，之后 Q5-Q20 全部级联失败** → 整份文档 0 题

**为什么双方都没发现**：132 项单测跑在 mock/孤立路径上，没有覆盖"真实综合题子题号 + 唯一索引 + 事务失败传播"的组合。**这是测试通过 ≠ 管线可用的典型反例，正是本项目审计一直强调的"虚空通过"**。

**修复方向（不能直接 `session.rollback()`）**：当前所有题目共用外层事务，直接 rollback 会连已成功的题也一起回滚。正确做法是每道题用 savepoint：`async with session.begin_nested():`，异常时只回滚当前题目，外层事务继续。或者改成每题独立 commit。

### 🔴 问题 B（P1）：ingestion 无逐题事务隔离

`ingest_pipeline_result`（ingestion.py L127）`except Exception` 捕获了单题失败，**但没有 savepoint 或 rollback**——session 已被第一个异常毒化，后续所有题无论是否有问题全部失败。修复：每道题用 `async with session.begin_nested():` savepoint，异常时只回滚当前题目。同时：任务失败时错误原因未可靠持久化（当前文档 4ae383a6 仍为 processing/running、result_json 为空），修复后应顺手把失败原因写入 task/document 状态。

### 🟡 问题 C（P2）：文件名 URL 双重编码

aiohttp `FormData.add_field(filename=...)` 把中文文件名存成了 `2026%E5%8C%97%E4%BA%AC...`（DB 里 `documents.filename`、`source_document_name` 全是百分号编码）。不影响入库，但污染显示与来源名。上传脚本需传原始字节名。

### 🟡 问题 D（P2）：e2e 回归缺口

现有 `test_e2e_ingestion_verification.py` 只覆盖单份数学 PDF（无综合题）。**必须补一份含综合题子题的 PDF（物理/化学/英语）到 e2e 测试**，否则问题 A 这类级联失败会再次"测试全绿、生产爆炸"。

---

## 三、从第一性原理的独立修复优先级

```
P0-A   ingestion 每题 savepoint 事务隔离（begin_nested per question）← 先止血，一道题失败不拖垮整份文档
P0-B   锚点校正增加 stem 结束位置校验（复用 _build_question_start_map 截断） ← Claude 的 P0，属实
P0-C   补综合题 e2e 回归测试（物理/化学含子题 PDF）                ← 问题 A 的回归网
P1-A   子题号归一化覆盖加固（line_annotator.py:192 已有正则但覆盖不完整，
       部分 LLM 输出格式命中不了，或 LLM 直接重复输出同题号无子题后缀）
P1-B   reviewing 题在学生端 API 的可见性核查（Claude #6 的深层点，非其结论）
P1-C   答案表解析加固（#8）+ 覆盖 LLM 时做题型一致性校验（#5）
P1-D   任务失败原因可靠落库（当前文档 processing/running 但 result_json 为空，无失败日志）
P2-A   raw_type 字段透传原始题型（#3 的低风险替代方案）
P2-B   prompt 两阶段拆分（#1，先边界后元数据，需实验验证而非假设）
P2-C   上传脚本文件名编码修复（问题 C）
```

**明确不采纳**：
- #3 的"保留原始题型不映射"——会破坏 quality_gate 选项检查，代价大于收益
- #6 的"禁止自动发布仍会入库"——事实错误，ingestion 已正确降级 reviewing

**部分采纳**：
- #4 的"OCR 噪声误合并"——触发条件纠正（需 LLM 显式标记），但风险未消失：LLM 误标共享材料时仍会误触发。保留为观察项，不升优先级

---

## 四、一句话结论

> Claude 的审计质量高、方向对，但**难度分布、合并触发条件、禁止自动发布三处与事实不符**；Codex 的逐条复核诚实且量化准确，但停留在"确认属实"，未上升到根因。**两人都漏掉了真实 e2e 刚暴露的重复题号级联失败——这才是当前阻断入库流程的头号问题**。优先顺序应是：**ingestion savepoint 事务隔离止血 → stem 结束校验 → 综合题 e2e 回归**，而非照单全收 Claude 的 P0 列表。#7 裸题号优先级经复核后从"夸大"升级为"属实且影响被低估"（通过 semantic_anchor 污染切片内容）。
