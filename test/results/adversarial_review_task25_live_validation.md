# Task 2.5 Live 全量验证 — 对抗性审查报告

**审查时间**: 2026-08-14 22:09
**复核更新**: 2026-08-14 22:20（按项目负责人复核意见修正 3 处数字/表述 + 1 处补充，见 §7）
**审查对象**: `test/results/live_validation/`（`run_live_validation.py` 产出：6 个 run JSON + report.json）
**审查方法**: 独立复算（`test/scripts/adversarial_check_live_validation.py`，不 import 被测管线代码）+ 数据源比对 + 阶段数据核查
**审查结论**: **不通过（NOT ACCEPTED）** — 报告数字与数据源矛盾、结论与脚本自动判定相反、双源验证空转、真实质量缺陷被掩盖

---

## 0. 审查执行摘要

| 检查项 | 结果 |
|---|---|
| 6 个 run JSON 合法性（UTF-8 + JSON） | ✅ 全部合法 |
| report.json 题数/状态/耗时 vs run 文件实际 | ✅ 完全一致 |
| 复现性独立复算 vs report.json | ✅ 一致（数学 21/21、英语 53/54、物理 19/20） |
| 数学 golden 独立复算 vs report.json | ✅ 一致（8/8、8/8、7/8、0/8、3/8、3/8、0/8、3/6） |
| **用户验收报告数字 vs 数据源** | ❌ **耗时、复现率、mock 数据全部无法复现** |
| **验收报告结论 vs report.json 自动判定** | ❌ **report.json overall=FAIL，报告宣称通过** |
| **双源/仲裁验证真实性** | ❌ **mock PP = native 副本，3 份卷 conflicts 全部 = 0，空转** |
| **全卷数据质量** | ❌ **英语 54/54 无答案、物理 16/20 无答案、数学 21/21 带 issues** |

---

## 1. 可确认属实的数据（独立复算交叉验证通过）

以下数字经 `adversarial_check_live_validation.py` 独立复算，与 `report.json` 完全一致：

- **题数（两次运行均一致）**：数学 21、英语 54、物理 20；3 份卷 6 次运行 status 全部 `succeeded`。
- **实际耗时（秒）**：数学 470.0 / 479.1、英语 800.1 / 690.2、物理 477.4 / 457.4。
- **复现性差异（属实，共 2 项）**：
  - 英语 Q54 `stem_line_ids`：run1 7 行 vs run2 10 行（`P8L024-030` vs `P8L024-031,P8L036-037`）。
  - 物理 Q16 type：`fill_in` vs `short_answer`。
- **数学 golden 准确率（属实）**：
  - question_number 8/8 = 100%
  - question_type 8/8 = 100%
  - answer 7/8 = 87.5%（Q11：result=`'2 2'` vs golden=`'$\frac{\sqrt{2}}{2}$'`）
  - stem_line_ids 0/8、options_line_ids 3/8、answer_line_ids 3/8
  - stem_content 0/8、options_content 3/6 = 50%
- **管线"端到端可运行"（弱结论成立）**：3 份真实 PDF 上 pipeline 不崩溃、能产出题目 JSON。

---

## 2. 报告数字无法复现（FAIL-1 ~ FAIL-4）

### FAIL-1：耗时数据全部不一致

| 学科 | 验收报告耗时 | 实际文件耗时（report.json） |
|---|---|---|
| 数学 Run1/Run2 | 292s / 339s | **470.0s / 479.1s** |
| 英语 Run1/Run2 | 282s / 332s | **800.1s / 690.2s** |
| 物理 Run1/Run2 | 294s / 251s | **477.4s / 457.4s** |

6 组耗时无一匹配。实际耗时已与 `math_run1.json` stages 交叉验证（`l1_arbiter` 295.2s + `llm_annotation` 174.4s ≈ 470s 总耗时），数据源自洽；验收报告中的耗时来源不明。

### FAIL-2：复现率 63/65 (96.9%) 无法从数据推出

- 实际总题数 21+54+20 = **95**，2 项差异 → 一致 93/95 = 97.9%。
- 验收报告写 **63/65 = 96.9%**。95 ≠ 65，93 ≠ 63，任何 65 的来源不存在（既不是题数、也不是 golden 题数、也不是差异后的任何组合）。该数字来源不明、无法从数据推出，且**复现性比较仅覆盖 question_number/type/answer/stem_line_ids 四个字段**，不比较 options/answer_line_ids/内容，"完全复现"的说法不严谨。

### FAIL-3：mock 模式数据未保存到报告产物

- `report.json` 中 `"mock": {}` **为空**（本次运行未执行 mock 模式，或执行结果未持久化）。
- 验收报告展示的 mock 表格（3 学科 succeeded、各 1 题、0.3s/1.6s/0.2s）**不是凭空编造**：复核时在当前代码上重跑 mock 模式可复现该数字（数学 1 题 0.3s、英语 1 题 1.6s、物理 1 题 0.2s）。真正的问题是 **mock 结果没有写入 report.json**，导致最终报告产物与展示内容不一致。
- 整改方式：脚本应将 mock 结果持久化到 `report.json`（`generate_report` 的 `mock` 分支在 `--live-only` 下不执行），验收报告只能引用持久化产物。
- 注：`_build_mock_response()` 只构造 **1 道假题**（`P1L001-003`），mock "succeeded" 仅证明管线机械流程不断裂，不证明任何解析质量；即使执行过也无验收意义。

### FAIL-4：选择性呈现（golden 指标缺 2 项）

- 验收报告 golden 表格列了 6 项，**漏掉 `stem_content` 0/8 和 `options_content` 3/6（50%）**。
- report.json 中这两项实际存在（`stem_content: {correct:0,total:8}`、`options_content: {correct:3,total:6}`）。

---

## 3. 结论与自动判定矛盾（FAIL-5）

`report.json` 自动判定：

```json
"overall": "FAIL",
"failures": ["reproducibility:english 1 differences", "reproducibility:physics 1 differences"]
```

`run_live_validation.py` 第 466 行 `return 0 if report["overall"] == "PASS" else 1` — 本次运行 exit code 应为 **1**。

验收报告却宣称："**Phase 1 基线验证通过。可以进入 Step 2（DSD 表迁移 + 数据落库）**"。与脚本自动判定直接相反，且未披露英语/物理复现性差异已导致 FAIL。

---

## 4. 验证设计缺陷：双源/仲裁空转（FAIL-6）

- 验收报告注明"OCR: 不可用 → 使用 native-only"。该自述可作为外部背景，但 `test/results/` 下**没有 PaddleOCR 格式错误或 MIMO/Qwen 400 的日志产物**，无法独立核实；修复 OCR 后必须留下 smoke 日志。无论 OCR 是否可用，本次验证都没有真实第二源参与。
- 但 `run_live_validation.py::build_mock_ppsv3_doc()` **把 native L1 每一行复制为 `source="ppsv3"` 的行**作为 mock PP 第二源，再走"双源合并 + LLM 仲裁"。
- 后果：两个源 100% 相同，仲裁必然零冲突。实测 **3 份卷 `l1_arbiter.conflicts` 全部 = 0**（数学 335 行、英语 795 行、物理 265 行被"审计"，0 冲突）。
- 对比 2026-08-13 真实双源 live-pp：`test/results/phase1_live_pp_result.json` 中 `l1_arbiter.conflicts = 45`（audited=127、llm_audited=104）。真实双源存在 45 项冲突、mock 双源 0 冲突，恰恰证明本次的 0 冲突是**假象**——第二源根本不存在。
- 验收报告"管线结构完整性确认：… 双源合并 → 仲裁 → … 全部通过"是**自证式结论**：两个相同的数据源合并、仲裁，未验证任何真实 OCR/PP 行为。**Task 2.5 的验收前提（真实 PP + 真实 LLM 的完整管线）不满足**，本次最多是 "native-only + 真实 LLM 的 LLM 标注冒烟"。

---

## 5. 真实质量缺陷被掩盖（FAIL-7 ~ FAIL-10）

### FAIL-7：英语卷 54/54 题答案为空

`english_run1.json`：`answer_matched=0`、**`answer_empty=54/54`**、`high_conf=0`、`issues=54/54`。
验收报告将英语展示为"✅ 54 题"，且复现性"53/54"复现的是**空答案**，无任何验收价值。

### FAIL-8：物理卷 16/20 题答案为空

`physics_run1.json`：`answer_matched=4`、`answer_empty=16/20`、`high_conf=3`、`issues=20/20`。

### FAIL-9：数学 answer 87.5% < 95% 验收线，且存在高置信度错误答案（落库前必须堵住的口）

- answer 7/8 = 87.5%，低于 REQUIREMENTS_AND_SOLUTION 验收指标（答案匹配 ≥95%）。
- Q11：result 答案 `'2 2'` vs golden `'$\frac{\sqrt{2}}{2}$'`。`answer_provenance.source = "document_answer_table"`、**confidence = 1.0**，`answer_line_ids = P5L006`（golden P5L005，偏移 1）。
- 精确化：Q11 为 `fill_in`，`confidence=0.85`，issues 仅含"缺 shared_material_line_ids"与"详解 LLM 兜底"，**不含"禁止自动发布"**——按当前质量门它属于可自动发布的高置信度题。目前 pipeline 只产出 JSON、**尚未自动落库**，因此风险是"**Step 2 入库前必须堵住这个口**"（对答案表匹配输出增加内容校验/低置信度门槛），而非"已经污染题库"。
- 数学另：5/21 题答案为空（解答题 17-21）、`question_images` 关联 0（6 张图 `url=null`、`placement=unknown`，图片未落库关联）。
- issues 精确化：数学 21/21 题带 issues，但其中 **13 题高置信度（quality_gate high_confidence=13）可自动发布**，仅 **8 题含"禁止自动发布"**（Q1/Q4 选项锚点缺失 ×2、Q6 锚点需重新标注 ×1、Q17-21 答案缺失 ×5）。"带 issues"≠"全部禁止发布"。

### FAIL-10：golden 比对在本次条件下无验收意义

- golden 基于 PP-StructureV3 行号/内容（`l1_fixture: l1_snapshot_math_real_ppsv3_postprocessed.json`），本次跑 native-only，行号体系天然不同（stem_line_ids 0/8、answer_line_ids 全偏移 1、stem_content 0/8）。
- 该比对结果是**无效测试**（条件不匹配），既非"通过"也非"失败"。验收报告把它列出来并用"预期行为"解释，同时隐瞒了 stem_content 0/8，属于把无效数据当作验收依据的误导性呈现。

---

## 6. 审查结论与整改要求

**Task 2.5 Live 全量验证：不通过验收。** 在以下问题解决前，**禁止进入 Step 2（DSD 表迁移 + 数据落库）**，尤其禁止以英语 54 题、物理 16 题空答案为入库基线。

必须整改：

1. **修复 OCR 链路**（PaddleOCR 返回格式错误、MIMO/DeepSeek VL 400），用真实 PP 数据重跑；在此之前不得再宣称"双源完整管线通过"。**注意**："OCR 不可用"目前只有验收报告的自述，`test/results/` 下没有 PaddleOCR 格式错误或 MIMO/DeepSeek VL 400 的日志产物，只能作为外部背景、不能作为验收依据；修复 OCR 后必须单独留下 smoke 日志供复核。
2. **验收报告必须如实呈现**：以 `report.json` 为准（overall=FAIL + 失败项），补上 stem_content/options_content，修正耗时与复现率数字；mock 结果须先持久化到 `report.json` 再引用，禁止引用未落盘的展示数据。
3. **建立英语/物理 golden**（验收报告注意事项自己也承认缺失），用于内容级比对，而非只比题数。
4. **修复 answer_matcher 行号偏移与高置信度错误答案**：Q11 `'2 2'`（provenance confidence=1.0、题目 confidence=0.85、无"禁止自动发布"issue）在 **Step 2 落库前必须堵住**——对答案表匹配输出增加内容校验/低置信度门槛，native 答案表行号偏移需校正；当前尚未自动落库，属"待堵口"而非"已污染"。
5. **明确本次验证的定位**：降级为 "native-only + 真实 LLM 冒烟（annotation 稳定性）"，写入文档时不得表述为 Task 2.5 验收通过。

---

## 7. 审查产物

- `test/scripts/adversarial_check_live_validation.py` — 独立复算脚本（含 golden 逐题明细、复现性、report 一致性检查），`python test/scripts/adversarial_check_live_validation.py` 可随时重跑。
- `test/scripts/adversarial_check_stages.py` — 阶段数据核查辅助脚本。
- 数据源：`test/results/live_validation/{math,english,physics}_run{1,2}.json`、`report.json`、`test/annotations/golden/math_real_golden.json`、`test/results/phase1_live_pp_result.json`。

---

## 8. 复核更新（2026-08-14 22:20，按项目负责人复核意见）

项目负责人独立重跑复算脚本并逐项核对 run JSON，确认 FAIL-1~FAIL-10 的绝大多数数字属实（耗时、复现率、双源空转、英语/物理答案为空、Q11 错误答案等），同时提出 3 处修正 + 1 处补充，本报告已按以下要点修订：

| # | 复核意见 | 本报告修订 |
|---|---|---|
| 1 | "真实双源 conflicts=42"错误，`phase1_live_pp_result.json` 实际为 **45** | 已改为 45，并补充该对比"更说明真实双源有冲突、mock 0 冲突是假象" |
| 2 | mock 数字非凭空编造，项目负责人已重跑复现（0.3s/1.6s/0.2s）；问题在未持久化 | FAIL-3 改为"未保存到报告产物"，整改方式为脚本持久化 mock 结果后再引用 |
| 3 | "21/21 issues"≠"全部禁止自动发布"：数学 13 题高置信度可发布，8 题含"禁止自动发布"；Q11 属可发布高置信度题 | FAIL-9 精确化：风险表述改为"Step 2 入库前必须堵住的口"，非"已污染题库" |
| 补充 | "OCR 不可用"无日志产物，只能作外部背景；修复后须留 smoke 日志 | 整改要求 1 已补充 |

**最终复核结论（与项目负责人一致）**：本次结果降级为 **"native-only + 真实 LLM 冒烟"**，**禁止进入 Step 2 落库**；在真实 PP 重跑、英语/物理 golden 建立、答案匹配修复、完整质量指标披露之前，不得宣称 Task 2.5 通过。
