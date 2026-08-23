# AI Tutor Personal Edition — 系统架构设计

Version: 4.5
Status: 开发指引基线
Date: 2026-08-11
Supersedes: SAD v4.2
Source of truth: `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`

---

## 1. 架构原则

### P1 — 题库为数据核心

系统围绕结构化题库构建。题目内容、配图、答案、详解和元数据是数据库中的一等实体，所有分析、生成和学习功能都依赖题库数据。

### P2 — 自动化为主，人工校对兜底

文档解析、元数据标注和错题识别以自动化为主。只有低置信度结果进入人工审核队列。

### P3 — LLM 统一入口

所有 LLM 调用统一通过 LLM Gateway 路由，不允许业务代码直接调用模型 SDK。

### P4 — MCP 是 Agent 接口层，不是业务主链路

正常业务主链路使用 Application Service 和 Domain Service。MCP 只作为 Agent 接口层，供 Codex/Claude 或其他智能体调用系统能力。

### P5 — 只存事实

数据库只保存题目内容、答案、详解、元数据、学习记录等事实，不保存 prompt、思维链和临时推理。

### P6 — 知识树人工可控

知识树以管理员提供的标准资料为基础，AI 只能映射，不能随意创建节点。

### P7 — 前端设计统一

所有前端页面遵循 `Docs/Design.md`，具体页面组件规范见 `Docs/02_Architecture/UI.md`。

### P8 — 解析信息源保真

文档解析必须优先保留信息源，禁止让有损表示成为唯一事实源：

- PDF 采用 Native/PP 双源 L1 证据路由；canonical L1 按行选择，LLM 只做行级仲裁。
- LLM 只输出粗略行号/元数据，代码先做锚点校正，再从 L1 原文切片。
- 配图必须保留 `page/bbox/placement/source`。
- 教师版答案/详解优先，LLM 生成只兜底并标记来源。

详细约束见 `Docs/05_Development/V1_LESSONS.md`。

---

## 2. 总体架构

```text
React/Vite 前端
  → FastAPI API Layer
  → Application Service
  → Domain Service
  → Repository
  → PostgreSQL + pgvector / MinIO / Redis

AI Gateway → LLM Provider
Agent → MCP Tool → Application Service
```

依赖方向必须保持单向：

```text
UI → API → Application Service → Domain Service → Repository → Infra
```

禁止路径：

- UI → DB
- API → DB
- Service → LLM SDK
- MCP Tool 绕过 Application Service 直连数据库

---

## 3. 分层职责

| 层 | 职责 |
|---|---|
| Frontend | 管理员后台和学生端页面，遵循 Design.md |
| API Layer | 外部 API 合约、请求校验、响应包装 |
| Application Service | 用例编排、任务调度、审核流程、统计计算 |
| Domain Service | 题目聚合、去重、知识映射、错题、练习等业务规则 |
| Repository | 数据访问和事务控制 |
| AI Gateway | 唯一 LLM 入口，负责 Provider 路由和回退 |
| MCP Tool | 可选 Agent 接口层，供智能体调用 Application Service |
| Infra | PostgreSQL、pgvector、MinIO、Redis、LLM Gateway |

---

## 4. 领域上下文

后端按领域拆分：

```text
backend/app/domains/
├── document/          # 文档上传、解析、进度、重试、日志
├── question/          # 题目模型、题库、审核、合并
├── knowledge/         # 知识树、知识点映射、题型规范
├── analytics/         # 频次、趋势、占比、统计
├── generation/        # AI 组题、生成题审核、导出
├── student/           # 学生登录、JPG 错题、练习、学习记录
├── wrong_question/    # 错题本、错题统计
├── embedding/         # Ollama embedding、语义查重
├── task/              # 统一后台任务、进度、重试
├── event/             # Domain Event、事件总线、事件消费
├── system/            # 配置、模型路由、API Key 管理
└── auth/              # 管理员/学生登录与角色
```

---

## 4.1 核心领域契约

### Question Aggregate

Question Aggregate 是系统底层契约，所有模块共享同一题目模型。

```text
Question
├── Content
│   ├── stem
│   ├── options
│   ├── answer
│   └── solution
├── Assets
│   └── images[]
├── Metadata
│   ├── subject
│   ├── grade
│   ├── knowledge_points
│   └── difficulty
├── Provenance
│   ├── source_instances[]
│   ├── source_type
│   └── review_status
├── Quality
│   ├── confidence
│   └── review_status
└── Statistics
    ├── appeared_count
    ├── wrong_count
    └── mastery_status
```

来源信息与题目内容分离：一道题是一个 Question Entity，每次出现是一个 Question Instance。

### Background Task

文档解析、AI 生成、导出、错题识别等统一使用同一任务模型：

```text
task_id
task_type
status: queued | running | succeeded | failed | review_required
progress
current_stage
error_detail
created_at
updated_at
```

### Domain Event

系统使用事件模型解耦统计、推荐、Agent 和学习分析：

```text
QuestionCreated
QuestionReviewed
QuestionMerged
WrongQuestionCreated
PracticeCompleted
KnowledgePointUpdated
```

事件由 Domain Service 发布，事件消费者负责更新统计、推荐和 Agent 可访问数据。

### 4.2 文档制品分层

V1 经验教训固化为 V2 的文档制品分层：

```text
L0  原始 PDF/DOCX 存档，永久不可变
L1  Native Markdown 或 OCR Markdown，按行编号，作为 LLM 标注的原文来源
L2  LLM 标注镜像：只保存题号、题型、粗略行号范围、校正后行号、答案字母、元数据等
L3  前端/导出渲染：由 L1 + L2 组合生成，不直接信任 LLM 抄写内容
```

说明：

- L1 必须可持久化、可追溯、可重新切片。
- L2 JSON 中不保存 LaTeX 题干原文。
- L2 必须同时保存 `llm_anchor`、`corrected_anchor`、`anchor_status`。
- LLM 行号属于粗定位；未经锚点校正不得直接作为最终切片边界。
- L2 行号字段在归一化时必须透传；quality gate 失败只标记低置信度，不整批丢弃。
- 图片关联属于 L1 元数据，必须保留 `page/bbox/placement/source`。

---

## 5. 核心工作流

### 5.1 文档入库

```text
管理员上传 PDF/DOCX
  → 原始文件写入 MinIO/对象存储
  → 文档解析任务入队
  → PDF 先检查 Native 文本层，充足时生成 Native Markdown
  → 扫描/原生不足时进入 PP-StructureV3/OCR/VL
  → 文本、公式、表格、图片提取
  → LLM 输出行号/题型/答案位置等标注
  → 代码按 L1 原文切片生成题目
  → 配图关联
  → 答案/详解匹配
  → 元数据标注与来源校验
  → 置信度判断
  → 高置信度入库 / 低置信度进入审核队列
  → 重复题合并
```

### 5.2 AI 组题

```text
管理员或系统触发生成
  → 获取历史趋势、频率、占比
  → 自动计算题型/知识点/难度分布
  → LLM 生成题目、答案、详解、公式/配图
  → 生成结果进入审核队列
  → 审核通过后标记“生成题”入库
  → 支持导出学生版和答案/详解版
```

### 5.3 学生 JPG 错题

```text
学生上传 JPG
  → 自动切分多题
  → OCR/VL 识别题目
  → 匹配题库已有题目或新建
  → 进入管理员确认队列
  → 确认后进入错题本
```

### 5.4 学生练习

```text
触发练习
  → 根据错题、掌握度、历史表现生成题目
  → 学生作答
  → 系统自动判分
  → 保存答题记录
  → 答错自动进入错题本
  → 更新知识点掌握度
```

---

## 6. 模型路由

| 任务 | 路由 |
|---|---|
| PDF 版面解析 | Native 文本层优先；PP-StructureV3 云 API 兜底 |
| DOCX 解析 | 本地解析 + LLM 结构化 |
| OCR/VL | PaddleOCR-VL、MIMO、DeepSeek Vision |
| 元数据标注 | DeepSeek / MIMO |
| AI 生成题 | DeepSeek / MIMO |
| 难度评估 | LLM + 规则 + 学习数据 |
| embedding | NAS 本地 Ollama qwen3-embedding:4b（2560） |
| 导出文档 | 服务端文档生成，不依赖 LLM |

所有 AI 能力必须可经过 LLM Gateway 路由。回退链按 Provider 配置执行。

---

## 7. 数据架构

### 7.1 存储栈

- PostgreSQL：结构化数据和统计结果。
- pgvector：语义查重和相似检索。
- MinIO 或 NAS 对象存储：原始 PDF/DOCX、配图、学生 JPG。
- Redis：任务队列、缓存、会话。

### 7.2 数据原则

- 题目内容与元数据分开。
- 同一道题跨文档出现时合并，保留来源和出现次数。
- AI 生成题标记类型，与真题共存。
- 练习记录保存题目快照、孩子答案、对错、用时和知识点。
- 数据库不保存 prompt 和 CoT。

详细表结构见 `Docs/03_Data/DSD.md`。

---

## 8. 前端架构与设计

前端分为两个入口：

```text
/           → 学生端
/admin      → 管理后台
```

前端遵循 `Docs/Design.md` 的设计语言：

- 单一蓝色强调色。
- 白色、浅灰、近黑全宽区块。
- 内容优先，避免装饰性渐变。
- 工具型页面保持低干扰、高密度、可扫描。

页面清单和组件规范见 `Docs/02_Architecture/UI.md`。

---

## 9. 部署

采用 Docker Compose 部署在 NAS。

服务：

```text
frontend
backend
worker
postgres
minio
redis
```

硬件约束：

- NAS 只有 CPU。
- embedding 使用 NAS 本地 Ollama qwen3-embedding:4b（2560 维）。
- 重任务使用云 API。
- 原始文件和图片保存在 NAS 对象存储。

配置通过 `.env` 管理，禁止硬编码 API Key。

---

## 10. 非目标

- 多租户。
- 多学生独立账号。
- 手机和平板优先支持。
- 固定模板模拟考试。
- 题库批量导入导出。

---

## 11. 架构治理

- 新功能必须符合 `UI → API → Application Service → Domain Service → Repository → Infra`。
- 只有 Agent 需要调用时才在 MIS.md 定义 MCP Tool。
- 新增后台任务必须复用统一 Task Domain。
- 业务状态变化必须发布 Domain Event。
- API 合约以 ACS.md 为准。
- 数据表以 DSD.md 为准。
- 产品范围以 PRD.md 和 REQUIREMENTS_AND_SOLUTION.md 为准。
- 文档解析严格执行 `Docs/05_Development/V1_LESSONS.md` 的 P0/P1 约束。
- 解析结果必须保留 L1 来源、行号标注和图片位置元数据。
- 任何表结构变更必须同步 Alembic migration。
- live LLM/OCR 测试必须与常规 pytest 隔离。

### 2026-08-11 23:49:10

- 文档解析架构更新为 L1 双源：PyMuPDF native 与 PP-StructureV3 并存。
