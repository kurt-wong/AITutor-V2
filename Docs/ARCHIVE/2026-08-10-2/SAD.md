# AI Tutor Personal Edition — 系统架构设计

Version: 4.0
Status: 开发指引基线
Date: 2026-08-10
Supersedes: SAD v3.2
Source of truth: `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`

---

## 1. 架构原则

### P1 — 题库为数据核心

系统围绕结构化题库构建。题目内容、配图、答案、详解和元数据是数据库中的一等实体，所有分析、生成和学习功能都依赖题库数据。

### P2 — 自动化为主，人工校对兜底

文档解析、元数据标注和错题识别以自动化为主。只有低置信度结果进入人工审核队列。

### P3 — LLM 统一入口

所有 LLM 调用统一通过 LLM Gateway 路由，不允许业务代码直接调用模型 SDK。

### P4 — Tool-First

能力通过 MCP Tool 暴露。API 层负责外部契约，Service 层负责业务编排，MCP Server 负责能力执行。

### P5 — 只存事实

数据库只保存题目内容、答案、详解、元数据、学习记录等事实，不保存 prompt、思维链和临时推理。

### P6 — 知识树人工可控

知识树以管理员提供的标准资料为基础，AI 只能映射，不能随意创建节点。

### P7 — 前端设计统一

所有前端页面遵循 `Docs/Design.md`，具体页面组件规范见 `Docs/02_Architecture/UI.md`。

---

## 2. 总体架构

```text
React/Vite 前端
  → FastAPI API Layer
  → Service Layer
  → MCP Client Layer
  → MCP Server Layer
  → PostgreSQL + pgvector / MinIO / Redis
  → LLM Gateway
```

依赖方向必须保持单向：

```text
UI → API → Service → MCP → Infra
```

禁止路径：

- UI → DB
- API → DB
- Service → LLM SDK
- MCP Server 绕过 Service 直连数据库

---

## 3. 分层职责

| 层 | 职责 |
|---|---|
| Frontend | 管理员后台和学生端页面，遵循 Design.md |
| API Layer | 外部 API 合约、请求校验、响应包装 |
| Service Layer | 业务编排、任务调度、审核流程、统计计算 |
| MCP Client | 调用 MCP Server 的能力入口 |
| MCP Server | 暴露单一职责能力工具 |
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
├── embedding/         # 本地 embedding、语义查重
├── system/            # 配置、模型路由、API Key 管理
└── auth/              # 管理员/学生登录与角色
```

---

## 5. 核心工作流

### 5.1 文档入库

```text
管理员上传 PDF/DOCX
  → 原始文件写入 MinIO/对象存储
  → 文档解析任务入队
  → 文本、公式、表格、图片提取
  → 题目切分
  → 配图关联
  → 答案/详解匹配
  → LLM 元数据标注
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
| PDF 版面解析 | PP-StructureV3 云 API |
| DOCX 解析 | 本地解析 + LLM 结构化 |
| OCR/VL | PaddleOCR-VL、MIMO、Qwen |
| 元数据标注 | DeepSeek / MIMO |
| AI 生成题 | DeepSeek / MIMO |
| 难度评估 | LLM + 规则 + 学习数据 |
| embedding | NAS 本地轻量模型 |
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
- embedding 使用本地轻量模型。
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

- 新功能必须符合 `UI → API → Service → MCP → Infra`。
- 新增能力必须先在 MIS.md 定义 MCP Tool。
- API 合约以 ACS.md 为准。
- 数据表以 DSD.md 为准。
- 产品范围以 PRD.md 和 REQUIREMENTS_AND_SOLUTION.md 为准。

