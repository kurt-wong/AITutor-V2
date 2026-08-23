# PP 主路径实验管线

Status: 实验路径（未切换主链路）
Date: 2026-08-16

## 目标

验证“PP markdown 为正文源 + native 只作证据补充 + 单次 LLM 语义提取”是否能替代当前
逐行双源 LLM 仲裁主链路，同时不降低答案/详解/来源质量。

## 边界规则

```text
PP 非空
  → 正文使用 PP，native 仅写入 raw_sources 作为证据，并保留 native_line_id

PP 为空
  → 同页同行 native 填充，标记 native_fallback

PP 与 native 冲突
  → 保留 PP，标记低置信度，进审核

公式/表格/HTML 结构行
  → 默认信任 PP，不自动用 native 替换
```

native 合法用途：

- 图片 bbox/xref 补充
- 答案表定位证据
- PP 空行/缺失内容兜底

行号规则：PP 使用 `P1L001`，Native 使用 `N1L001`；canonical 保留 PP 行号，native 行号只通过
`raw_sources["native_line_id"]` 溯源。

## 代码路径

- `backend/app/domains/document/simple_pipeline.py`
  - `run_simple_pipeline()`：PP 主路径实验管线
  - `_build_pp_canonical()`：PP canonical + native 证据
- `test/scripts/simple_pipeline_experiment.py`
  - 对 math/english/physics 3 份 PDF 跑实验并输出 JSON
- `backend/tests/test_simple_pipeline.py`
  - 验证 PP 主路径跳过 l1_arbiter

当前 `pipeline.py`、`l1_arbiter.py`、`anchor_corrector.py` 保持不变，作为 fallback。

## 实验命令

```powershell
# live 实验（真实 PP + LLM）
python test/scripts/simple_pipeline_experiment.py

# 每科跑 2 次，用于复现性观察
python test/scripts/simple_pipeline_experiment.py --runs 2

# 30 份 PDF 批量基线（先跑 10 份 pilot）
python test/scripts/simple_pipeline_batch.py --limit 10
python test/scripts/simple_pipeline_batch.py
```

输出：

```text
test/results/simple_pipeline_experiment/{subject}_run{N}.json
test/results/simple_pipeline_experiment/summary.json
```

## 对比指标

| 指标 | 口径 |
|---|---|
| 题目数 | simple pipeline vs 当前 live_pp run |
| 题干/选项/答案/详解完整度 | 非空 + 来源可追溯 |
| 行号 refs 有效性 | 所有 line_id 必须存在于 PP L1 |
| answer_empty | 与当前管线对比 |
| LLM 调用数 | 当前 vs simple |
| 阶段耗时 | llm_annotation、l1_arbiter、总耗时 |
| 复现性 | runs=2 时 question/answer/answer_line_ids 差异 |

## 当前状态

- simple pipeline 代码和测试已完成
- 后端全量测试（排除已知 tmp_path 权限用例）：301 passed
- 2026-08-16 14:49：3 份 PDF、6 个 run 实验完成
  - math/english/physics 均 `answer_empty=0`
  - 三科均 `blocked=0`
  - 三科两跑复现 match
  - 总耗时约 19 分钟
- 尚未切为主链路
- 下一步：用 `simple_pipeline_batch.py` 跑 30 份 PDF 基线，数据通过后再决定是否切换

## 3 份 PDF 对比结果（2026-08-16 14:49）

### 耗时

| 科目 | 旧 live_pp 单次 | simple pipeline 单次 |
|---|---:|---:|
| math | 约 25.4 分钟 | 约 2.7 分钟 |
| english | 约 25.3 分钟 | 约 2.7-3.6 分钟 |
| physics | 约 15.7 分钟 | 约 4.1 分钟 |

6 个 run 总耗时：旧约 2 小时，simple 约 19 分钟。

### 质量/复现性

| 科目 | answer_empty | blocked | 两跑复现 |
|---|---:|---:|---|
| math | 0/19 | 0 | match |
| english | 0/54 | 0 | match |
| physics | 0/20 | 0 | match |

### golden 字段对比

| 字段 | math 旧→simple | english 旧→simple | physics 旧→simple |
|---|---:|---:|---:|
| question_number | 8/8 → 8/8 | 54/54 → 54/54 | 20/20 → 20/20 |
| question_type | 8/8 → 8/8 | 54/54 → 54/54 | 18/20 → 18/20 |
| answer | 8/8 → 8/8 | 29/54 → 31/54 | 2/20 → 2/20 |
| stem_line_ids | 7/8 → 7/8 | 45/54 → 45/54 | 8/20 → 8/20 |
| options_line_ids | 8/8 → 8/8 | 49/54 → 49/54 | 14/20 → 14/20 |
| answer_line_ids | 7/8 → 7/8 | 54/54 → 54/54 | 6/20 → 6/20 |
| stem_content | 8/8 → 8/8 | 52/54 → 52/54 | 10/20 → 10/20 |
| options_content | 6/6 → 6/6 | 29/29 → 29/29 | 14/14 → 14/14 |

英语/物理 golden 仍为 draft，低匹配率主要来自 golden 自证/格式问题，不是 simple pipeline 退化。

### 结论

- simple pipeline 未劣于旧 live_pp，且性能显著提升。
- 下一步：用现有 30 份 PDF 跑 simple pipeline 基线，再做最终切换决策。

## 10 份 pilot 结果（2026-08-16 15:50）

### 总体

- 10 份 PDF、282 题
- answer_empty=114（40.4%）
- blocked=125（44.3%）
- 总耗时约 50.8 分钟（平均约 5 分钟/份）

### 分科问题

| 文档 | 题数 | answer_empty | blocked |
|---|---:|---:|---:|
| 历史-东城 | 43 | 43 | 43 |
| 历史-海淀 | 32 | 32 | 32 |
| 政治-东城 | 28 | 12 | 13 |
| 化学-八一学校 | 26 | 9 | 6 |
| 数学-二中 | 23 | 11 | 12 |
| 数学-二十中 | 21 | 0 | 3 |
| 数学-八中 | 21 | 1 | 1 |
| 英语-东城 | 46 | 1 | 6 |
| 物理-丰台 | 22 | 2 | 6 |
| 物理-九中 | 20 | 3 | 3 |

### 根因判断

- 朝阳三科表现好，但不能代表全部 9 科。
- 历史/政治/化学等科目答案区格式未被 `answer_matcher` 的规则覆盖，导致大量 `answer_empty` 和 blocked。
- 当前 simple pipeline 的答案/详解仍依赖 `answer_matcher` 的正则/规则，而不是 LLM 在同一次语义提取中输出 `answer_lines/explanation_lines`。
- native 答案区只被统计为证据，未实际注入答案匹配链路。
- 还有 `invalid_line_id`、`section 仅包含单题` 等 LLM 标注稳定性问题。

### 结论

- **simple pipeline 暂不具备切换条件。**
- 下一步不是跑 30 份全量，而是先把“LLM 语义提取”扩展为同时输出答案/详解 refs，让答案匹配不再依赖写不完的规则。

## 答案/详解 refs 已接入（2026-08-16 16:01）

- `line_annotator` 的标注契约新增：
  - `answer_line_ids`：该题答案所在 L1 行，选择题/填空题指向答案表或题后答案行，解答题指向解题过程中的答案行
  - `explanation_line_ids`：该题详解/解题过程所在 L1 行
  - `answer`：仅客观题短答案（如 `C`、`AB`），必须是从答案区逐字提取的短结果，不输出题干/选项/详解原文
- `simple_pipeline` 调用 `match_answers(..., llm_annotation=annotation)`：
  - 优先使用 LLM 行号从 PP/native canonical L1 原文切片
  - `answer_matcher` 只对 LLM 缺失项做确定性 fallback
- 后端全量测试 **311 passed**，`validate_docs_vs_code.py` 通过。
- 下一步：先用 3 份 PDF 重跑验证，再跑 10 份 pilot，确认历史/政治/化学答案区不再大规模 `answer_empty`。

## 答案行号质量防线（2026-08-16 16:16）

- LLM 答案行号切片若指向明显非答案内容（解析/分析头、与题干高度重叠、超长且含题干特征词），回退到 `answer_matcher` 规则匹配。
- `quality_gate` 拦截 `llm_annotation` 来源的空答案或纯标点答案，标记 `禁止自动发布`。
- `_clean_llm_sliced_answer` 支持 `故选 / 答案为 / 答案是 / 故答案为 / 答案： / 选` 等常见答案前缀清理。
- `correct_anchors` 继续保留在 simple pipeline：它处理 stem/options 的粗定位、缺失回退和确定性范围收敛；answer/explanation refs 不在该环节。

## 3 份 PDF 重跑（2026-08-16 16:52）

- math 19、english 54、physics 20，三科均 `answer_empty=0`、`blocked=0`。
- math/english 两跑复现性 0 差异。
- physics 4 项差异根因：Q18 混入 PP 图注行 `P10L001`，Q19 公式跨行行号不稳定。
- 新增 `_normalize_short_answer_line_ids()`：过滤短图注噪声、补齐公式跨行、按 L1 order 稳定排序。
- 用现有 physics run1/run2 复算，Q18/Q19 answer_line_ids 已收敛。
- 下一步：用户本机重跑 `simple_pipeline_experiment.py --runs 2` 确认 physics 复现性 0，再跑 10 份 pilot。

## 同行多题答案按题号切分（2026-08-16 16:57）

- LLM 的 `answer_line_ids` 指向同一行时，代码按题号边界只切当前题答案，修复 Q11/Q12/Q13 拼接。
- 兼容 PP 将 `（13）` 识别为 `ги13гй` 的 OCR 噪声。
- 无效 stem 行号由 `line_annotator` 过滤，`anchor_corrector` 对缺失 stem/options 确定性回退；无需新增规则。

## 错误题号行回退与漏题防护（2026-08-16 17:43）

- 非解答题遇到含答案表题号但不含当前题号的行时，跳过该行并回退 `answer_matcher` 规则链，避免把别的题答案拼进当前题。
- `line_annotator` prompt 要求不得跳过题号；无法定位时输出空行号。

## 10 份 pilot 结果（2026-08-16 19:52）

- 10 份 PDF 全部 succeeded，280 题；`answer_empty=7`（2.5%）、`blocked=46`（16.4%）。
- 相比上一轮 10 份 pilot：`answer_empty` 114→7、`blocked` 125→46。
- 总耗时约 45.1 分钟，平均约 4.5 分钟/份。
- 剩余空答案：历史东城 Q42/Q43、历史海淀 Q31/Q32、政治 Q27、物理九中 Q20、数学八中 Q18。
- 剩余 blocked 主要为“锚点需重新标注”；另有少量答案可疑、选项异常。

## 精确优先输出与 LLM 重试（2026-08-16 20:22）

- `PipelineResult.to_dict()` 新增 `ingested_questions` / `discarded_questions` / `ingest_summary`。
- `simple_pipeline` 在存在 blocked、answer_empty 或缺失题号时，LLM 标注重试一次；重试后仍失败则进入 `discarded_questions`。
- `simple_pipeline_batch.py` summary 增加 ingested/discarded/discard_reasons。
- 后端全量 **313 passed**。

## 对抗审查修复（2026-08-16 20:37）

- 重试改为选择两遍中质量更优的结果，避免重试导致质量回退。
- 重试 pass 中间阶段异常时回退第一遍结果。
- 重试触发条件收窄：blocked、answer_empty、缺失题号。
- 最终采用 stage 标记 `selected: true`。
- `discard_reasons` 每题去重；discarded 题目包含 `discard_categories` / `discard_details`。
- `quality_gate` 校验 `llm_annotation` 的 `answer_line_ids` 非空。
- 丢弃率暂定阈值 **<10%**。
- 后端全量 **316 passed**。

## PDF 视觉 OCR 回退（2026-08-16 21:16）

- PDF 不再直接作为图片发送；`LLMVisionOCRProvider` 用 PyMuPDF 渲染每页为 PNG，逐页调用 MIMO/DeepSeek Vision。
- `PaddleOCRClient` 对 submit HTTP 400 code 10010 自动重试。
- `simple_pipeline_batch.py` 单个 PDF 异常不会中止批次，summary 每次 run 后增量保存。
- 后端全量 **319 passed**；OCR smoke/batch 需用户本机网络环境复跑。

## 语义锚点（2026-08-17）

目标：LLM 不再承担精确行号职责，改为输出 `stem_markers` 作为定位计划；代码从 PP/native 原文切片，保证最终内容来自原文。

代码路径：

- `backend/app/domains/document/semantic_anchor.py`
  - `normalize_marker_text()`：统一全半角、空白和常见 OCR 标点差异
  - `find_marker()`：先精确匹配，再模糊匹配；支持跨两行 marker
  - `resolve_stem_range()`：按 start/end marker 解析题干 L1 范围；end 缺失时用下一题/选项/答案区边界
- `backend/app/domains/document/line_annotator.py`
  - LLM prompt 新增 `stem_markers.start/end`
  - 解析结果写入 `L2QuestionAnnotation.stem_start_marker/stem_end_marker`
- `backend/app/domains/document/anchor_corrector.py`
  - 题干优先级：`semantic markers → LLM line_ids → retry`
  - 题号正则允许 `3.2025年...`，同时排除 `3.2x`、`3.14`、LaTeX 续行
- `backend/app/domains/document/pipeline.py`
  - `PipelineResult.to_dict()` 新增 `llm_annotation` 诊断块，保存 LLM 原始响应和 marker 状态

验证：

```powershell
python test/scripts/run_physics_validation.py
python test/scripts/run_9subject_validation.py --runs 1
```

`run_9subject_validation.py` 覆盖历史、政治、英语、语文、地理、数学、物理、化学、生物各一份 PDF，输出到 `test/results/9subject_validation/`。

当前 Task 2.5 仍 NOT_ACCEPTED，禁止进入 Step 2；9 科验证结果由用户决定启动后作为下一步证据。

## Retry hints（2026-08-17）

第二遍 LLM 标注不再盲重试：

- `simple_pipeline` 第一遍质量门失败后，`_build_retry_hints()` 把题干、选项、答案的失败锚点汇总成结构化提示。
- `line_annotator.build_annotation_prompt(doc, retry_hints=...)` 在 prompt 末尾追加“上一轮标注问题（必须修正）”。
- `llm_annotation_retry` stage 记录 `hint_count`，便于审计重试反馈是否生效。

验证：

```powershell
python test/scripts/run_composite_validation.py --subjects 数学,化学 --runs 1
python test/scripts/run_composite_validation.py --runs 1
```

`--subjects` 用文件名中的科目名过滤；不传时运行 9 科样本。

## OCR 学科路由（2026-08-18）

### 背景

V1 经验：化学方程式下标被 PPS 识别为普通数字。V2 默认模型是 PP-StructureV3（`PaddleOCRClient.__init__` 的 `model` 参数默认 `"PP-StructureV3"`）。

### 对照测试结果

5 科各 1 份 PDF，PPS vs PaddleOCR-VL 双模型 L1 对比：

| 科目 | 指标 | PPS | VL | 优胜 |
|---|---|---|---|---|
| 化学 | 选项标签 | ❌ B/C/D 丢失 | ✅ 全部保留 | **VL** |
| 化学 | 公式质量 | ❌ 字母间空格 | ✅ 正确 | **VL** |
| 化学 | 图片数 | 85 | 21 | PPS |
| 化学 | 速度 | 1.4s | 21.5s | PPS |
| 语文/数学 | 各项 | 接近 | 接近 | PPS（更快、图片更多） |
| 生物/地理 | 待确认 | — | — | 先用 PPS |

详细数据：`test/results/ocr_comparison/comparison_report.json`

### 路由方案

```python
# 学科 → OCR 模型映射
SUBJECT_OCR_MODEL = {
    "化学": "PaddleOCR-VL-1.6",  # 公式占比42.9%，VL 选项标签保留率和公式质量差距决定性
}
DEFAULT_OCR_MODEL = "PP-StructureV3"
```

### 实现路径

1. `PaddleOCRClient` 构造时绑定 `model`，`extract()` 也支持 `model` 覆盖。
2. `build_ocr_chain(model=...)` 将 model 透传给 `PaddleOCRClient`。
3. `run_simple_pipeline(subject=..., ocr_model=...)` 自动识别学科并路由。
4. 学科识别：文件名必须含科目名 + 考试关键词（期末/模拟/月考等），避免误匹配。
5. 路由可通过 `ocr_model` 参数或 `OCR_MODEL_OVERRIDE` 环境变量全局覆盖。

### 各科题目特征分析（决定路由依据）

| 科目 | 公式占比 | 表格 | 图片数(PPS) | PPS丢弃率 | 路由 |
|---|---|---|---|---|---|
| 化学 | **42.9%** | 6 | 85 | 20%(PPS)/0%(VL) | **VL** |
| 数学 | 69.7% | 2 | 76 | 9%（解答题锚点） | PPS |
| 生物 | 5.7% | 9 | 60 | 0% | PPS |
| 地理 | 0.3% | 7 | 112 | 12% | PPS |
| 语文 | 0% | 0 | 92 | 0% | PPS |
| 英语/物理/历史/政治 | — | — | — | <10% | PPS |

详细数据：`test/results/ocr_comparison/comparison_report.json`、`test/results/_subject_analysis.txt`

### live 测试结论（2026-08-18）

化学 VL 单独跑：25 题全部入库，0% 丢弃（PPS 20%）。
化学 VL 模型名必须是 `"PaddleOCR-VL-1.6"`（非 `"PaddleOCR-VL"`），否则 API 静默回退 PPS。
VL API 不稳定时（队列满/5xx/超时），`_submit_with_retry` 自动重试（指数退避，最多5次）。
全量跑 VL 时 PaddleOCR 队列满风险高——已由 `PaddleOCRQueue` 单并发保护。

## 表格 block 与 VL 队列保护（2026-08-18）

### 表格 block 处理

- `ocr_l1_converter` 对 `block_label=table` 的 block 整块保留为单条 L1Line，不再按换行拆散。
- `l1_postprocessor` 对 `block_type=table` 的行跳过题号/选项行内拆分，避免 `<table>` 单元格里的 `1.`/`A.` 被误判为新题或选项。
- 效果：PP/VL 输出的 HTML `<table>` 保持完整，`answer_matcher` 可继续用 `<table>...</table>` 整表解析。

### VL 队列保护

- `build_ocr_chain(model=...)` 对包含 `VL` 的模型使用 `QueuedPaddleOCRProvider`，底层 `PaddleOCRQueue(max_concurrent=1)`。
- 化学 `PaddleOCR-VL-1.6` 走单并发；PP-StructureV3 仍直接使用 client，不额外排队。
- 新增真实并发测试：同一队列并发提交 2 个 PDF，`max_active == 1`。
- `simple_pipeline` 使用完 OCR 链后调用 `ocr_chain.close()`，取消 VL 队列后台 worker，避免 long-running 进程残留 pending task。
