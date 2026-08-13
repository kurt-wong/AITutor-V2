# AI Tutor Personal Edition — RESTART_PROMPT

Version: 2.0
Status: 重启恢复指引（Phase 1 最终验收通过 + 基础设施加固，2026-08-13；golden 8 题纵向闭环，全卷低置信度项待 Phase 2/3 审核）
Date: 2026-08-13

---

## 1. 用途

本文件用于 Codex/Claude 在重启后快速恢复工作状态。

任何 Agent 进入项目后，应先读本文件，再按需读取 `rules.md`、`PROJECT_STATUS.md`、`LOG.md` 和相关权威文档。

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

当前阶段：P0/P1 完成，P2 临时验证闭环已冻结；**T3 Phase 1 最终验收通过**（2026-08-13，golden 8 题纵向闭环；全卷低置信度项待 Phase 2/3 审核）。后端 143 项测试通过。

- 已有完整需求基线。
- 已创建后端 FastAPI 骨架和前端 React/Vite 骨架。
- 已创建 Docker Compose、`.env`、`.env.example` 和 README。
- 后端 `compileall` 通过，`docker compose config` 通过。
- 前端 `npm install` 因环境限制超时，尚未生成 `package-lock.json` 和 `node_modules`。
- 核心文档已按新需求重写，旧文档已备份到 `Docs/ARCHIVE/2026-08-10/` 和 `Docs/ARCHIVE/2026-08-10-2/`。
- 已确认使用 Docker 部署在 NAS，NAS 只有 CPU。
- 已确认 embedding 使用本地 Ollama `qwen3-embedding:4b`（2560 维），文档解析、题目生成等重任务使用云 API。
- 已有 DeepSeek、MIMO、PaddleOCR-VL、PP-StructureV3 API Key。
- MCP 已定位为可选 Agent 接口层，不作为业务主链路。
- 已确定核心领域契约：Question Aggregate、Background Task、Domain Event、Knowledge Tree。
- 已确定 Phase 0 至 Phase 5 开发路线。
- 已建立 `DICTIONARY.md`，用于统一字段、功能和状态枚举。
- 已补齐后端 Repository、Domain Service、Application Service、统一 Task/Domain Event 和 LLM Gateway 基础路由骨架。
- 开发任务计划已固化到 `ROADMAP.md`，后续按 P0-P7 执行；OCR API 资料已保存到 `PADDLEOCR_API.md`。
- 已编写 22 张 DSD 表模型的 Alembic 初始迁移，并已在现有 `aitutor-postgres` 的 `aitutors` 新库执行成功；旧 `ai_tutor` 库未改动。
- embedding 为 2560 维，超过 pgvector HNSW 索引 2000 维上限，初始迁移不建向量索引，采用暴力余弦检索。
- 已新增 `scripts/allow-codex-docker.ps1`；当前会话直接复用现有 Docker 实例，脚本保留给沙箱账号场景。
- 已建立 `test/pdf/`，包含 30 份教师版 PDF，覆盖 9 科；尚未建立字段级准确率统计。
- MinIO 客户端已接入，后端已通过 PostgreSQL/Redis/MinIO 依赖健康检查。
- 已实现文档上传、MinIO 对象写入、文档/任务查询、状态、重试、日志 API。
- 已生成 `test/pdf/manifest.csv`，30 份 PDF、9 科清单校验通过。
- 已补齐 `backend/scripts/validate_docs_vs_code.py` 并通过。
- P2 已新增 PP-StructureV3 客户端、OCR/VL 回退链、LLM 结构化 Question Aggregate 输出、`test/scripts/run_parse_baseline.py` 和 `test/scripts/evaluate_parse_accuracy.py`。
- `test/annotations/` 尚无 30 份人工标注 JSON；DeepSeek/MIMO/Qwen base/model 已配置，live 联调前需切换 `LLM_GATEWAY_MODE=live` 并验证可达性。
- 已新增 `Docs/05_Development/V1_LESSONS.md`，把 V1 的解析、配图、来源、审核、测试和部署坑固化为 v2 强制约束。
- 当前 `question_extractor.py` 仍是临时验证版，正式 T3 前必须改为行号标注范式。
- 行号标注规范已补充：LLM 行号是粗定位，代码必须做锚点校正并保存 `llm_anchor/corrected_anchor/anchor_status`。
- `V1_LESSONS.md` 已按差距分析扩充至 3.29，新增复合题、quality gate 部分保存、单行选项、L2 行号透传、答案区不截断、Solution draft 等约束。
- 尚未完成前端依赖安装和完整文档入库/审核管线。
- T3 Phase 1 状态：**最终验收通过 + 基础设施加固**（2026-08-13）。L1 双源：PyMuPDF native + PP-StructureV3；canonical L1 与 LLM 行级仲裁已实施。Mock eval 8/8 100%，Live-pp golden 8/8 100%；全卷 21 题 answer_matched=16、blocked=7，低置信度项按题标记待审核。eval 脚本新增全卷验收阈值 `THRESHOLDS_FULL卷`；`HTTPLLMProvider` 新增指数退避重试（max_retries=2）。
- Phase 1 模块：`ppsv3_l1.py`（开发中）、`native_markdown.py`（辅助源）、`line_annotator.py`、`anchor_corrector.py`、`content_slicer.py`、`answer_matcher.py`、`quality_gate.py`、`pipeline.py`。
- Phase 1 真实样本：`2026北京朝阳高一（上）期末数学（教师版）.pdf`，L1 fixture 172 行，golden 8 题。
- Phase 0 保留：Schema、fixture（数学 38 行 + 英语 69 行）、golden（数学 v3.1 7 题 + 英语 v3.1 10 题）、smoke test（14 项）。

---

## 4. 文档地图

| 文档 | 用途 |
|---|---|
| `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md` | 真实需求与方案基线 |
| `Docs/00_Requirements/DICTIONARY.md` | 字段、功能、状态字典 |
| `Docs/01_Product/PRD.md` | 产品需求 |
| `Docs/01_Product/TASK.md` | 任务执行规范 |
| `Docs/02_Architecture/SAD.md` | 系统架构 |
| `Docs/02_Architecture/MIS.md` | MCP 工具规范，Agent 接口层 |
| `Docs/02_Architecture/ACS.md` | API 合约 |
| `Docs/02_Architecture/PIPELINE.md` | 文档入库管线 |
| `Docs/05_Development/V1_LESSONS.md` | V1 经验教训与强制约束 |
| `Docs/01_Product/ROADMAP.md` | 开发任务计划（严格执行基线） |
| `Docs/02_Architecture/PADDLEOCR_API.md` | PaddleOCR-VL / PP-StructureV3 API 资料 |
| `Docs/02_Architecture/UI.md` | 前端页面规范 |
| `Docs/03_Data/DSD.md` | 数据库结构 |
| `Docs/Design.md` | 前端视觉设计风格 |
| `PROJECT_STATUS.md` | 当前状态和下一步 |
| `LOG.md` | 变更历史 |
| `rules.md` | 项目规则和约束 |

---

## 5. 待办任务

任务计划以 `Docs/01_Product/ROADMAP.md` 为准；T1-T10 为阶段内细化条目。

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

状态：**Phase 0 已完成验收**（DeepSeek/MIMO/Qwen 全部 Live passed，English Golden Set v3.1 基于 postprocessed L1 fixture，69 行含完形填空共享材料、答案区与详解区）；**Phase 1 最终验收通过**（golden 8/8，2026-08-13 对抗性审查通过，全卷低置信度项待 Phase 2/3 审核）。

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
- qwen_vl：**passed**，38s，`json_valid=true`

**Phase 0 验收通过。**

### 6.3 后续再重启时的验证清单

```powershell
python test/scripts/llm_smoke_test.py --live
```

若全部 passed，直接进入 Phase 1。

若 `smoke_report.json` 中 deepseek/mimo/qwen_vl 全部 passed，再更新 `PROJECT_STATUS.md` 并进入 Phase 1。

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
