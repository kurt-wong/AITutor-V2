# AI Tutor V2 — V1 经验教训与强制约束

Version: 2.1
Status: 权威约束
Date: 2026-08-11 07:07:42
Source: `D:\Project\AI Tutors\LOG.md`、`PROJECT_STATUS.md`、`RESTART_PROMPT.md`、`TASKS_F2_F3.md`、`question-quality-fix-plan.md`、`math-teacher-e2e-root-cause.md`

---

## 1. 用途

本文件把 V1 在真实教师版 PDF 解析、入库、配图、审核、部署和验证过程中已经实际踩过的坑，固化为 V2 的硬约束。

V1 已经证明：很多问题不是“模型能力不足”，而是“信息在链路中丢失”或“让 LLM/代码做了错误的事”。V2 后续开发必须先读本文件，再读 `PIPELINE.md` 与 `SAD.md`。

---

## 2. 优先级说明

| 级别 | 含义 |
|---|---|
| P0 | 正式文档解析/入库前必须满足，否则会丢题、错题、错图或静默覆盖真实数据 |
| P1 | 必须纳入架构设计，否则会产生难以维护的多路径解析或来源不可追溯 |
| P2 | 应纳入实现规范，避免重蹈 V1 的运维和测试坑 |

---

## 3. 经验教训与强制约束

### 3.1 LLM 不得直接输出题目原文（P0）

教训：

- V1 早期让 LLM 在 JSON 中直接抄写题干、选项、答案、解析。
- LaTeX 反斜杠未转义导致 `Invalid \escape`、整题丢失或内容被静默损毁。
- `response_format` 只能保证 JSON 合法，不能保证 LaTeX 内容不损坏。

强制约束：

1. 文档解析的 LLM 输出必须是“标注/元数据”，不是“内容”。
2. LLM 输出行号、行范围、题号、题型、答案字母、位置信息等。
3. 代码从原始 Markdown/原生文本中按行号切片生成题干、选项、答案和解析。
4. JSON 中不包含 LaTeX 命令字符串；如必须出现，只能作为低优先级兜底并记录来源。

### 3.1a LLM 行号必须经过代码锚点校正（P0）

教训：

- “LLM 只输出行号”仍不等于“LLM 行号准确”。
- V1 实测中 LLM 行号存在常见 ±1 偏移，直接按行号切片会把题干首行/末行、选项边界、答案边界切偏。
- 如果只修 prompt 不修切片逻辑，LLM 越“自信”，错误行号越容易被静默固化。

强制约束：

1. LLM 输出的行号/行范围一律视为 `coarse_line_range`，不是最终切片边界。
2. 代码必须对 L1 原文做锚点校正：
   - 题号起点：吸附到最近的题号标记，同时避免把 `3. 2x` 误判为小数 `3.2`。
   - 选项边界：按 `A.`、`B.`、`C.`、`D.` 等标记校正；单行多选项必须做行内切分。
   - 答案/详解边界：吸附到答案表、`【答案】`、`【详解】`、`【分析】` 等标记。
   - 相邻题目边界：LLM 起点偏前/偏后时，按下一题起点或稳定标记重新截断。
3. L2 必须同时保存 `llm_anchor`、`corrected_anchor`、`anchor_status`：
   - `exact`：锚点与稳定标记精确匹配。
   - `nearest`：锚点吸附到最近稳定标记，允许范围差。
   - `missing`：找不到稳定锚点，禁止静默切片，进入低置信度或聚焦重试。
   - `retry`：校正后内容校验失败，要求 LLM 在局部区域重新标注。
4. 未经校正的 LLM 行号禁止直接作为最终入库边界。
5. 切片后必须校验题干非空、选择题选项数量、答案/详解来源；校验失败不能视为成功。

### 3.2 L1 采用双源证据路由，禁止单一提取器垄断（P0）

教训：

- PyMuPDF 文本层对数学公式、根号、私有区 Unicode 会丢符号；OCR Markdown 对上下标、化学式、表格也容易错配。
- 单一提取器作为整份正文 L1 基座，会把该提取器的损失固化到下游所有环节。

强制约束：

1. 同时保留 `native raw L1` 与 `ppsv3 raw L1`，不得只保留其中一份。
2. canonical L1 由代码按行/区块证据选择，并保留 `raw_sources/selected_source/evidence/confidence`。
3. PyMuPDF 只作为辅助源：页面尺寸、图片 xref/bbox、答案表定位、上下标几何信息。
4. PP-StructureV3 用于公式符号、复杂版面、扫描页；上下标/化学式/计量单位必须双源校验。
5. LLM 只做行级仲裁，输出 line_id 和 evidence，禁止生成或改写 L1 原文。
6. native 与 PP 冲突时默认低置信度，禁止静默采用任一来源。

### 3.3 JSONL 响应结构不能跨模型假设一致（P0）

教训：

- PaddleOCR-VL-1.6 每行 JSONL 可能打包多个 `layoutParsingResults`。
- PP-StructureV3 通常每行一个。
- 只取 `[0]` 会丢 75% 页面。

强制约束：

1. 所有 JSONL 解析必须遍历 `layoutParsingResults` 全部条目。
2. 轮询任务时必须记录并检查 `extractProgress` 的 `totalPages` 与 `extractedPages`。
3. `extractedPages < totalPages` 时必须告警或失败，不允许静默继续。

### 3.4 图片必须有 page/bbox/placement，禁止猜页（P0）

教训：

- 无 page/bbox 时使用整页图片兜底，会把第 1 页的图关联到后面的题。
- 同一物理图会被广播到 Q9-Q12 等多题。
- bbox 精确匹配会因轻微坐标偏移漏掉同一物理图。

强制约束：

1. 每张配图必须携带 `page_no`、`bbox`、`placement`、`source` 元数据。
2. 无 page/bbox 时不允许自动关联，只能记录 `missing_figure` 并进入审核。
3. **物理图存储去重**：同一物理图在对象存储中只保留一份，通过 `figure_id` 标识。
4. **题-图关联允许多对多**：`question_images` 表中同一 `figure_id` 可关联多道题（共享材料题场景），但必须有显式证据（如同一 figure 出现在多题的 L1 行范围内）。
5. **无证据的跨题广播必须抑制**：没有显式空间/语义证据时，禁止将同一图自动广播到多题。
6. bbox 去重使用 IoU/中心距离判断，不做简单精确相等。

### 3.5 元数据来源优先级必须明确（P0）

教训：

- LLM 元数据全为 `None` 时会覆盖文件名/上传表单解析出的可靠元数据。
- `str(None)` 曾把 `school` 写成字符串 `"None"`。

强制约束：

1. 文件名、上传表单、文档路径解析出的元数据为高优先级。
2. LLM 只填充缺失字段，或只有置信度足够高时才允许覆盖。
3. 所有元数据写入前必须做空值/类型校验，禁止把 `None` 写成字符串。

### 3.6 知识树必须先有种子数据（P0）

教训：

- `knowledge_nodes=0` 时，关键词匹配无论多准都无法写入 `question_knowledge`。
- 结果就是“日志显示已映射，数据库实际为 0”，且不报错。

强制约束：

1. 启用知识点映射前必须先完成知识树初始化。
2. 启动/任务开始时检查知识树是否为空，为空则告警或拒绝映射任务。
3. 映射失败必须回退到 `{SUBJ}-UNKNOWN`，不能静默跳过。

### 3.7 内容完整性必须校验，不能只看“提取成功”（P0）

教训：

- LLM 会自行省略选择题选项、重复选项、截断内容。
- OCR 会产生下划线噪声、错误 Unicode 上标、坏表格、坏图表。
- “题目数量正确”不代表“题干、选项、答案、详解完整”。

强制约束：

1. 选择题必须校验选项数量与重复项。
2. 对原文中的公式、希腊字母、关键符号做保留检查。
3. ASCII 表格、HTML 表格、茎叶图等需要识别为表格/图片，不能按普通文本接受。
4. 缺内容、越界行号、指向整张答案表等结果必须进入低置信度审核。

### 3.8 教师版答案/详解优先，LLM 推理只做兜底（P0）

教训：

- `answer_lines` 为 null 时直接使用 LLM 推理答案，掩盖了教师版参考答案区。
- 后台自动生成详解后直接更新，导致用户无法区分“教师版原文”和“LLM 生成”。

强制约束：

1. 文末答案表、`【答案】`、`【分析】`、`【详解】` 是优先来源。
2. LLM 推理只能作为缺失项兜底。
3. 入库必须保留来源标记：`document_extract` / `llm_generated` / `auto_solve` 等。
4. 已有教师版详解时，自动生成流程不得覆盖。

### 3.9 管线保持简单，不要重建多步切分链（P0）

教训：

- V1 的 section detection、batch splitting、QNO remap、answer merge 中间链成为大量 bug 来源。
- 单次 LLM 标注、代码按行号切片反而让 9 科回归明显更稳定。

强制约束：

1. 文档规模可单次调用时，优先单次 LLM 标注。
2. 不引入与“行号标注 + 代码切片”重复的多步切分链。
3. 如必须拆分，拆分边界必须由 LLM 语义元数据决定，代码只负责机械执行。

### 3.10 Schema 变更必须有 Alembic migration（P0）

教训：

- V1 曾手动 `ALTER TABLE` 加 `solutions.status`，全新环境建库失败。

强制约束：

1. 任何表结构变更必须同步 Alembic migration。
2. 禁止只改模型或只改数据库。
3. 文档/DSD、模型、migration 三处保持一致。

### 3.11 Worker/进程验证必须可信（P1）

教训：

- `uvicorn --reload` 会遗留旧子进程。
- 旧 worker 仍消费 Redis 队列时，新代码根本未被验证。
- 旧 `__pycache__` 可能被加载。

强制约束：

1. 修改解析/worker 代码后，验证前必须清理旧 Python/Celery 进程。
2. 不使用 `--reload` 作为验证模式。
3. 启动后必须确认进程 PID 和队列消费者是新的。
4. 修改核心模块后清理 `__pycache__`。

### 3.12 Live 测试必须隔离（P1）

教训：

- V1 全量 pytest 会真实调用 LLM/OCR，导致长时间挂起和测试环境污染。

强制约束：

1. 常规 pytest 使用 `mock` 模式，不调用外部 LLM/OCR。
2. live E2E 使用独立脚本或显式标记的测试，不允许混入默认套件。
3. 测试库 schema 落后时先重建，不用旧数据误判结果。

### 3.13 错误不能被静默吞掉（P1）

教训：

- V1 曾大量 `except Exception`，关键失败被当成成功。
- API 层直连 DB/MinIO、多个独立 JSON 解析器导致行为发散。

强制约束：

1. 解析失败、映射失败、图片关联失败必须记录结构化原因。
2. 不静默吞异常；无法恢复的路径必须进入失败/低置信度状态。
3. JSON 解析、OCR Provider、LLM Provider 统一入口，避免多份相似实现。
4. API/Service/Repository/Infra 分层遵守 `SAD.md`。

### 3.14 富化任务不能阻塞文档 worker（P1）

教训：

- 解答、难度、嵌入、详解子任务如果同步执行，会占住文档 worker 10-15 分钟。
- 一个文档产生 40+ 个子任务时会填满队列，阻塞后续文档。

强制约束：

1. 文档入库主任务与富化/详解子任务分离。
2. 富化任务使用统一 Background Task，不阻塞文档主任务。
3. 队列需要容量/优先级设计，避免子任务淹没文档任务。

### 3.15 外部 API 限流与超时要防护（P1）

教训：

- 多 worker 并发提交 PP-StructureV3 曾导致 API 队列溢出，返回空结果。
- DeepSeek review 超时 90s，MIMO/OCR 偶发不可用。

强制约束：

1. 外部 API 调用必须有超时、重试上限和退避。
2. 并发提交需要限流或串行化，避免打爆 API。
3. 失败时进入明确 fallback 或失败状态，不能返回空结果当成功。

### 3.16 LaTeX JSON 转义是静默数据损坏（P0）

教训：

- `\f` 是合法 JSON formfeed 转义，会被 JSON 解析器接受但静默损坏内容。
- `\s` 等是非法 JSON 转义，会导致整段 JSON 解析失败。
- `response_format=json` 只保证 JSON 合法，不保证 LaTeX 内容不损坏。

强制约束：

1. 文档解析的正式链路必须避免 LaTeX 进入 JSON；这是 Annotation Paradigm 的直接动机。
2. 如果 LLM 偶尔违规，JSON 修复只能作为防御，不能作为主要依赖。
3. 对 `\b`、`\f`、`\r` 等合法但可能损坏内容的转义要做语义级检查，不能只做语法级修复。

### 3.17 选择题答案必须专用处理（P0）

教训：

- 选择题答案通常只需字母 `A/B/C/D` 或组合 `ABD`。
- LLM 推理全文答案容易引入噪音，且教师版答案表/`answer_lines` 更可靠。
- `answer_lines` 为 null 时如果直接走 LLM 推理，会丢失教师版来源优先级。

强制约束：

1. 选择题答案优先从答案表、`answer_lines` 或 `【答案】` 中提取字母。
2. LLM 推理全文只能作为缺失答案的低优先级兜底。
3. 入库必须标记 `answer_from_document` 或 `answer_llm_fallback`。

### 3.18 共享材料题需要 section 级处理（P0）

教训：

- 完形填空、阅读理解、七选五等题目共享同一篇材料，单纯按题号正则切分会失败。
- V1 的纯题号/block 切分在复合题型上出现过 55.6% 失败率。

强制约束：

1. 先由 LLM 识别 section/材料块及其题号范围。
2. section 材料作为共享上下文，再在 section 内切分子题。
3. 代码负责按 section 元数据组装，不靠关键词猜测材料归属。

### 3.19 跨页合并需要多层验证（P1）

教训：

- 纯文本规则跨页合并只有约 70% 精度。
- 需要文本规则 → VL 文本验证 → VL 图像验证三层过滤。

强制约束：

1. 低置信跨页候选必须经过文本规则过滤。
2. 文本规则无法判定的候选进入 VL 文本验证。
3. 涉及图表/图像语义的候选再进入 VL 图像验证。
4. 任一层判定的硬阻断必须可审计，不能直接合并。

### 3.20 Quality gate 失败不能丢弃全部结果（P0）

教训：

- V1 曾因 quality gate 失败回滚整个 LLM 标注结果，丢失所有已提取数据。

强制约束：

1. 解析结果按题保存；单题质量差只影响该题。
2. quality gate 失败时保留已提取内容并标记低置信度/审核，不整批丢弃。
3. 整批失败的判定必须保留诊断快照，便于定位是模型、解析还是文档问题。

### 3.21 单行选项必须去重并做行内切分（P0）

教训：

- OCR 输出 `A.选项A B.选项B C.选项C D.选项D` 时，LLM 可能为每个选项输出同一行号。
- `_extract_multiple_ranges()` 逐个切片会把同一行切 4 次，导致选项重复 x4。

强制约束：

1. 行号 range 必须先去重。
2. 单行多选项按 `A./B./C./D.` 做行内切分。
3. 相邻题目挤在同一行时，在题号前做机械换行处理后再标注。

### 3.22 L2 行号字段必须在归一化时透传（P0）

教训：

- QD 返回 `stem_lines/options_lines/answer_lines/explanation_lines`，但归一化时被丢弃。
- 结果 L2 标注镜像为空，内容无法追溯。

强制约束：

1. 从 LLM 标注到入库的每一层都必须透传 `*_lines` 和校正后锚点。
2. 入库前检查 L2 行号字段非空。
3. 添加测试防止归一化函数再次静默丢字段。

### 3.23 OCR 题号前必须强制换行（P0）

教训：

- `D. 既不充分也不必要条件5.已知...` 中，下一题题号与上一题选项挤在同一行。
- LLM 无法在行号层面给下一题独立起点。

强制约束：

1. OCR 后处理在题号标记前插入换行。
2. 机械换行规则必须避开小数、化学式、数学表达式等误拆。
3. 无法安全拆分的行进入低置信度，不强行切题。

### 3.24 图片引用检测范围不能只认 `<img>` 和 `![]()`（P1）

教训：

- OCR Markdown 经常不保留函数图/几何图引用，例如题干写“图象如图所示”，Markdown 只有 `$$y=f(x)$$`。
- 只检测 `<img>` / `![]()` 会漏掉大量配图题。

强制约束：

1. 图片引用检测必须覆盖“图/图象/图像”等题干语义线索。
2. 优先使用 Native/OCR 的图片 block、C4 figure anchor、page+bbox 元数据。
3. 没有精确 page/bbox 时禁止整页兜底，记录 `missing_figure` 并进入审核。

### 3.25 MIMO `response_format: json_object` 是专用经验（P2 参考）

教训：

- 不加 `response_format: json_object` 时，MIMO 可能把所有 token 消耗在内部推理，返回空 `content`。

参考：

1. MIMO OpenAI 兼容调用默认开启 `json_object` 约束。
2. 该行为是 Provider 专用，不推广为所有 LLM 的统一假设。
3. 接入新 Provider 时必须验证 reasoning/vision/JSON 三种模式的实际返回结构。

### 3.26 图片物理去重必须是文档级（P0）

教训：

- per-question set 无法阻止同一物理图关联到多题。
- 同一 C4 图曾被广播到 Q9-Q12。

强制约束：

1. 去重集合从”每题独立”改为”文档级”。
2. bbox 去重使用 IoU/中心距离判断，不用精确相等。
3. 物理图存储去重：同一物理图只存一份（通过 `figure_id` 标识）。
4. 题-图关联允许多对多：共享材料题场景下，同一物理图可关联多道题。
5. 无显式证据的跨题广播必须抑制。

### 3.27 Native 图片必须记录 bbox（P1）

教训：

- Native 图片上传时未记录 bbox，无法与 C4/ppsv3 图片比对去重。

强制约束：

1. Native 图片提取时通过 `page.get_image_rects(xref)` 获取精确 bbox。
2. bbox 随图片元数据一起落库。
3. 下游消费时参与文档级物理去重。

### 3.28 答案区不得截断（P0）

教训：

- 大文档答案区曾被 8000 字符截断，导致后部题目答案丢失。

强制约束：

1. 答案区、L1 Markdown、L2 标注不得做静默字符截断。
2. 如需限制 LLM 输入，使用分页/分段输入，不能截断后仍声称完整。
3. 截断路径必须显式标记，并进入低置信度审核。

### 3.29 Solution 质量门默认 draft（P0）

教训：

- 初始 `document_extract` 无讲解时默认 `published`，导致坏结果永不被替换。

强制约束：

1. 空讲解/未通过 review 的 Solution 必须为 `draft`。
2. `published` 只能由有效内容 + 质量门通过产生。
3. 已有 `published` 不被低质量 draft 覆盖，但高质量新结果可以提升状态。

---

## 4. V1 状态提醒

V1 最后停留在 Session #178：F2/F3 代码已改，但因旧进程抢队列而**未完成有效验证**。

因此以下问题在 V2 中必须当作“仍然存在的坑”，不能当作“V1 已解决”：

- 图片物理去重未完成有效验证。
- Solution 草稿/发布生命周期未完成有效验证。
- Native PDF 图片 bbox 记录未完成。
- 跨题共享物理图去重未完成端到端验证。

---

## 5. 与 V2 当前实现的关系

### 已符合

- `PaddleOCRClient` 遍历所有 `layoutParsingResults`。
- 常规后端测试使用 mock，避免 live E2E 挂起。

### 待修正

- `question_extractor.py` 当前仍让 LLM 直接输出题干/选项/答案/解析文本，必须改为行号标注范式。
- 当前正在实现 `ppsv3_l1.py` 与 canonical L1 双源仲裁，尚未完成验收。
- 当前图片模型缺少 `page_no/bbox/placement/source`，也没有文档级去重。

### 待补充

- 元数据来源优先级规则。
- 知识树种子数据检查。
- 页面完整性诊断。
- 内容完整性校验。
- worker/进程验证规范。

---

## 6. 引用要求

以下文档必须引用本文件：

- `rules.md`
- `Docs/01_Product/TASK.md`
- `Docs/01_Product/ROADMAP.md`
- `Docs/02_Architecture/PIPELINE.md`
- `Docs/02_Architecture/SAD.md`
- `RESTART_PROMPT.md`
- `PROJECT_STATUS.md`

### 3.30 OCR 学科路由：公式密集科目用 PaddleOCR-VL，文本密集科目用 PP-StructureV3（P1）

教训：

- 2026-08-18 对照测试：化学/生物/地理/语文/数学各 1 份 PDF，分别用 PP-StructureV3 和 PaddleOCR-VL 跑 L1。
- PP-StructureV3（PPS）对化学多行方程式选项的 B/C/D 标签全部丢失（只剩裸公式），VL 完整保留。
- PPS 公式渲染有字母间空格（`$\mathrm{N a}_{2}\mathrm{S O}_{4}$`），VL 输出正确化学式（`$Na_{2}SO_{4}$`）。
- PPS 在速度（1.4s vs 21.5s）和图片提取数量（85 vs 21）上显著优于 VL。
- 文本密集科目（语文/数学/英语/历史/政治）两者质量接近，PPS 更快、图片更多。
- 两者对表格选项（HTML table 结构）的处理都是短板。

强制约束：

1. **化学默认走 PaddleOCR-VL-1.6**——公式占比42.9%，VL 选项标签保留率和公式质量差距决定性。
   2026-08-18 实测：VL 化学单独跑 0% 丢弃（25/25 入库），PPS 20%。
2. **其余科目走 PP-StructureV3**——生物5.7%、地理0.3%、数学69.7%（但丢弃是解答题锚点问题非OCR），
   PPS 已足够好，速度更快（1-3s vs 20-30s）、图片提取更多。
3. VL API 不稳定时的降级策略：OCR 失败标记 `pending_retry`，PDF 存储后待重试。
   `PaddleOCRClient._submit_with_retry` 覆盖队列满、5xx、网络超时等瞬态错误。
4. 学科路由基于文件名中的科目名或上传时的元数据，不依赖 OCR 结果反推。
5. 路由配置必须可覆盖（`ocr_model` 参数或 `OCR_MODEL_OVERRIDE` 环境变量），不硬编码。
6. VL 的 L1 行结构跟 PPS 不同（行边界、内容分布），题号正则已兼容 VL 转义点（`16\.`）。
7. 两者对表格选项（HTML table 结构）的处理都是短板。
8. **地理综合题分组已验证正确**——11 组单选题组（一材料对应 2-3 题）+ 5 道材料分析题 = 16 综合题。
   单选题组共享地图/图表材料，应作为一道综合题入库（材料+子题）。
9. **图片选项是固有限制**——地理 Q19 选项是 4 幅图片，OCR 无法提取图片内容为文字，
   选项锚点校验必然失败。此类题目需人工审核或图片识别兜底。
10. **试卷缺失题需正确处理**——地理 Q23-Q25 试卷本身缺失，LLM 正确识别但无法提取答案，
    丢弃是正确行为。管线应能区分"OCR/LLM 失败"和"试卷缺失"。
11. **table block 必须整块保留**——`ocr_l1_converter` 不再按换行拆散 `<table>`，
    `l1_postprocessor` 跳过 table 行拆分；否则 HTML 表格选项/答案表会被拆成片段，
    下游正则和 LLM 都看不到完整表格。
12. **VL 队列必须显式关闭**——`PaddleOCRQueue` 后台 worker 不会自退出；
    `simple_pipeline` 在 OCR 链 `finally` 中调用 `close()`，防止 long-running
    worker 中 pending task 累积。

### 3.31 Native/PP 行号编码分离（2026-08-20）

1. PP 行号使用 `P1L001`，Native 行号使用 `N1L001`，禁止双源共用同一行号前缀。
2. canonical 双源 L1 保留 PP 行号；native 行号只写入 `raw_sources["native_line_id"]`，
   LLM 标注阶段只暴露 canonical 行号。
3. 双源合并按 `(page, line_no)` 加文本相似度对齐，不能假设 native 与 PP 共享 `line_id`。

---

## 7. 变更记录

### 2026-08-11 07:07:42

- 创建本文件，固化 V1 已验证教训为 v2 强制约束。

### 2026-08-11 07:19:47

- 新增 3.1a：LLM 行号必须经过代码锚点校正。
- 明确 `coarse_line_range`、`llm_anchor`、`corrected_anchor`、`anchor_status` 契约。

### 2026-08-11 07:29:33

- 按 V1 代码/日志差距分析补充 3.16-3.29。
- 新增 P0：LaTeX 转义根因、选择题答案专用处理、共享材料 section、quality gate 部分保存、单行选项切分、L2 行号透传、OCR 题号换行、文档级图片去重、答案区不截断、Solution draft 质量门。
- 新增 P1：跨页多层验证、图片引用检测范围、Native 图片 bbox。
- 新增 P2 参考：MIMO `response_format: json_object`。

### 2026-08-11

- 版本升至 1.3：修正 3.4/3.26 图片去重语义。
- 物理图存储去重 + 题图关联多对多 + 无证据广播抑制。

### 2026-08-11 23:49:10

- 版本升至 2.0：L1 改为双源证据路由。
- PyMuPDF 降级为辅助源，PP-StructureV3 作为公式/复杂版面识别源。
- 明确 LLM 只能做行级仲裁，不能生成或改写 L1 原文。

### 2026-08-18

- 版本升至 2.1：新增 3.30 OCR 学科路由约束。
- 化学用 PaddleOCR-VL，文本密集科目用 PP-StructureV3。
- 对照测试数据保存在 `test/results/ocr_comparison/`。

### 2026-08-18 19:38:00

- 3.30 新增第 11 条：table block 必须整块保留为单条 L1Line。
- `ocr_l1_converter` 与 `l1_postprocessor` 已实现该约束。

### 2026-08-18 19:46:43

- 3.30 新增第 12 条：VL 队列必须显式关闭。
- `PaddleOCRQueue.close()` / `QueuedPaddleOCRProvider.close()` / `OCRFallbackChain.close()` 已实现。

### 2026-08-20 22:40:51

- 新增 3.31：Native/PP 行号编码分离。
- PP 用 `P1L001`，Native 用 `N1L001`；canonical 保留 PP 行号，native 行号只存 `raw_sources["native_line_id"]`。
