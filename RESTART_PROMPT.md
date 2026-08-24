# AI Tutor Personal Edition — RESTART_PROMPT

Version: 6.15
Status: 重启恢复指引（9 科答案基线 mismatch=0、严格通过率 187/213 (88%)；英语 Q46 已标记需人工审核；T0-2 三个 API key 实测仍未轮换（待用户控制台操作）；下一步：重灌二中数学恢复 e2e 测试 + 处理 pytest stats 干净库冲突 + 物理重跑）
Date: 2026-08-25

---

## 1. 用途

本文件用于 Codex/Claude 在重启后快速恢复工作状态。

任何 Agent 进入项目后，应先读本文件，再按需读取 `rules.md`、`PROJECT_STATUS.md`、`LOG.md`、`bugs.md` 和相关权威文档。

---

## 2. 项目目标

项目是一个家庭自用、面向高中学生的题库管理与智能辅导平台。

核心目标：

1. 管理员批量上传教师版 PDF/DOCX，系统自动提取题目、配图、答案、详解和元数据。
2. 题库支持题型频次、年份趋势、知识点占比、难度分布等统计分析。
3. AI 根据历史趋势、频率和占比生成新题，经管理员审核后入库，并支持导出学生版和答案详解版。
4. 学生上传 JPG 错题，系统自动切分、识别、匹配或新建，形成错题本。
5. 系统根据错题和知识点掌握度生成针对性练习，自动判分并记录学习过程。

---

## 3. 系统现状

当前阶段：**Phase 2A 总验收通过；Phase 2B/2C 已实现；入库管线 P0-A/P0-B/P0-C/P0-G 止血补丁完成；答案验证器独立化完成（以原始 PDF 为主判据）；9 科答案基线 mismatch=0、严格通过率 76%；英语 P0-A 材料合并 11/11 验证通过；OCR 链加固完成（PPS 排队 + paddle 10010 熔断 + mimo 短超时降级）；架构方向决策：先量化再止血再单科原型再逐科推广（2026-08-25，版本 6.10）。**

> **全量回归确认（2026-08-22 00:39）**：修复收集错误（`run_pipeline` 恢复至 pipeline.py，4 个引用方零改动）+ 4 项测试与生产代码不同步（processor 已迁移 `run_simple_pipeline`，patch 目标同步）+ DB 历史题清理（9 道英语卷题，stats 测试恢复干净库前提）+ 沙箱 temp 权限根治（`backend/tests/conftest.py` 固定 temp 根到工作区 `tmp/pytest`，`processor._download_pdf` 改工作区 tmp，新增 `test_temp_root.py`）。全量 pytest（用户本机，注入 backend/.env DATABASE_URL）**549 passed，0 failed，9 warnings**（546 → 549，+3 temp 根测试；收集错误与 temp 权限间歇失败均已消除）。
> **已知记录口径修正**：此前 LOG/PROJECT_STATUS 中 534/537/539/542/546 等数字与当前工作树不一致（processor 迁移后测试未同步、收集错误被隐藏），本次全量 549 passed 为权威基线。
> Task 2.5 管线门禁已通过。P0 入库流程已实现并通过 30 份文档验证。
> 知识树 333 节点已入库。Phase 2A 设计基线已冻结（PLAN_QUESTION_FAMILY v2.0）。
> Phase 2A Step 1 ✅ migration 已执行（alembic current=20260821_0005）。
> Phase 2A 总验收通过：Step 0-6 全部验收；三个修复项已验证（跨文档清理、冲突详情持久化、LLM 兜底降级）；专项测试 96 项。
> **Phase 2B ✅ 已实现（两轮审查修复后）**：条件搜索（含 confidence 精确匹配）+ 统计聚合（含 kp_year_trend 知识点×年份出现频率、start_year/end_year 全局过滤）+ 高频知识点排行 + 题目详情（含配图 + occurrence_count 派生，SQL 下沉 Repository 层）；27 项测试。
> **Phase 2C ✅ 已实现（两轮审查修复后）**：Structure Signature 采集（object/task/method/condition 四层，序列化附带 source/confidence/annotation_version 元数据）+ Annotation 版本标记（`ANNOTATION_PROMPT_VERSION`）；10 项测试。
> 含 Phase 2B/2C 两轮修复后全量 pytest 540 passed（用户本机预期；沙箱 537 passed + 3 项 temp 权限）。
> 高优先级遗留修复完成：answer_retry_worker 提取失败按 max_retries 恢复 pending/failed；综合题合并保留 structure_signature；全量 pytest 546 passed。
> **入库管线 P0/P1 修复完成（2026-08-22）**：5 个 P0（配图属性名、题型 get-or-create、难度必填 prompt、膨胀检测、材料独立）+ 1 个 P1（子题答案 L2 层提取），共 40 项测试。e2e 可复现验收：数学 PDF 23 题题型/难度分布精确匹配（`test_e2e_ingestion_verification.py`，9 项，直接查 PostgreSQL）。跨学科题型行为固化（`QuestionType.code` 全局唯一，6 项）。P0 审计结论已整合到 `bugs.md`。
> 下一步：Phase 2D Similarity/Family 研究（前置条件：样本量 + golden set + Structure Signature raw 分布）。

- Math: ✅ 管线通过（21 题全部正确）
- Physics: ✅ 管线通过
- English: ✅ 管线通过
- 新科目：化学/生物/语文 L1 fixture + paper structure manifest 已落地
- **入库流程**：✅ 已实现（answer_extractor + ingestion + processor/worker 集成）
- **三份文档持久化**：✅ native_markdown + ocr_markdown + llm_annotated_markdown
- **答案提取重试**：✅ 重试表 + retry worker + API
- **去重**：✅ 精确匹配
- **答案准确性**：✅ 历史 40 题选择题 100% 正确

**待处理**：
1. Phase 2D Similarity/Family 研究（前置条件：样本量 + golden set + Structure Signature raw 分布）

已完成：
1. Native L1 与 PP L1 行号编码分离（`P1L001` vs `N1L001`）
2. 知识树种子数据入库（333 节点，9 科，4 级深度，292 父子关系）
3. Phase 2 设计冻结（PLAN_QUESTION_FAMILY v2.0，经 MiMo/ChatGPT/Codex 三方对齐）
4. Phase 2A Step 0：真实回填演练验收通过（pytest 迁移演练 + 脚本版）
5. Phase 2A Step 1：DSD 变更 + 最小入库适配（migration 20260821_0003）
6. Phase 2A Step 2：审核决定写回 DB
7. Phase 2A Step 3：Worker 失败语义 + L2 完整持久化 + 幂等重跑清理
8. Phase 2A Step 4：答案重试关联修正
9. Phase 2A Step 5：精确去重 content_hash（migration 20260821_0005）
10. Phase 2A Step 6：知识点映射落库
11. **Phase 2A 总验收通过**（总验收 SQL 4/4 OK）
12. **Phase 2B 基础统计与搜索已实现**（条件搜索含 confidence + 统计聚合含 kp_year_trend + 高频知识点排行 + 详情含配图，27 项测试）
13. **Phase 2C Annotation 原始积累已实现**（Structure Signature 四层 + 元数据 + Annotation 版本标记，10 项测试）

---

## 4. 文档地图

| 文档 | 用途 |
|---|---|
| `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md` | 真实需求与方案基线 |
| `Docs/00_Requirements/DICTIONARY.md` | 字段、功能、状态字典 |
| `Docs/01_Product/PRD.md` | 产品需求 |
| `Docs/01_Product/TASK.md` | 任务执行规范 |
| `Docs/01_Product/PLAN_QUESTION_FAMILY.md` | **Phase 2 设计基线**（题目体系/题族/相似度/统计） |
| `Docs/01_Product/ROADMAP.md` | 开发任务计划（Phase 2A/2B/2C/2D） |
| `Docs/02_Architecture/SAD.md` | 系统架构 |
| `Docs/02_Architecture/MIS.md` | MCP 工具规范，Agent 接口层 |
| `Docs/02_Architecture/ACS.md` | API 合约 |
| `Docs/02_Architecture/PIPELINE.md` | 文档入库管线 |
| `Docs/05_Development/V1_LESSONS.md` | V1 经验教训与强制约束 |
| `Docs/02_Architecture/PADDLEOCR_API.md` | PaddleOCR-VL / PP-StructureV3 API 资料 |
| `Docs/01_Product/T3_IMPLEMENTATION.md` | T3 Annotation Paradigm 实施基线 |
| `Docs/02_Architecture/UI.md` | 前端页面规范 |
| `Docs/03_Data/DSD.md` | 数据库结构 |
| `backend/app/domains/document/answer_extractor.py` | LLM 答案提取模块 |
| `backend/app/domains/document/ingestion.py` | 入库服务 |
| `test/ocr_markdown/` | 30 份 OCR markdown（答案提取验证基线） |
| `Docs/Design.md` | 前端视觉设计风格 |
| `PROJECT_STATUS.md` | 当前状态和下一步 |
| `LOG.md` | 变更历史 |
| `bugs.md` | 已知问题 / Bug 跟踪 |
| `rules.md` | 项目规则和约束 |
| `docs_archive/` | 历史归档文档 |

---

## 5. 待办任务

任务计划以 `Docs/01_Product/ROADMAP.md` 为准；T1-T10 为阶段内细化条目。

### T0. 2026-08-25 当前焦点（按优先级）

1. **PPS/PVL 队列满载** ✅ 已解决：paddle 提交 HTTP 200 + jobId 返回；英语重跑 PP-StructureV3 OCR 2.8s 直接成功。客户端排队 + 熔断 + 降级机制保留（防御性）。
2. **轮换泄露 API key（安全）**：dacad48 提交把 MIMO/DeepSeek/PaddleOCR 密钥写进 git 历史，92a8c07 已从工作树移除硬编码。**必须轮换三个 key**，更新 backend/.env（.gitignore 中）。待用户在各平台控制台执行。
3. **英语 stem 位置/选项归属** ✅ 已完成（2026-08-25 02:30）：位置 7/11 → 11/11、选项 7/11 → 11/11、Q46 作文缺库解决（DB 11/11）、严格通过 10/11。根因：semantic_anchor is_short_answer 忽略 end_marker（语法填空行内编号）+ 截断边界按题号大小而非文档顺序（OCR 噪声 "48、" 截空 Q46）。详见 LOG.md 2026-08-25 02:30。
4. **provider_used 落盘** ✅ 已完成（2026-08-25 03:30）：`PipelineResult` 新增 ocr_provider_used/ocr_model_used 写入 task result。实时验证：英语重跑 ocr_provider_used=paddleocr、ocr_model_used=PP-StructureV3。
5. **Phase 2D Similarity/Family** ⏸ 前置条件未满足（评估完成，2026-08-25 03:30）：样本 191 题（数学 5、语文 7 过少）、golden 仅 3 科、Structure Signature 覆盖率 20%（限数学/物理/化学）。需先扩充样本 + 补齐 9 科签名 + 建立相似度 golden。

### T1. 建立真实文档测试集

- 已有 30 份教师版 PDF 位于 `test/pdf/`，继续补充 DOCX/JPG 等样本。
- 覆盖数学、物理、化学、英语、语文、生物、政治。
- 覆盖文末答案和题后答案。
- 覆盖配图题、公式题、表格题、复合题。
- 建立字段级准确率统计。

### T2. 搭建后端骨架

- FastAPI 项目结构。
- Application Service、Domain Service、Repository 骨架。
- 统一 Background Task。
- Domain Event 发布与消费。
- PostgreSQL、MinIO、Redis 本地可运行。
- LLM Gateway 基础路由。

状态：已完成；FastAPI 骨架、数据模型、Alembic 初始迁移、Repository、Domain Service、Application Service、统一 Task/Domain Event、LLM Gateway 基础路由、MinIO 客户端和依赖健康检查均已就绪。

### T3. 实现文档解析管线

- 按 `Docs/02_Architecture/PIPELINE.md` 实现。
- 优先验证 PDF/DOCX 到 Question Aggregate 的结构化提取。
- 输出置信度并支持低置信度审核。

状态：**Phase 0、Phase 1、Task 2.5 均已通过**。simple_pipeline 为核心实验路径。

### T3.5 实现入库流程（P0）

- LLM 答案提取：`answer_extractor.py`，从 OCR markdown 提取题号→答案映射。
- 入库服务：`ingestion.py`，管线结果 + LLM 答案 → DB。
- 管线集成：`processor.py` + `document_worker.py`，管线成功后自动调用入库。
- 30 份文档验证通过（9 学科、约 800 题、LLM 提取准确率 100%）。
- 对抗性审查发现 6 个问题，待修复后验收。

状态：**已实现，三科重验收通过，答案准确性已验证**。

验收结果：
1. ✅ Alembic migration 已执行
2. ✅ 9 份 PDF 全流程验收（171 题，153 题 approved）
3. ✅ 三份文档持久化
4. ✅ 去重（精确匹配）
5. ✅ 重试队列
6. ✅ review_reason 分类
7. ✅ 三科重验收（地理 27 题、数学 21 题、历史 43 题）
8. ✅ 历史选择题答案准确性验证（40 题 100%）

### T4. 实现题库与审核

- 题目 CRUD。
- 低置信度审核队列。
- 重复题合并。
- Question Instance 保留来源信息。

### T5. 实现搜索、统计与知识

- 条件搜索。
- 去重。
- embedding。
- 知识点映射。
- 题型频次、年份趋势、知识点占比、难度分布。
- 学生学习趋势。

### T6. 实现学生错题

- JPG 多题自动切分。
- 识别、匹配题库或新建。
- 管理员确认后进入错题本。
- 错题本列表、详情、重练、标记已掌握。

### T7. 实现练习与掌握度

- 自动判分。
- 保存题目快照、答案、对错、用时、知识点。
- 答错自动进入错题本。
- 根据掌握度调整出题。

### T8. 实现 AI 生成

- Phase 2.5：先做简单单题生成实验，输入知识点、题型、难度，输出一题、答案、解析，不自动入库。
- Phase 5：实现趋势/频率/占比驱动的完整 AI 出题。
- 生成题审核后入库，标记为生成题。
- 导出学生版，以及答案和详解独立版。

### T9. 实现前端

- 管理员后台和学生端。
- 按 `Docs/02_Architecture/UI.md` 和 `Docs/Design.md` 实现。
- 先支持电脑浏览器。

状态：解析审核台与结果展示已完成；学生端为轻量外壳，后续按 Phase 3 继续。

### T10. Docker/NAS 部署

- Docker Compose 编排。
- PostgreSQL、MinIO、Redis、backend、worker、frontend。
- API Key 通过 `.env` 管理。

### 阶段顺序

```text
Phase 0 基础工程
Phase 1 题库核心
Phase 2 搜索/统计/知识
Phase 2.5 AI 生成实验
Phase 3 学生错题
Phase 4 练习与推荐
Phase 5 AI 生成与导出
```

---

## 6. 恢复流程

Codex/Claude 启动后建议按以下顺序恢复：

1. 读 `RESTART_PROMPT.md`。
2. 读 `rules.md`，确认不可违反规则。
3. 读 `PROJECT_STATUS.md` 和 `LOG.md`，确认当前状态。
4. 根据任务类型读对应权威文档。
5. 修改前确认当前任务和完成标准，不擅自扩大范围。

### 6.1 V1 教训固化要点

动文档解析相关代码前必须读 `Docs/05_Development/V1_LESSONS.md`。最短红线：

1. LLM 只输出行号/元数据，不输出题目原文。
2. LLM 行号是粗定位；代码必须锚点校正后切片。
3. L1 双源证据路由：PyMuPDF native 与 PP-StructureV3 并存，canonical L1 按行选择，LLM 只做行级仲裁。
4. 配图必须有 `page/bbox/placement/source`，禁止猜图。
5. 教师版答案/详解优先，LLM 生成只兜底并标记来源。
6. 知识树为空时不得静默跳过映射。
7. Schema 变更必须有 Alembic migration。
8. 常规 pytest mock，live 测试隔离。
9. 验证前清理旧进程，不用 `--reload`。

### 6.2 重启后验证记录（2026-08-11）

用户在本机执行 `python test/scripts/llm_smoke_test.py --live` 的结果：

- mock：passed，1ms
- deepseek：passed，12s，`json_valid=true`
- mimo：**passed**，134s，`json_valid=true`（`response_format: json_object` 生效）
- deepseek_vl：**passed**，38s，`json_valid=true`

**Phase 0 验收通过。**

### 6.3 后续再重启时的验证清单

```powershell
python test/scripts/llm_smoke_test.py --live
```

若全部 passed，直接进入 Phase 1。

若 `smoke_report.json` 中 deepseek/mimo/deepseek_vl 全部 passed，再更新 `PROJECT_STATUS.md` 并进入 Phase 1。

当前 Task 2.5 验收清单（需用户本机联网执行）：

```powershell
python test/scripts/ocr_smoke.py --provider all
python test/scripts/run_live_validation.py --with-ocr --runs 2
python test/scripts/adversarial_check_live_validation.py --require-live-pp
```

---

## 7. 更新记录

### 2026-08-10 21:56:55

- 创建本文件，作为 Codex/Claude 重启恢复入口。

### 2026-08-10 22:10:28

- 更新架构定位：MCP 仅作为 Agent 接口层。
- 更新核心契约：Question Aggregate、Background Task、Domain Event。
- 更新阶段路线和待办任务顺序。

### 2026-08-10 22:17:19

- 新增 `DICTIONARY.md`，作为字段、功能和状态枚举的统一术语来源。

### 2026-08-10 22:41:06

- 初始化 Phase 0 项目骨架。
- 新增后端、前端、Docker Compose、环境变量和 README。
- 后端与 Compose 配置验证通过；前端依赖安装待环境允许后继续。

### 2026-08-10 23:07:14

- 扩展 Phase 0 后端分层骨架。
- 新增 DSD 数据模型、Alembic 初始迁移、Repository/Domain Service/Application Service、统一 Task/Domain Event 和 LLM Gateway。
- 后端测试与 Alembic offline SQL 验证通过；Docker API 权限不足，真实迁移待后续执行。

### 2026-08-10 23:30:50

- 新增 `scripts/allow-codex-docker.ps1`，用于持久授权 Codex 沙箱访问 Docker Desktop 与 localhost。
- 已同步更新项目状态和变更日志；待重启 Docker Desktop 与 Codex 后验证 Docker CLI 与数据库端口连通性。

### 2026-08-10 23:54:42

- 复用现有 aitutor-postgres(15432)/aitutor-redis(16379)/aitutor-minio(9000)，移除误建的新容器。
- 在现有 PostgreSQL 中新建 aitutors 库执行 Alembic 初始迁移，旧 ai_tutor 库未改动。
- 确认 embedding 使用本地 Ollama qwen3-embedding:4b（2560 维）；因 HNSW 上限 2000 维，初始迁移不建向量索引。
- docker-compose.yml 改用 pgvector/pgvector:pg16，并新增 EMBEDDING_PROVIDER/MODEL/DIMENSION 配置。

### 2026-08-11 00:08:00

- 新增 `Docs/01_Product/ROADMAP.md`，作为后续开发任务的严格执行基线。
- 新增 `Docs/02_Architecture/PADDLEOCR_API.md`，保存 PaddleOCR-VL-1.6 与 PP-StructureV3 API 示例资料。
- 测试数据、测试脚本和测试结果统一放 `test/`，已写入 `rules.md` 与 `TASK.md`。

### 2026-08-11 00:30:16

- 更新系统现状为 P0/P1 已完成。
- 新增 MinIO 客户端、依赖健康检查、文档上传/任务 API、PDF 清单与文档校验脚本状态。
- T2 标记完成，后续进入 T3 文档解析管线。

### 2026-08-11 00:45:41

- 更新系统现状为 P2 文档解析验证代码闭环已实现。
- 新增 PP-StructureV3 客户端、OCR/VL 回退链、LLM Question Aggregate 提取、test 批量解析/准确率脚本和 mock fixtures。
- 后续任务：建立 30 份 PDF 字段级标注并完成 live API 联调。

### 2026-08-11 07:07:42

- 新增 `Docs/05_Development/V1_LESSONS.md`，固化 V1 解析/配图/来源/审核/测试/部署教训。
- 更新 `rules.md`、`TASK.md`、`PIPELINE.md`、`SAD.md`、`ROADMAP.md`、`DICTIONARY.md`、`DSD.md`，明确后续 T3 必须按行号标注、Native PDF 优先和图片位置元数据执行。

### 2026-08-11 07:19:47

- 补充“LLM 行号不准”约束：LLM 行号仅为粗定位，必须经代码锚点校正后才能切片。
- 新增 `llm_anchor/corrected_anchor/anchor_status` 契约，禁止未校正行号直接入库。

### 2026-08-11 07:29:33

- 按 V1 代码/日志差距分析补充 14 条教训到 `V1_LESSONS.md`。
- 明确复合题 section 切分、quality gate 部分保存、单行选项、L2 行号透传、OCR 题号换行、文档级图片去重、答案区不截断、Solution draft 等后续 T3/P3 必须遵守。

### 2026-08-11 07:33:00

- 配置 DeepSeek：`DEEPSEEK_BASE_URL=https://api.deepseek.com`、`DEEPSEEK_MODEL=deepseek-v4-flash`。
- `LLM_GATEWAY_MODE` 保持 `mock`；后续需要 live 联调时再切换。

### 2026-08-11 07:35:00

- 配置 MIMO：`MIMO_BASE_URL=https://api.xiaomimimo.com/v1`、`MIMO_MODEL=mimo-v2.5`。
- `LLM_GATEWAY_MODE` 保持 `mock`；后续需要 live 联调时再切换。

### 2026-08-11 07:44:54

- 配置 Qwen VL base URL 与模型；API Key 仅写入 `backend/.env`。
- DeepSeek/MIMO/Qwen 参数已齐备，`LLM_GATEWAY_MODE` 保持 `mock`。

### 2026-08-11 09:30:00

- 更新版本至 1.0。
- 更新系统现状为 T3 Phase 0 完成，准备进入 Phase 1。
- 新增 Phase 0 完成详情：L1/L2 Schema、LLM fixture + Golden Set、LLM Provider Smoke Test、L1 后处理规则。
- 更新 T3 任务状态：Phase 0 已完成，Phase 1 待执行。

### 2026-08-11 09:30:00

- 新增 `T3_IMPLEMENTATION.md`（v1.0），T3 Annotation Paradigm 实施的执行基线。
- 冻结 `question_extractor.py` 和 `parser.py` LLM 路径。
- 更新 `V1_LESSONS.md` 至 1.3：图片多对多语义。
- 更新 `DSD.md` 至 4.5：L1/L2 中间态说明。
- 按 T3_IMPLEMENTATION.md 建立 Phase 0-3 四阶段执行计划。

### 2026-08-11 14:06:37

- 版本升至 1.2，更新为 Live 部分验证状态。
- 用户本机 live：DeepSeek passed；MIMO 61s 超时；Qwen JSON 解析失败。
- 沙箱 curl 仍返回 `HTTP:000` / `WinError 10013`，属于沙箱外网限制，不是真实本机网络问题。
- 记录后续再重启时的验证清单，恢复流程必须先检查 `test/scripts/smoke_report.json`。

### 2026-08-11 16:24:02

- 补齐 English L1 fixture 详解区（P1L059-P1L069），English Golden Set 更新至 v3.1。
- 10 题 `explanation_line_ids` 与 `expected_anchor.explanation_line_ids` 均非空，`explanation_source` 改为 `document_inline_explanation`。
- 同步状态：后端 41 + Smoke 13 = 54，Phase 0 验收项全部闭合。

### 2026-08-11 23:49:10

- 更新至 1.6：T3 Phase 1 改为架构重构中，不再标记验收通过。
- L1 架构调整为 PyMuPDF native + PP-StructureV3 双源，canonical L1 按证据生成。

### 2026-08-12 Phase 1 条件通过

- Phase 1 状态更新为"条件通过，待最终验收"。
- 真实 PP OCR + DeepSeek LLM 端到端验证通过：dual_source_lines=7，LLM 仲裁 125 行审计 7 冲突。
- 待修复：eval 脚本 options_line_ids 比较逻辑（sorted(dict) 只比较 key）、explanation 明确移出 Phase 1 验收范围。
- explanation_line_ids：golden 8 题均为空（explanation_source: llm_fallback），已明确移出 Phase 1 验收范围，属 Phase 2+ 范畴。

### 2026-08-13 19:26:10

- Phase 1 状态更新为"未最终验收"：mock/golden 子集通过，live-pp 全卷待复审。
- 后端测试更新为 136 passed；Mock eval 8/8 100%。
- Live-pp（2026-08-13 19:17 结果）：golden 8/8 字段 100%，全卷 21 题、answer_matched=14、blocked=7、quality high=10。
- 同步更新 PROJECT_STATUS.md 与 adversarial_review_phase1.md。

### 2026-08-13 19:44:35

- 版本升至 1.7。
- Phase 1 复审修复完成：答案表支持括号答案、题号正则排除 LaTeX 续行、L1 后处理支持行内全角括号题号切分。
- 后端测试更新为 142 passed；Mock eval 8/8 100%。
- 沙箱外网仍受限，live-pp 未重跑；后续先在本机执行 `python test/scripts/run_phase1_eval.py --live-pp`，再按全卷结果复审。

### 2026-08-13 20:33:00

- 版本升至 1.8。
- 用户本机 live-pp 重跑完成：21 题、golden answer/answer_line_ids 8/8，但 question_type=6/8；根因为 LLM 返回中文 `填空题`。
- 修复题型归一化：中文题型映射 canonical 枚举，prompt 明确 canonical 题型。
- 后端测试更新为 143 passed；同一 live-pp 结果复算 golden 8 项 100%。
- 最终验收仍需用新代码在本机执行 `python test/scripts/run_phase1_eval.py --live-pp`。

### 2026-08-13 21:50:57

- 版本升至 1.9。
- 用户用新代码重跑 live-pp：3 次运行取最差后 `PASS`，golden 8/8 全字段 100%，line ID errors=0。
- 对抗性审查结论：Phase 1 按 golden 8 题纵向闭环验收通过；全卷 7 blocked / 5 answer_empty 均带低置信度标记，作为 Phase 2/3 审核边界登记。

### 2026-08-13 22:15:00

- 版本升至 2.0。
- Phase 1 基础设施加固完成：`run_phase1_eval.py` 新增全卷验收阈值 `THRESHOLDS_FULL卷`（min_answer_matched=16、max_blocked=7、min_quality_high=14、max_missing_anchors=10）；`THRESHOLDS_SMOKE` 补充 `stem_line_ids`、`options_line_ids`、`answer_line_ids` 三项；`HTTPLLMProvider` 新增指数退避重试（max_retries=2、retry_base_delay=1.0s）。
- 后端测试 143 passed，全部通过。

### 2026-08-16 21:16:25

- 版本升至 2.1。
- 当前实验主路径为 `simple_pipeline`；Task 2.5 保持 NOT_ACCEPTED，禁止进入 Step 2。
- PDF 视觉 OCR fallback 已修复为逐页 PNG；Paddle 队列满会退避重试；batch 已支持 per-PDF 异常保护与增量 summary。
- 后端 **319 passed**；下一步用户本机执行 `python test/scripts/ocr_smoke.py --provider all` 与 `python test/scripts/simple_pipeline_batch.py --limit 10 --runs 2`。

### 2026-08-17 13:20:32

- 语义锚点落地：`stem_markers` 只作定位计划，最终内容从 PP/native 原文切片；新增 `semantic_anchor.py`、题号校验和 `llm_annotation` 诊断块。
- 后端 **325 passed**；新增 9 科每科一份 PDF 验证脚本 `run_9subject_validation.py`；Task 2.5 仍 NOT_ACCEPTED。

### 2026-08-17 23:42:03

- 综合题透传、retry hint 与数学/化学验证完成；后端 **328 passed**；OCR 学科路由对照测试完成。
- 化学采用 PaddleOCR-VL、文本密集科目采用 PP-StructureV3 的方案已写入 V1_LESSONS 3.30。

### 2026-08-18 00:20:00

- 解析审核前端闭环完成：审核接口支持 `review_overrides`，前端支持逐题审核、修正、筛选和导出审核 JSON。
- 后端 **332 passed**；新增 `test/scripts/check_review_ui.py`。

### 2026-08-18 00:45:00

- 解析结果显示页增强完成：默认显示效果模式，KaTeX 渲染公式，按 `question_images` 展示配图。

### 2026-08-18 00:46:00

- 版本升至 2.2。
- 前端按 `Docs/Design.md` 完成视觉优化：品牌导航、毛玻璃 `result-toolbar`、设计 token、学生端轻量仪表盘、Inter fallback。
- 新增 `test/scripts/check_review_ui_responsive.py`；`npm run build` 通过，桌面与 390px 移动视口 Playwright 验证通过。

### 2026-08-18 18:48:33

- 版本升至 2.3。
- 同步 9 科最终验证、OCR 学科路由与地理综合题结论到根目录权威文档。
- 地理状态改为 ✅：16/16 综合题，Q19 图片选项与 Q23-Q25 试卷缺失为预期丢弃，实际丢弃率 0%。
- 后端恢复基线实测 **338 passed**；移除 `Docs/` 下重复的 PROJECT_STATUS/LOG/RESTART_PROMPT。

### 2026-08-20 07:30:00

- 版本升至 2.5。
- 语文/化学/生物 paper structure manifest 已落地（基于人工校对结构）。
- `paper_structure.py` 恢复为完整 groups-level 验证实现。
- 试卷结构门禁测试 8/8 全部通过。
- 后端全量 378 passed；3 个失败均为 DSH 沙箱 temp 目录权限问题（WinError 5），非代码 bug。
- **Task 2.5 三科门禁验收通过**：复现性归一化完成，报告重建 PASS，adversarial_check --require-live-pp 通过。
- Task 2.5 状态从 NOT_ACCEPTED 更新为**通过**。

### 2026-08-20 18:00:00

- 版本升至 2.7。
- P0 入库流程实现：answer_extractor.py（LLM 答案提取）+ ingestion.py（入库服务）+ processor/worker 集成。
- LLM 答案提取方案验证：30 份 OCR markdown、9 学科、约 800 题，准确率 100%。
- QuestionImage 补齐 page_no/bbox/placement/source/figure_id；Question 补齐 is_composite/sub_questions。
- Alembic migration 生成；单元测试 18 passed；后端全量 395 passed。
- 对抗性审查（第二轮）发现 6 个问题（2 P0 + 3 P1 + 1 P2），待修复。

### 2026-08-20 22:00:00

- 版本升至 2.9。
- 第二轮修复：选择题区域搜索、题号正则扩展、native_markdown 写入、字段名修正、重试机制、LLM 相似判断（禁用）。
- 第三轮审查：所有原始问题已修复，2 个低优先级遗留，1 个 P1 TODO。
- 新增文件：retry_repository.py、answer_retry_worker.py、answer_extraction_retries 表。
- 新增 API：GET /answer-retries、POST /answer-retries/{id}/retry。
- PipelineResult 新增 native_l1_document 字段。
- 后端全量 398 passed。
- **准备进入系统功能验收**。

### 2026-08-20 20:30:00

- 版本升至 3.4。
- answer_matcher 修复：主观题（short_answer）跳过 `_is_suspicious_llm_answer_text` 检查。
- gateway 重写：每个 provider 最多尝试 2 次（间隔5秒），连续失败后切换下一个。
- JSON 截断容错：`_try_fix_truncated_json` 补全截断括号再解析。
- 三科重验收：地理 27 题 ✅、数学 21 题 ✅、历史 43 题 ✅。
- 历史选择题答案准确性验证：40 题 100% 正确。
- 新增待办：Native/PP 行号编码分离（`P1L001` vs `N1L001`）。
- **P0 入库流程修复完成，答案准确性已验证**。

### 2026-08-20 22:40:51

- 版本升至 3.6。
- Native/PP 行号编码分离完成：PP 用 `P1L001`，Native 用 `N1L001`。
- canonical L1 保留 PP 行号体系，native 行号通过 `raw_sources["native_line_id"]` 溯源。
- `pipeline._merge_dual_source()` 改为按 `(page, line_no)` 对齐双源，避免前缀不同后丢失绑定。
- native fixture 同步更新为 `N1L001`；后端全量 407 passed。

### 2026-08-21

- 化学/生物/语文 golden draft 从当前前置待办降级为"暂不生成"。
- 待处理列表重新排序：知识树初始化 → Phase 2 → LLM 相似判断方案。
- 新增 golden 机制说明：区分 live 验收（P0）与冻结回归（golden），明确后续补 golden 的触发条件。
- 知识树种子数据入库完成：333 节点、9 科、4 级深度、292 父子关系。
- 版本升至 3.7。

### 2026-08-21 07:02:01

- 版本升至 4.0。
- Phase 2A Step 0 复核结论更新为「未验收」：现有 Step 0 集成测试只验证当前 schema 插入/约束，未执行 migration upgrade，不能证明旧数据回填；待补真实回填演练。
- 稳定全量命令确认（根目录 + 注入 backend/.env 的 DATABASE_URL）：Step 2 前 453 passed 0 failed（用户本机）。
- Phase 2A Step 2（审核写回 DB）代码已实现：`update_document_review` 同时更新 task.result_json 与 questions 表；定位规则 question_id 优先，否则 question_instances(document_id, source_question_number)；新增 11 项集成测试全部通过；DB 验证脚本 `backend/scripts/step2_db_verify.py` 输出 approved/修正内容证据；含 Step 2 全量 461 passed（沙箱，剩余 2 failed + 1 error 为 temp 权限）。
- Step 2 正式验收待 Step 0/1 前置完成后按 docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md 确认。

### 2026-08-21 07:30:00

- 版本升至 4.1。
- Phase 2A Step 0 验收通过：新增 `backend/scripts/step0_backfill_verify.py` 一次性临时库真实回填演练（upgrade 旧 head → 插入旧数据 → upgrade 20260821_0003 → 验证 → downgrade），8/8 项验证通过（document_id 回填、COALESCE 不清空已有值、year/school 0 残留、唯一索引拒绝重复、downgrade 有损回退）。
- Step 0 集成测试补齐 ingestion 真实路径 2 条（Question 不写 year/school、Instance 写 document_id、精确匹配只建 Instance 且 occurrence_count=COUNT），Step 0 集成 18 passed。
- 含 Step 0+2 全量 pytest 463 passed（沙箱，剩余 2 failed + 1 error 仅 temp 权限）。
- 下一步：Step 1 正式验收 → Step 2 正式验收 → Step 3-6。

### 2026-08-21 08:00:00

- 版本升至 4.2。
- Phase 2A Step 1 正式验收通过（29 条结构测试 + DB 与 DSD §8 一致 SQL 验证 + Step 0 回填证据关联）。
- Phase 2A Step 2 正式验收通过（11 项集成测试重跑，真实 PostgreSQL）。
- Phase 2A Step 3 实现 + 验收通过：Worker 失败语义（ingestion 异常 → task failed + document failed；答案提取失败仍走 retry queue）+ L2 完整持久化（llm_annotated_markdown 保留 knowledge_points/difficulty/score/corrected_anchors/anchor_status/question_type/sub_questions）+ 幂等重跑清理（只清理未审核记录，已审核/已驳回保留）。新增 7 项测试 + `backend/scripts/step3_db_verify.py`（DB 验证 8/8 字段 OK）；旧 worker 测试 mock 同步（12 项通过）。
- 含 Step 0-3 全量 pytest 470 passed（沙箱，剩余 2 failed + 1 error 仅 temp 权限，无回归）。
- 下一步：Step 4 答案重试关联修正 → Step 5 content_hash 去重 → Step 6 知识点映射落库。

### 2026-08-21 08:30:00

- 版本升至 4.3。
- Phase 2A Step 4 实现 + 验收通过：答案重试关联修正（`answer_retry_worker.py` 弃用 `source_document_name + 顺序` 猜测，改用 `question_instances(document_id, source_question_number)` 精确关联；找不到 Instance 记录失败；已有答案不覆盖）。新增 5 项测试 + `backend/scripts/step4_db_verify.py`（Q1→A、Q2→B、Q3→C 精确更新，无串题）。
- 含 Step 0-4 全量 pytest 475 passed（沙箱，剩余 2 failed + 1 error 仅 temp 权限，无回归）。
- 下一步：Step 5 content_hash 去重 → Step 6 知识点映射落库。

### 2026-08-21 09:00:00

- 版本升至 4.4。
- Phase 2A Step 5 实现 + 验收通过：精确去重 content_hash（`content_hash.py` SHA256(规范化题干+选项+题型+子题)；ingestion 按 content_hash 匹配；hash 相同答案不同 → review_reason='answer_conflict' 不建重复 Question；migration 20260821_0005 回填已执行）。新增 10 项测试；DB 验证重复组=0/NULL=0。
- 含 Step 0-5 全量 pytest 485 passed（沙箱，剩余 2 failed + 1 error 仅 temp 权限，无回归）。
- 下一步：Step 6 知识点映射落库。

### 2026-08-21 09:30:00

- 版本升至 4.5。
- Phase 2A Step 6 实现 + 验收通过：知识点映射落库（`KnowledgeService.map_question_to_knowledge`：关键词匹配知识树节点写 question_knowledge；低置信度→pending；空/无命中→回退 {SUBJ}-UNKNOWN + pending；综合题子题级映射）。新增 7 项测试 + `backend/scripts/step6_db_verify.py`（"函数单调性"→MATH-ANA，confidence=1.0/approved）。
- **Phase 2A 总验收通过**：总验收 SQL 4/4 OK；含 Step 0-6 全量 pytest 492 passed（沙箱剩余 2 failed + 1 error 仅 temp 权限，无回归）。
- 下一步：Phase 2B 基础统计与搜索。

### 2026-08-21 10:00:00

- 版本升至 4.6。
- **Phase 2B 基础统计与搜索已实现**：`GET /api/admin/questions` 条件搜索（学科/题型/知识点/年份/学校/难度/来源/状态 + 分页）+ `GET /api/admin/statistics` 统计聚合（total / 题型/知识点/难度分布 / 年份趋势 / 高频知识点降序排行）+ `GET /api/admin/questions/{id}` 详情。新增 12 项测试；含 Phase 2B 全量 pytest 504 passed（沙箱剩余 2 failed + 1 error 仅 temp 权限，无回归）。
- 下一步：Phase 2C Annotation 原始积累（Structure Signature 采集 + Annotation 版本标记）。

### 2026-08-21 10:30:00

- 版本升至 4.7。
- Step 0 真实 Migration Rehearsal 纳入 pytest 验收：新增 `test_phase2a_step0_migration_rehearsal.py`（一次性临时库，7 项断言：document_id 回填、COALESCE、year/school 删除、唯一索引拒绝重复、downgrade 有损回退）。修复 alembic.ini 相对路径 + monkeypatch 替代手动 settings save/restore。
- 全量 pytest（根目录）：**513 passed**，2 failed + 1 error 仅沙箱 temp 权限，无回归（504 → 513，+1 迁移演练）。
- 下一步：Phase 2C Annotation 原始积累。

### 2026-08-21 11:00:00

- 版本升至 4.8。
- **Phase 2C Annotation 原始积累已实现**：Structure Signature 采集（line_annotator prompt 加 structure_signature 可选字段：object/task/method，仅数学/物理/化学）+ Annotation 版本标记（`ANNOTATION_PROMPT_VERSION = "v2.1-structure-v1"` 写入 llm_annotated_markdown）+ `_serialize_l2_for_persistence` 提取为独立函数。新增 12 项测试。
- 含 Phase 2C 后全量 pytest 513 passed（沙箱剩余 2 failed + 1 error 仅 temp 权限，无回归）。
- 下一步：Phase 2D Similarity/Family 研究（前置条件满足后启动）。

### 2026-08-21 11:30:00

- 对抗性审查缺口修复：Step 2 端到端测试增加 task.result_json 同步断言；Step 3 新增 2 项真实 DB 验证（ingestion 异常→task/document failed 落库 + llm_annotated_markdown L2 字段落库）；Step 6 审查确认使用真实 MATH subject。
- 全量 pytest：**515 passed**，2 failed + 1 error 仅沙箱 temp 权限，无回归（513 → 515，+2 真实 DB 验证）。

### 2026-08-21 12:00:00

- 对抗性审查第三轮：发现并修复 `_cleanup_unreviewed_records` 真实 Bug（未删除 question_images/question_knowledge/question_embeddings FK 依赖，重跑有配图/知识点映射的文档时触发 ForeignKeyViolationError）。修复：cleanup 先删子表记录再删 question。新增 `test_rerun_cleanup_handles_fk_dependents`。

### 2026-08-22 09:30:00

- 版本升至 4.9。
- **Phase 2B/2C 对抗性审查缺陷修复（5 项阻断缺陷全部修复）**：
  - Phase 2B：`GET /api/admin/questions` 新增 confidence 筛选（ACS §5.3）；`GET /api/admin/questions/{id}` 返回配图 images + occurrence_count 改为 COUNT(instances) 派生（ACS §5.3）；`statistics()` 新增 kp_year_trend 知识点×年份趋势（ROADMAP P4B #3）；补空结果/多条件组合/统计空结果边界测试。
  - Phase 2C：structure_signature 增加 condition 层（PLAN §4.2 四层）；序列化附加 source='llm'/confidence/annotation_version 元数据（PLAN §5.2）；annotation_version 文档级 + 题目级双重写入。
- 全量 pytest（沙箱）：**534 passed**，2 failed + 1 error 仅沙箱 temp 权限，无回归（516 → 534，+13 修复测试；用户本机预期 537 passed）。
- 下一步：Phase 2D Similarity/Family 研究（前置条件满足后启动）。
- 全量 pytest：**516 passed**，2 failed + 1 error 仅沙箱 temp 权限，无回归（515 → 516，+1 FK 依赖测试）。

### 2026-08-22 00:39:59

- 版本升至 5.3。
- **全量回归确认 + 修复 4 类问题**（最终全量 549 passed，0 failed，9 warnings）：
  1. 收集错误（2 ERROR）：`run_pipeline` 恢复至 pipeline.py（4 个引用方零改动；含 Fix 1 空源语义）。
  2. 测试与生产代码不同步（4 项）：processor 已迁移 `run_simple_pipeline`，`test_phase2_critical_fixes.py` 3 处 patch 目标同步 + `test_processor_progress.py` patch 目标从 pipeline 模块改为 simple_pipeline 模块。
  3. DB 历史题清理（9 道英语卷题）：stats 测试恢复干净库前提（19 passed）。
  4. 沙箱 temp 权限根治：`backend/tests/conftest.py` 固定 temp 根到工作区 `tmp/pytest` + `processor._download_pdf` 改工作区 tmp + 新增 `test_temp_root.py`。
- **记录口径修正**：此前 534/537/539/542/546 等数字与当前工作树不一致（processor 迁移后测试未同步、收集错误被隐藏）；本次 549 passed 为权威基线。
- 下一步：Phase 2D Similarity/Family 研究（前置条件：样本量 + golden set + Structure Signature raw 分布）。

### 2026-08-24 23:30:00

- 文档治理规则补充：状态类文档必须按时间戳顺序在文末追加，禁止直接在文档头更新。
- 同步更新 `rules.md`、`PROJECT_STATUS.md`、`bugs.md`。

### 2026-08-24 23:45:00

- Docs 精简：历史归档移至根目录 `docs_archive/`；文档地图已移除已归档文件并补充归档目录。
- 规划文档内变更记录统一迁移到 `LOG.md`。

### 2026-08-24 23:50:00

- 同步更新代码/测试中的文档路径引用，并将残留 `qwen_vl` 验证说明更新为 `deepseek_vl`。

### 2026-08-24 23:55:00

- `rules.md` 已明确日常文档更新映射，并禁止未经用户确认在 `Docs/` 新增状态类文档。

### 2026-08-25 02:30:00

- 版本升至 6.11。PPS/PVL 队列满载解决（paddle 提交 200，英语重跑 PPS OCR 直接成功）。
- 英语 stem 位置/选项归属修复完成：位置 7/11 → 11/11、选项 7/11 → 11/11、Q46 作文缺库解决（DB 11/11）、严格通过 10/11 (91%)。
- 修复文件：`semantic_anchor.py`（综合题 short_answer 信任 end_marker）、`anchor_corrector.py`（截断边界改文档顺序 + 题号过滤）、`e2e_semantic_report.py`（选项归属改 L2 行号区间）、`test_semantic_anchor.py`（+2 测试）、`test_ocr_vision_pdf_fallback.py`（过期测试修复）。
- 全量 pytest 629 passed，剩余失败均为沙箱 temp ACL 与 DB 数据前置，无回归。
- 下一步：T0-4 provider_used 落盘 → T0-5 Phase 2D 前置评估；轮换泄露 API key 待用户操作。

### 2026-08-25 03:30:00

- 版本升至 6.12。T0-4 provider_used 落盘完成（ocr_provider_used/ocr_model_used 写入 task result，实时验证 paddleocr/PP-StructureV3）。
- T0-5 Phase 2D 前置评估完成：样本 191 题、golden 3 科、签名覆盖率 20%——前置条件未满足，暂缓启动。
- 英语最终验收稳定：位置/选项/stem/材料 11/11、DB 11/11、严格 10/11 (91%)。
- 下一步：轮换泄露 API key（待用户操作）+ 英语答案 free_text 验证改进（可选）+ 扩充样本/补齐 9 科签名 → Phase 2D。

### 2026-08-25 04:30:00

- 版本升至 6.13。验收口径修复：历史 Q38-43 位置误报（`__q_*` 独立题 section artifact）→ 历史 42/43；28 题空名 subject → 政治 + 知识映射 MATH-UNKNOWN → POLI 重映射 + 4 垃圾行清理；ingestion subject 加固（文档优先 + get-or-create 防护）。
- 全科严格通过率 172/197 (87%)。
- 下一步：重跑语文验证 T0-3 普适性 → 复算 9 科基线 → 英语 Q46 free_text 验证改进。

### 2026-08-25 05:30:00

- 版本升至 6.14。语文重跑成功：位置 3/8 → 19/24、材料/选项 24/24、严格 18/24（T0-3 普适性验证）；独立题共享材料并入修复（content_slicer）+ 20 题回填；9 科基线 187/213 (88%)。
- 下一步：英语 Q46 free_text 验证改进 → DB 清理恢复 pytest 基线 → 物理重跑 → T0-2 key 轮换（待用户）。

### 2026-08-25 06:30:00

- 版本升至 6.15。Q46 作文答案标记 essay_manual_review（需人工审核）；T0-2 key 轮换准备完成（实测三个 key 均为泄露原值未轮换，轮换步骤见 bugs.md）。
- 下一步：重灌二中数学恢复 e2e_ingestion 测试 → pytest stats 干净库冲突决策 → 物理重跑。
