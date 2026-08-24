# AI Tutor Personal Edition — 文档入库管线规范

Version: 5.0
Status: 开发指引基线
Date: 2026-08-11
Supersedes: PIPELINE v4.2
Source of truth: `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`

---

## 1. 目标

本管线负责将教师版 PDF/DOCX 转换为结构化题库数据。

最终输出：

- 题目内容：题干、选项、答案、详解、配图
- 元数据：学科、年级、年份、学校、题型、分值、难度、知识点、出现次数
- 状态：高置信度自动入库，低置信度进入人工审核

### 1.1 V1 教训固化

本文档执行 `Docs/05_Development/V1_LESSONS.md` 的 P0 约束：

- LLM 只输出行号/元数据，不输出题干原文；代码从 L1 原文切片。
- LLM 行号只是粗定位；代码必须做锚点校正后再切片。
- PDF 采用双源证据路由：PyMuPDF native 与 PP-StructureV3 并存，canonical L1 由代码按行选择；不再以单一提取器为整份正文基座。
- 配图必须携带 `page/bbox/placement/source`，禁止猜页和整页兜底。
- 教师版答案/详解优先，LLM 推理只做缺失项兜底并保留来源。
- JSONL 必须遍历全部 `layoutParsingResults`，并用 `extractProgress` 校验页面完整性。
- 复合题 section 级切分、quality gate 部分保存、单行选项、L2 行号透传、OCR 题号换行、答案区不截断、Solution draft 等按 `V1_LESSONS.md` 3.16-3.29 执行。

---

## 2. 输入范围

支持：

- 带文字层的 PDF
- 排版规范的 DOCX
- 扫描版或图片型 PDF

扫描版和图片型 PDF 会进入 OCR/VL 处理，识别结果默认按低置信度处理。

单个文件上限：50MB。

---

## 3. 管线总览

```text
1. 上传与原始文件存储
2. 源文件解析
3. 文本/公式/表格/图片提取
4. 题目切分
5. 配图关联
6. 答案与详解匹配
7. 元数据标注
8. 置信度判断
9. 重复题合并
10. 入库与异步富化
```

---

## 4. 阶段说明

### 4.1 上传与原始文件存储

- 管理员批量上传 PDF/DOCX。
- 原始文件写入 MinIO 或 NAS 对象存储。
- 创建 documents 记录。
- 解析任务进入统一 Background Task 队列。

### 4.2 源文件解析

PDF：

- 生成两份 raw L1：PyMuPDF native 文本层（行号 `N1L001`）、PP-StructureV3 OCR/Layout（行号 `P1L001`）。
- PyMuPDF 负责页面尺寸、图片 xref/bbox、答案表定位、上下标几何信息。
- PP-StructureV3 负责公式符号、复杂版面、扫描页和视觉识别。
- 代码按每行/每区块证据生成 canonical L1，保留 `raw_sources/selected_source/evidence/confidence`；canonical 保留 PP 行号体系，native 行号通过 `raw_sources["native_line_id"]` 溯源。
- 上下标/化学式/计量单位默认双源校验；冲突时进入低置信度，禁止直接接受 PP。

DOCX：

- 解析段落、表格、图片和公式对象。
- 尽量利用 Word 排版结构辅助题目切分。

### 4.3 文本/公式/表格/图片提取

输出统一的中间表示：

- 文本块
- 公式块
- 表格块
- 图片块
- 题目编号和题型线索
- 每页按行编号的 canonical L1（canonical 使用 PP 行号；native/ppsv3 raw L1 保留为可追溯源，native 行号写入 raw_sources）
- 图片的 `page/bbox/placement/source` 元数据

公式内部使用结构化表示，页面和导出时渲染为印刷体，不显示 LaTeX 源码。

### 4.4 题目切分

- 使用 LLM 判断题目边界。
- LLM 输出题号、题型、`stem_lines/options_lines/answer_lines/explanation_lines` 等粗略行号范围。
- 代码先对粗略行号做锚点校正：
  - 题号起点吸附到最近题号标记。
  - 选项边界按 `A./B./C./D.` 等标记校正，单行多选项做行内切分。
  - 答案/详解边界吸附到答案表、`【答案】`、`【详解】`、`【分析】` 等标记。
  - 相邻题目边界按下一题起点重新截断。
- 校正后保存 `llm_anchor`、`corrected_anchor`、`anchor_status`。
- 只有 `anchor_status` 为 `exact` 或 `nearest` 且内容校验通过时才切片入库。
- `missing`/`retry` 进入低置信度审核或聚焦重试，禁止静默切片。
- 禁止让 LLM 把 LaTeX 题目原文抄写进 JSON。
- 支持按学科细粒度题型识别。
- 支持复合题、材料题、一题多问。
- 机械操作，如纯题号提取，可以使用正则；语义判断必须使用 LLM。

### 4.5 配图关联

- 数学/物理/化学中的几何图、电路图、装置图、函数图需要独立截取。
- 图片资源写入对象存储。
- 每张配图与 question_id 建立关联。
- 每张配图必须保留 `page_no/bbox/placement/source`。
- 图片去重是文档级，同一物理图只关联一个题目；bbox 用 IoU/中心距离判断。
- 无 page/bbox 时禁止整页猜测或自动关联，记录 `missing_figure` 并进入审核。
- 如果题目本身是图片，保留原图，并尽量提取图片文本。

### 4.6 答案与详解匹配

支持两种结构：

- 文末答案：按题号反查。
- 题后答案：就近匹配。

匹配规则：

- 优先使用教师版文档结构信息和参考答案区原文。
- LLM 负责判断答案归属和解释归属。
- LLM 答案/详解只能作为缺失项兜底，并标记 `llm_generated` 来源。
- 匹配失败进入低置信度审核。

### 4.7 元数据标注

使用 LLM 按规范自动标注：

- 学科
- 年级
- 年份
- 学校
- 题型
- 分值
- 难度
- 知识点

元数据必须符合 `Docs/03_Data/DSD.md` 中的定义。

来源优先级：

1. 上传表单/文件名/文档路径解析出的元数据。
2. 高置信度 LLM 标注。
3. 任何 `None` 不得写成字符串 `"None"`。

### 4.8 置信度判断

判定维度：

- 题目切分是否完整
- 题干是否完整
- 答案是否匹配
- 详解是否匹配
- 配图是否关联
- 元数据是否可信
- 内容是否完整（选项数量、公式/符号保留、表格/图表识别）

高置信度自动入库。

低置信度进入审核队列，由管理员修正后入库。

### 4.11 页面与内容完整性

- JSONL/OCR 任务必须检查 `extractProgress`，`extractedPages < totalPages` 时告警或失败。
- 选择题必须校验选项数量与重复项。
- 对公式、希腊字母、关键符号做保留检查。
- ASCII 表格、HTML 表格、茎叶图等按表格/图片处理，不能作为普通文本静默接受。

### 4.9 重复题合并

查重方式：

- 文本规则匹配。
- embedding 语义相似度。

同一道题重复出现时：

- 合并为一道题。
- 保留多个来源信息。
- 累加出现次数。

### 4.10 入库与异步富化

入库后通过统一 Background Task 异步执行：

- 生成 embedding。
- 更新出现次数统计。
- 校验答案和详解完整性。
- 生成可供统计分析使用的聚合数据。

---

## 5. 准确率策略

- 高优先级科目：数学、物理、化学、英语、语文、生物、政治。
- 使用字段级指标验收，不只用单一“95%准确率”。
- 其他科目可以适当降低精度要求。
- 开发阶段使用真实教师版文档建立测试集，按科目统计准确率。

字段级目标：

| 指标 | 目标 |
|---|---|
| 题目切分准确率 | 98% |
| 题干提取准确率 | 98% |
| 题号识别准确率 | 98% |
| 答案匹配准确率 | 95% |
| 详解匹配准确率 | 90% |
| 配图关联准确率 | 90% |
| 学科/年级/年份/学校元数据 | 95% |
| 题型识别准确率 | 95% |
| 知识点映射准确率 | 85%，低置信度人工修正 |
| 自动通过题目无需修改比例 | 95% |
| 100 道题人工审核时间 | 10 分钟内 |

说明：

- 自动通过题目无需修改比例是“减少人工”的核心指标。
- 审核效率用于验证 Human-in-the-loop 的成本是否可控。

---

## 6. 模型分工

| 任务 | 模型/方式 |
|---|---|
| PDF 版面解析 | PyMuPDF native + OCR 双源；canonical L1 按证据选择 |
| DOCX 解析 | 本地解析 + LLM 结构化 |
| OCR（学科路由）| 化学 → PaddleOCR-VL；其余 → PP-StructureV3（见 V1_LESSONS 3.30） |
| 题目切分 | LLM |
| 配图截取 | 本地图像处理 + 文档结构 |
| 答案匹配 | 文档结构 + LLM |
| 元数据标注 | DeepSeek / MIMO |
| embedding | NAS 本地轻量模型 |
| 难度评估 | LLM + 规则 + 学习数据 |

所有 LLM 调用必须经过 LLM Gateway。

---

## 7. 配置项

主要配置项：

| 配置 | 说明 |
|---|---|
| PADDLEOCR_VL_ENABLED | 是否启用 PP-StructureV3 |
| PADDLEOCR_VL_TOKEN | PP-StructureV3 API Token |
| PADDLEOCR_API_BASE_URL | PP-StructureV3 API 地址 |
| PADDLEOCR_POLL_INTERVAL_SECONDS | PP-StructureV3 任务轮询间隔 |
| PADDLEOCR_JOB_TIMEOUT_SECONDS | PP-StructureV3 任务超时 |
| NATIVE_MARKDOWN_ENABLED | 是否启用电子文本 PDF Native Markdown |
| NATIVE_TEXT_THRESHOLD | Native 文本层覆盖率阈值 |
| DEEPSEEK_API_KEY | DeepSeek API Key |
| MIMO_API_KEY | MIMO API Key |
| MIMO_BASE_URL | MIMO OpenAI 兼容地址 |
| MIMO_MODEL | MIMO 模型名 |
| DEEPSEEK_VL_MODEL | DeepSeek Vision 模型名（VL 回退） |
| MIMO_VL_MODEL | MIMO 多模态模型名（VL 首选） |
| EMBEDDING_PROVIDER | Ollama |
| EMBEDDING_MODEL | qwen3-embedding:4b |
| EMBEDDING_DIMENSION | 2560 |
| DOCUMENT_MAX_SIZE_MB | 单文件大小上限，默认 50 |
| BATCH_UPLOAD_LIMIT | 批量上传上限 |
| AUTO_APPROVE_THRESHOLD | 高置信度自动入库阈值 |

API Key 必须通过 `.env` 管理，禁止硬编码。

---

## 8. 目标源码结构

建议按以下结构实现：

```text
backend/app/domains/document/
├── api.py
├── service.py
├── pdf_parser.py
├── docx_parser.py
├── image_extractor.py
├── question_splitter.py
├── answer_matcher.py
├── metadata_annotator.py
├── confidence.py
├── question_extractor.py
├── parser.py
├── evaluation.py
├── native_markdown.py
├── line_annotation.py
├── image_metadata.py
├── ocr/
│   ├── __init__.py
│   ├── paddle_client.py
│   └── providers.py
└── tasks.py
```

当前 P2 已落地部分：`ocr/paddle_client.py` 负责 PP-StructureV3 提交、轮询和 JSONL 解析；`question_extractor.py` 通过 LLM Gateway 输出 Question Aggregate JSON。

> **2026-08-25 起（OCR Provider 策略，见 `OCR_PROVIDER_POLICY.md`）**：
> L1 识别仅使用 paddle 系（PP-StructureV3 / PaddleOCR-VL，学科路由）；
> **mimo-vl / deepseek-vl 移出 OCR 驱动链**（不再自动降级驱动入库），
> 仅保留为可选交叉验证入口（默认关）。paddle 不可用时任务标记
> `ocr_unavailable` 等待恢复重跑，不降级 LLM VL。

注意：当前 `question_extractor.py` 仍是临时验证版，允许 LLM 直接输出内容文本。正式 T3 前必须改为“粗略行号标注 + 代码锚点校正”范式，禁止直接复用到正式入库链路。

## 9. 表格选项提取

- 化学等试卷的选项可能位于 HTML table，PPS/VL 直接按行拆分会丢失选项内容。
- 原则：保留 table 类型，解析 `<table>/<tr>/<td>`，处理 `rowspan/colspan`，再提取选项行。
- 集成点：`ocr_l1_converter.py`、`content_slicer.py` 的表格选项切片；验收必须覆盖化学表格选项题。

## 10. PP 主路径

- 主路径为 `simple_pipeline.py`：PP canonical 为正文源，native 只做证据补充，LLM 输出行号/锚点，代码负责定位与切片。
- `pipeline.py`、`l1_arbiter.py` 保留为 fallback。
- 详细实验过程和归档版本见 `docs_archive/2026-08-24/SIMPLE_PIPELINE.md`。

> 变更记录统一记录在根目录 `LOG.md`；历史版本文档见 `docs_archive/2026-08-24/`。
