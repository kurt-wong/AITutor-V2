# AI Tutor 已知问题与修复记录

> 本文件只记录开发过程中发现和修复的 Bug。
> 日常进度、验收结果、架构决策分别写入 `LOG.md`、`PROJECT_STATUS.md`、`Docs/`。
> 新增 Bug 按 ID 追加；修复后标记 `Resolved`，保留历史。

---

## Open Bugs

### BUG-001 英语 composite 材料未进入 DB（旧 DB 数据）

- Status: Open
- 现象：英语 Q26-Q36 材料在 raw/native/OCR/LLM shared_material 中都存在，但 DB stem 不含材料。
- 根因：旧 DB 由旧 `content_slicer` 生成；composite 只取 `stem_line_ids`，没有并入 `shared_material_line_ids`。
- 代码修复：`content_slicer.py` 已改为 composite 材料在前、stem 在后并去重。
- 验收条件：重跑英语入库后，材料完整率应从 `12/23` 显著提升；必须用真实 e2e 报告验证。

### BUG-002 缺库题

- Status: Open
- 现象：L2/管线存在但 DB 缺少 11 题，当前答案验收标记为 `missing_db_question`。
- 涉及科目：历史、地理、物理、生物、英语、语文。
- 验收条件：逐科列出缺库题号并重跑入库或单独修复，目标为归零。

### BUG-003 stem 越界/串题

- Status: Open
- 现象：
  - 语文 Q1/Q8/Q17/Q18 stem 串入下一 section 或下一题材料。
  - 英语 Q11/Q14/Q18/Q25/Q37 stem 越界。
  - 物理多项/实验/解答题 stem 未落在正确 section。
- 根因：LLM 行号边界和锚点校正仍不完整。
- 验收条件：位置正确率 `172/209` 必须逐科提升，且不得降低 stem/材料/选项指标。

### BUG-004 生物缺题 Q1/Q2

- Status: Open
- 现象：生物 Q1/Q2 在 L2 存在但 DB 缺失。
- 根因：旧管线 stem 为空被过滤。
- 验收条件：重跑生物入库后 Q1/Q2 出现在 DB 中。

### BUG-005 答案验证器 composite 子题覆盖不足

- Status: Resolved
- 现象：生物 Q21-Q26 被标为综合题后，验证器未逐子题映射答案，被标为 `composite_subquestion` unverifiable。
- 修复：子题号非数字时回退到父题整体答案长文本匹配，子题部分 matched 才保留 composite_subquestion。
- 验证：9 科 unverifiable 从 23 降到 16，composite_subquestion 清零；严格通过率升至 `158/209 (76%)`。

---

## Resolved Bugs

### BUG-010 P0-A ingestion savepoint 事务隔离

- Status: Resolved
- 问题：单题失败导致 session 进入 PendingRollbackError，整份文档后续题目级联失败。
- 修复：每道题使用 `session.begin_nested()` savepoint；worker 失败时先 rollback 再标记任务失败。
- 验证：真实 PostgreSQL savepoint 诊断 + 3 项测试通过。

### BUG-011 P0-B stem 结束位置校验

- Status: Resolved
- 问题：锚点校正只校验 stem 首行，不校验结束位置。
- 修复：`_truncate_stem_at_next_question` 截断 stem 到下一题起点；截断后同步 `stem_anchor.corrected_line_ids`。
- 验证：`test_stem_end_validation.py`、`test_anchor_corrector.py`、`test_content_slicer.py` 通过。

### BUG-012 P0-G composite 材料合并

- Status: Resolved（代码层）
- 问题：composite 题 `shared_material_line_ids` 与 `stem_line_ids` 分离时，材料被切片逻辑清空。
- 修复：`_slice_single_question` 对 composite 保留材料；`_merge_question_group` 聚合选项。
- 验证：`test_composite_material_separate.py` 17 项通过。

### BUG-013 P0-C 答案表 OCR 错误覆盖 LLM

- Status: Resolved
- 问题：OCR 答案表识别错误（如生物 Q6 `D`、Q7 `∀`）会覆盖 LLM 正确答案。
- 修复：答案表改为来源感知；native 答案表优先，OCR 与 LLM 有效字母答案冲突时保留 LLM。
- 验证：`test_answer_matcher.py` 28 项 + `test_answer_shared_line_id.py` 4 项通过；生物 Q6=`C`、Q7=`A`。

### BUG-014 生物 Q6/Q7 真实答案错误

- Status: Resolved
- 问题：DB 答案 `D/D`，原始 PDF 为 `C/A`。
- 修复：随 BUG-013 的答案表来源感知修复解决。
- 验证：9 科 e2e 答案 mismatch = 0。

### BUG-015 e2e 答案短答案直接匹配假阳性

- Status: Resolved
- 问题：短答案在答案区出现即判定通过，化学/政治/生物/数学被高估。
- 修复：新增 `answer_verifier.py`，按 table/prefix/inline/free_text/composite 多源证据验证，`unverifiable` 必须带原因。
- 验证：`test_answer_verifier.py` 4 项通过；9 科答案基线可复现。

### BUG-016 Qwen VL 配置/文档残留

- Status: Resolved
- 问题：VL 回退已切换为 DeepSeek VL，但 `.env`、活跃文档、smoke 产物仍残留 Qwen VL。
- 修复：删除 Qwen VL 配置，更新文档与 smoke 报告。
- 验证：非归档目录搜索 `qwen_vl / qwen2.5vl / qwen3.7-plus` 无命中。

### BUG-017 验证器 composite 子题号非数字映射

- Status: Resolved
- 问题：生物 Q21-Q26 子题号是 `（1）（2）（3）`，验证器递归后标记 `invalid_question_number`。
- 修复：无法映射子题号时回退到父题整体答案长文本匹配。
- 验证：9 科 `composite_subquestion` unverifiable 清零；commit `67e5a83`。

---

## 历史审查整合说明

以下审查/审计结论已整合进本文件，原 `Docs/05_Development/` 临时审查文档已清理：

- 入库管线数据质量审计（难度、LaTeX、材料、选项、综合题答案）
- P0 入库流程对抗性审查
- P0-A/P0-B 修复对抗性审查
- P0-G 修复对抗性审查
- 文档解析管线对抗性审查
- 管线入库质量紧急问题清单
- 旧 `PROJECT_STATUS_2026_08_20.md`
- `TASK_2.5_REPAIR_PLAN.md` 执行基线

---

## 更新记录

### 2026-08-24 23:30:00

- 建立 `bugs.md`，整合历史审查、审计和紧急质量问题。
- 按文档治理规则，后续 Bug 新增/修复必须追加时间戳记录，不在文件头部直接更新。

### 2026-08-25 02:30:00

- **BUG-003 英语部分修复**（stem 越界/串题）：Q11/Q14/Q18 已修复（根因：`semantic_anchor.resolve_stem_range` is_short_answer 分支忽略 end_marker，语法填空行内编号导致 next_q 越过 section 簇；修复：综合题信任 end_marker，min(end_marker, next_q-1)）。语文 Q1/Q8/Q17/Q18、物理多项/实验/解答题待处理。
- **BUG-002/004 英语 Q46 作文缺库修复**：根因 `_truncate_stem_at_next_question` 按题号大小取边界，OCR 噪声题号行 "48、"（书面表达第一节标题拆行）题号 48 > 46 但文档顺序在作文题之前，把 Q46 stem 截空。修复：边界改"当前题号行/题干起点之后、且题号不小于当前题"的最早题号行（文档顺序 + 题号过滤）。重跑后 Q46 作文 prompt 完整入库，DB 11/11。
- **选项归属假阳性修复（验证脚本）**：`e2e_semantic_report.py` verify_options 对多行选项拼接文本的 section 包含判断产生假阳性（Q1/Q26/Q29/Q33），DB 数据本身正确；改为 L2 options_line_ids 行号区间判断。
- **存量过期测试**：`test_ocr_vision_pdf_fallback.py::test_paddle_queue_full_retries_submit` 自 8574109（10010 熔断）后与生产代码不同步（期望 10010 重试 2 次后成功，实际连续 2 次触发熔断）；已改为 503 瞬态错误重试路径（`test_submit_transient_error_retries_then_succeeds`）。

### 2026-08-25 04:30:00

- **BUG-018 subject 垃圾行（Resolved）**：ingestion `_get_or_create_subject` 查不到就创建，LLM 答案提取返回空/非规范 subject 时产生空名、生物学、英语(A班)、高一物理 4 个垃圾行；28 题（政治文档）subject_id 指向空名行，知识点被回退映射到 MATH-UNKNOWN（subject_code 回退 MATH）。修复：文档 subject 优先 + get-or-create 加固（空名回退"未知"、别名归一化、非 canonical 不创建）；数据侧 28 题改指政治、知识重映射 POLI、4 垃圾行删除。
- **BUG-019 历史 Q38-43 位置误报（Resolved，验证脚本）**：`__q_*` 逐题回退 section（无共享材料）的 norm_text 解析为空，in_section 检查 0% 覆盖误报；DB stem 内容正确。修复：此类题跳过 in_section 检查（越界检查保留）。历史 位置 36/43 → 42/43。
- **遗留**：历史 Q37 缺库（stem 为空）、Q41-43 题干膨胀标记；语文 Q1/Q8/Q17/Q18 stem 越界（与英语同根因，待重跑）。

### 2026-08-25 05:30:00

- **BUG-020 独立题共享材料丢失（Resolved）**：P0-5 旧行为对独立题从 stem 剔除 shared_material_line_ids；语文 LLM 将材料阅读/文言文题标为独立但提供共享材料 → 题目失去材料上下文（报告材料覆盖 0%，无法独立使用）。修复：`content_slicer._slice_single_question` 统一并入材料（材料在前去重）；20 题数据回填（`backfill_chinese_material.py`）。语文材料 4/24 → 24/24。
- **语文重跑验收（2a）**：位置 3/8 → 19/24、严格 18/24、DB 24/24（T0-3 修复普适性验证通过）。
- **遗留（语文）**：Q14-16 诗歌阅读 位置行覆盖 67%（section 边界未覆盖全部 stem 行）；Q17 题干膨胀 1840 字符（reviewing）；Q22 串题（散文阅读_1/四、本大题）。
- **遗留（物理）**：严格 11/19（08-23 旧数据，答案 14/22、选项 16/22、缺库 3），待重跑。

### 2026-08-25 06:30:00

- **3a Q46 需人工审核标记（Resolved）**：`answer_verifier.py` 长自由文本答案（≥100 字符）→ `essay_manual_review`（需人工审核），区别于短答案 `free_text_answer`。英语 Q46 作文 713 字符标记生效。
- **T0-2 泄露 key 轮换（Open，待用户操作）**：实测三个 key（PADDLEOCR_VL_TOKEN/MIMO_API_KEY/DEEPSEEK_API_KEY）**均为 dacad48 泄露原值，尚未轮换**。轮换步骤：
  1. 平台控制台重置：PaddleOCR AIStudio（VL token）、MIMO 开放平台、DeepSeek 开放平台
  2. 新 key 写入 `backend/.env`（gitignore，不入库）
  3. 重启后端后运行 `python test/scripts/_verify_env_keys.py`，三个 key 须均为 OK
  4. 历史泄露仍在 git 历史（dacad48），可考虑重写历史或接受风险

### 2026-08-25 07:30:00

- **3b e2e_ingestion 测试恢复（Resolved）**：重灌二中数学（23/23）；测试文档 ID 改按文件名动态解析（旧硬编码 042f5b90 随重灌失效）+ 难度断言放宽（LLM 标注波动）。9/9 通过。
- **数学解答题 LaTeX 验证缺口（Open）**：DB 答案 `$0$`/`$\frac{4}{3}$` 与答案区 `0`/`4/3` 不匹配（验证器无 LaTeX 归一化），数学 7 题答U（Q13/Q15/Q16/Q19/Q20/Q21/Q22）中至少 Q13 类可修复。方案：answer_verifier 增加 LaTeX 归一化（`$` 剥离 + `\frac{a}{b}`→`a/b`）。
- **phase2b 干净库冲突（Open，待决策）**：统计测试断言全局总数（total==3），与 DB 基线数据（200+ 题）互斥。方案：专用测试库（推荐，需知识树种子+迁移）／跑前清库（破坏基线，重灌恢复）／登记为环境前置。
