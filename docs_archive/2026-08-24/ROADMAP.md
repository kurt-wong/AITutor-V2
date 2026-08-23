# AI Tutor Personal Edition — 开发任务计划

Version: 2.0
Status: 执行基线（Phase 2 设计已冻结，见 PLAN_QUESTION_FAMILY v2.0）
Date: 2026-08-21
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
- OCR/VL 回退链：PP-StructureV3 → MIMO → DeepSeek VL。
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

### P4. 搜索、统计与知识点（Phase 2 设计基线：PLAN_QUESTION_FAMILY v2.0）

目标：建立可靠的数据底座，让题库可检索、知识点可统计、趋势可分析。

> **Phase 2 设计原则（冻结）：**
> - Question = 事实，QuestionInstance = 出现事实，Similarity = 关系，Family = 分析结果
> - Knowledge Point ≠ Family，统计视图（KP × Type × Year）不等于题族
> - Family / Similarity / Embedding 暂不实现，进入 2D 的前置条件是样本量和 golden set，不是固定题数阈值
> - Annotation 不是事实，LLM 输出的标注带 source/confidence/version
> - Phase 2A 验收前，不新增 Family/Similarity/Annotation 表设计变更

#### P4A. 数据底座修复（最高优先级，按序号顺序执行）

> 代码审计（2026-08-21）发现三项额外问题：审核不写回 DB、Worker 把失败当成功、L2 Annotation 被裁剪。
> 这三项与原有 DSD 变更合并为 Phase 2A 六步，按依赖关系排序。Step 1 包含 migration + 最小入库适配，否则 migration 后测试不可能全绿。
> 每项完成后跑 pytest。
> 执行控制：DSH 必须遵守 `Docs/01_Product/PHASE_2A_EXECUTION_PLAN.md`；禁止用文档状态代替命令输出。

| Step | 任务 | 说明 | 验收 |
|---|---|---|---|
| 1 | DSD 变更 + 最小入库适配 | content_hash 列、Instance.document_id 回填（先回填再加约束）、Question 移除 year/school、question_knowledge 新增 mapping_source/review_status、入库逻辑适配、修 test_models | migration 成功；DB 与 DSD §8 一致；Instance document_id 全部非 NULL；pytest 全量通过 |
| 2 | 审核决定写回 DB | 审核通过/驳回更新 questions.status；review_overrides 写回题干/选项/答案；通过 question_instances(document_id, source_question_number) 定位 Question.id | DB 查询验证 status 和内容真实变化；更新的是正确题目 |
| 3 | Worker 失败语义 + L2 完整持久化 | ingestion 异常 → task failed；答案提取失败 → 保留 retry queue；llm_annotated_markdown 保留完整 L2 字段；幂等重跑只清理未审核记录 | 异常时 task failed；答案失败走 retry；L2 完整 |
| 4 | 答案重试关联修正 | 改用 document_id + question_instances 精确关联 | 同文档多道空答案题各自正确更新 |
| 5 | 精确去重 content_hash | hash 覆盖题干+选项+题型；hash 相同但答案冲突 → 同一 Question 上生成审核冲突，不创建重复 Question；已有数据回填 | 同 PDF 两次上传只创建 Instance；答案冲突不产生重复 Question |
| 6 | 知识点映射落库 | knowledge_points → knowledge_nodes 映射 → question_knowledge 写入；低置信度进审核；综合题子题级映射 | DB 查询验证题目关联到知识树节点 |

**Phase 2A 总验收：** pytest 全量通过；同 PDF 两次上传只创建 Instance；知识点映射到知识树；审核后 status 真实变化；Worker 异常标 failed；答案失败走 retry；L2 完整持久化；答案冲突不产生重复 Question。

#### P4B. 基础统计与搜索

| # | 任务 | 说明 |
|---|---|---|
| 1 | 知识点 × 题型 × 年份统计 API | 基于 question_instances + question_knowledge + questions 的聚合查询 |
| 2 | 条件搜索 | 按学科/题型/知识点/年份/学校筛选题目 |
| 3 | 高频知识点排行 | 哪些知识点出现最多？按年份看趋势 |

#### P4C. Annotation 原始积累

| # | 任务 | 说明 |
|---|---|---|
| 1 | Structure Signature 采集 | 在现有 annotation prompt 里为数学/物理/化学增加可选 structure_signature 字段。只存到 llm_annotated_markdown JSON，不做 DB migration。 |
| 2 | Annotation 版本标记 | 在 llm_annotated_markdown 中记录 prompt 版本号。 |

#### P4D. Similarity / Family 研究（前置条件满足后启动）

**启动前置条件：**
- 目标学科有足够样本量
- 建立了可验证的 Golden Dataset（每个结构化科目 50-100 条边界案例，owner + AI 辅助建立）
- Structure Signature raw 数据有足够分布

| # | 任务 | 说明 |
|---|---|---|
| 1 | Structure Signature 分布分析 | 从 raw 数据中统计 object/task/method 变体分布 |
| 2 | Normalizer 实现 | 同义词映射 + LLM 兜底 |
| 3 | Family 自动聚类 | 归一化后 object+task 相同的题归入同一 Family |
| 4 | question_families 表 | 到这一步才建表 |
| 5 | Similarity Engine | Embedding 召回 + 结构比较 |
| 6 | Family × Year 频率统计 | 基于 Instance 聚合 |

**暂不实现：** question_families 表、question_similarity 表、独立 question_annotations 表、Embedding 索引。

#### P4E. 真实题库入库验收（当前最高优先级）

> **背景（2026-08-22 全量审查结论）**：Phase 2A/2B/2C 的能力已全部实现并通过测试，
> 但主库真实题目为 0 条 —— 所有验证都建立在集成测试的临时数据上（测试后回滚/清理）。
> 搜索、统计、知识点映射、Structure Signature 目前是「能力已具备，但没有真实题库可服务」。
> P4E 的目标是把数据底座变成可用的题库资产，为 Phase 3（错题）和 Phase 4（练习/掌握度）建立真实数据前提。

| # | 任务 | 说明 | 验收标准 |
|---|---|---|---|
| 1 | 真实题库入库验收 | 用现有 PDF 集在真实 PostgreSQL 上跑完整流程（PDF→OCR→LLM 标注→ingestion），题目、配图、答案、知识点映射真正持久化 | 主库出现可查询的 approved 题目；`GET /api/admin/statistics` 返回非空、可解释的结果；不是「测试通过」而是「主库有数据」 |
| 2 | 管理端审核闭环 | 在真实题目上使用审核接口：通过、驳回、修改题干/选项/答案、处理答案冲突、修正知识点映射 | 审核后 `SELECT status, stem, answer FROM questions` 真实变化；冲突题目进入 reviewing 且 review_reason 有详情 |
| 3 | 题库质量 baseline | 生成可复现的题库质量快照：题目数、答案准确率、知识映射 pending 数、content_hash 冲突数、配图完整率 | baseline 脚本可重复执行，输出保存到 `test/results/`；后续每次改管线可对比，避免「测试绿但数据坏」 |
| 4 | 前端页面搭建 | 搭建管理端 + 学生端前端页面，让 owner 能从页面用两种身份对后端业务流程质量做判定 | 页面能展示真实题库数据（搜索/统计/题目详情）、执行审核、查看质量指标 |

**执行顺序**：1 → 2 → 3 → 4。P4E 完成前，Phase 3/4/7 与 P4D 不启动。

**Phase 3/4 设计原则（P4E 完成后讨论）**：
- Phase 3 学生错题：先做「切分 + 识别 + 新建草稿题 + 管理员确认」，题库匹配随后补（匹配依赖真实题库）
- Phase 4 练习与掌握度：优先客观题（答案可确定性判分），主观题判分后续；知识映射和错题本必须有真实数据支撑，否则掌握度空转
- Phase 7 AI 生成：依赖真实统计趋势和样本量，题库无真实量级前不启动

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

### 2026-08-21

- 版本升至 2.0。
- P4 重写为 Phase 2 四阶段（2A 数据底座 / 2B 统计搜索 / 2C Annotation 积累 / 2D Similarity/Family 研究）。
- Phase 2 设计基线冻结为 PLAN_QUESTION_FAMILY v2.0。
- Phase 2A 明确五项 P0：知识映射落库、Question/Instance 字段修正、Instance 关联 document_id、content_hash、occurrence_count 派生。
- Family/Similarity/Embedding 暂不实现。
