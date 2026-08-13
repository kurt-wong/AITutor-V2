# AI Tutor Personal Edition — 开发任务计划

Version: 1.3
Status: 执行基线
Date: 2026-08-11
Source of truth: `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`

---

## 1. 定位

本文件是项目开发任务计划的权威基线。后续任务必须能对应到本文件中的阶段和验收标准。

本文件描述目标计划，不代表已实现。阶段完成情况以 `PROJECT_STATUS.md` 为准。

文档解析相关阶段必须同时遵守 `Docs/05_Development/V1_LESSONS.md`。

---

## 2. 第一性原理

系统核心链路：

```text
教师版文档 → 结构化题目 → 审核入库 → 检索/练习 → 学生反馈 → 掌握度 → 生成/导出
```

执行原则：

1. 先打通最薄的端到端闭环，再扩大覆盖。
2. 文档解析准确率是最大风险，必须先建立可量化验证。
3. 数据和接口契约先定，UI 最后做。
4. 复用现有 PostgreSQL/Redis/MinIO/Ollama 和已配置的云 API。
5. 每个阶段必须有可运行结果和验收标准，禁止 big-bang 交付。

---

## 3. 阶段计划

### P0. 本地运行与测试资产基线

目标：让后端能在现有 Docker 服务上稳定运行，并把 30 份 PDF 变成可复用的测试基线。

交付：

- 后端使用现有 `aitutor-postgres`、`aitutor-redis`、`aitutor-minio` 正常启动。
- 建立 `test/pdf/` 文件清单，记录科目、文件、大小、是否包含答案、是否含图。
- 建立 `test/` 下的解析结果、标注结果、测试脚本目录结构。
- 补上 `backend/scripts/validate_docs_vs_code.py` 或明确移除该引用。

验收：健康检查通过，MinIO 可连接，PDF 清单可被测试脚本读取。

### P1. 文档上传与后台任务

目标：完成 PDF 入库的入口和状态跟踪。

交付：

- 文档上传 API。
- MinIO 对象存储写入。
- `documents` 记录创建。
- 统一 Background Task 创建与状态查询。
- Domain Event 发布“文档已上传”。

验收：上传一份 PDF 后，能通过 API 查询到文件、状态、任务进度和错误信息。

### P2. 文档解析验证

目标：验证“Native/PP 双源 L1 → LLM 行级仲裁 → canonical L1 → LLM 行号标注 → 代码切片”能否把教师版 PDF 转成结构化题目。

交付：

- 同时生成 PyMuPDF native raw L1 与 PP-StructureV3 ppsv3 raw L1。
- PyMuPDF 只用于页面尺寸、图片 xref/bbox、答案表定位、上下标几何信息。
- PP-StructureV3 用于公式符号、复杂版面、扫描页和视觉识别。
- 新增 canonical L1 生成：按行选择 source，保留 `raw_sources/selected_source/evidence/confidence`。
- LLM 只做行级仲裁，禁止生成或改写 L1 原文。
- OCR/VL 回退链：PP-StructureV3 → MIMO → Qwen。
- LLM 输出 Question Aggregate JSON：题号、题型、粗略行号范围、答案字母、元数据等。
- 代码对粗略行号做锚点校正后，再从 L1 原文切片生成题干、选项、答案、解析。
- L2 保存 `llm_anchor/corrected_anchor/anchor_status`，禁止未校正行号直接入库。
- 配图输出 `page/bbox/placement/source`，建立文档级去重。
- 页面完整性诊断：遍历全部 `layoutParsingResults` 并检查 `extractProgress`。
- 输出到 `test/` 的解析结果目录，保留置信度。
- 字段级准确率统计脚本，用 30 份 PDF 建立基线。

验收：至少 1 个科目、多份 PDF 能产出可审核题目 JSON；canonical L1 每行可回溯到 native/ppsv3 raw L1；解析结果使用“粗略行号 + 代码锚点校正”而非 LLM 抄写内容；能统计“题号识别、题干提取、答案匹配、详解匹配”的准确率。

### P3. 题库与审核队列

目标：把解析结果变成正式题库数据。

交付：

- 题目 CRUD。
- 低置信度审核队列。
- 审核通过/驳回流程。
- Question Instance 保存来源、页码、题号、年份、学校。
- 重复题合并的初步规则。

验收：解析 JSON 可进入审核队列，管理员审核后进入正式题库。

### P4. 搜索、去重与 embedding

目标：让题库可检索、可查重、可支撑统计。

交付：

- 条件搜索：科目、题型、年级、年份、难度。
- embedding 生成：`qwen3-embedding:4b`，2560 维，写入 `question_embeddings`。
- 暴力余弦查重/相似题检索。
- 知识点映射。
- 题型频次、年份趋势、知识点占比、难度分布统计。

前置：知识树必须先初始化种子数据，禁止在空知识树上静默跳过映射。

验收：能对一道新题找到相似题，能生成基础统计报表；知识映射结果可追溯到已有知识树节点。

### P5. 学生错题

目标：完成“拍照错题 → 识别 → 匹配/新建 → 错题本”。

交付：

- JPG 上传与切分。
- 识别、匹配题库或新建草稿题。
- 管理员确认后进入错题本。
- 错题列表、详情、重练、标记已掌握。

验收：一张含多题的 JPG 能切分并进入审核流程。

### P6. 练习与掌握度

目标：让学生真正用题库练习并积累反馈。

交付：

- 手动/推荐练习会话。
- 题目快照、学生答案、判分、用时。
- 答错自动进入错题本。
- 掌握度记录与推荐策略。

验收：完成一次练习后，能产生判分结果、错题记录和掌握度变化。

### P7. AI 生成与导出

目标：在真实题库和学习数据足够后，再启用 AI 出题。

交付：

- 单题生成实验，不自动入库。
- 趋势/频率/知识点驱动的批量出题。
- 生成题审核后入库。
- 导出学生版、答案版、详解版。

验收：管理员可生成、审核、入库并导出题目。

---

## 4. 执行约束

- 单任务制：同一时间只推进一个任务。
- 每任务不超过 4 小时，必须产出可运行结果。
- 阶段验收通过前，不进入下一阶段。
- 阶段完成后更新 `LOG.md`、`PROJECT_STATUS.md`，必要时更新权威文档。
- 真实文档样本、测试脚本和测试结果统一放在 `test/` 下。
- 文档解析代码必须遵守 `V1_LESSONS.md`：Annotation Paradigm、L1 双源证据路由、图片位置元数据、来源可追溯。
- 常规 pytest 使用 mock；live LLM/OCR 验证单独隔离。
- 表结构变更必须同步 Alembic migration。

---

## 5. 推荐首个任务

先做 P0 收口加 P1 的最小入口：

1. 启动后端并验证连接现有 PostgreSQL/Redis/MinIO。
2. 实现“上传 PDF → 写入 MinIO → 创建文档记录 → 创建 Background Task → 查询状态”的最小 API。
3. 生成 `test/pdf` 文件清单，作为解析测试基线的第一版。

暂时不做：前端页面、MCP 工具、完整 AI 生成、多学科一次性铺开。

---

## 6. 变更记录

### 2026-08-11 23:49:10

- P2 文档解析改为 L1 双源：PyMuPDF native + PP-StructureV3 ppsv3。
- canonical L1 由代码按证据生成，LLM 只做行级仲裁。
