# AI Tutor Personal Edition — MCP Interface Specification

Version: 2.1
Status: 开发指引基线
Date: 2026-08-10
Supersedes: MIS v2.0
Source of truth: `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`

---

## 1. 设计原则

系统业务主链路采用 Application Service + Domain Service + Repository。

MCP 不是业务主链路，而是 Agent 接口层：

- 正常业务：API → Application Service → Domain Service → Repository。
- AI 能力：AI Gateway → LLM Provider。
- Agent 能力：Agent → MCP Tool → Application Service。
- 不设置独立 Agent 运行时。

核心关系：

```text
Agent 智能能力 = MCP Tool
业务编排 = Application Service
业务规则 = Domain Service
所有持久化 = DSD Schema
所有外部契约 = ACS
```

---

## 2. 架构规则

调用链：

```text
UI → API → Application Service → Domain Service → Repository → Infra
Agent → MCP Tool → Application Service
```

禁止：

- API 直连数据库。
- Service 直连 LLM SDK。
- MCP Tool 绕过 Application Service 直连 SQL。
- 前端直接访问数据库。
- 数据库中保存 prompt 和 CoT。

说明：

- 本文件工具表是 Agent-facing 能力清单。
- 正常业务主链路不强制经过 MCP。
- 只有需要让 Codex/Claude 或其他 Agent 调用系统时，才实现对应 MCP Tool。

---

## 3. MCP Server 工具表

以下为开发指引目标工具表。工具命名在实现时可以微调，但职责和语义不能减少。

### 3.1 Document MCP

负责文档上传、解析、进度和审核前处理。

| Tool | Description |
|---|---|
| upload_documents | 上传 PDF/DOCX 到对象存储并创建文档记录 |
| parse_documents | 对文档执行完整解析任务 |
| get_document_status | 获取文档处理状态和进度 |
| retry_document | 重新执行失败文档 |
| get_parse_logs | 获取文档解析日志 |
| extract_question_blocks | 从文档中切分题目块 |
| extract_question_images | 提取并关联题目配图 |
| match_answers | 匹配题后答案和文末答案 |
| annotate_metadata | 用 LLM 标注学科、年级、年份、学校、题型、分值、难度、知识点 |
| judge_confidence | 判断题目置信度并决定入库或审核 |

### 3.2 Question MCP

负责题目保存、查询、编辑、审核和合并。

| Tool | Description |
|---|---|
| save_question | 保存结构化题目 |
| get_question | 按 ID 获取题目 |
| search_questions | 按条件搜索题库 |
| update_question | 更新题目内容、答案、详解和元数据 |
| delete_question | 删除题目 |
| merge_duplicate | 合并重复题并保留来源和出现次数 |
| review_question | 审核低置信度或生成题 |
| add_question_image | 添加或替换题目配图 |

### 3.3 Knowledge MCP

负责知识树、题型规范和题目映射。

| Tool | Description |
|---|---|
| classify_subject | 识别题目学科 |
| map_knowledge_points | 映射题目到标准知识树节点 |
| evaluate_difficulty | 评估题目难度 |
| get_knowledge_tree | 获取标准知识树 |
| update_knowledge_tree | 人工维护知识树 |
| get_question_types | 获取按学科维护的题型规范 |
| update_question_types | 人工维护题型规范 |

### 3.4 LLM Gateway MCP

所有 LLM 能力统一入口。

| Tool | Description |
|---|---|
| solve_question | 生成题目解答 |
| generate_explanation | 生成详解 |
| generate_hint | 生成思考提示 |
| extract_visual_structure | 从图片提取题目和图形结构 |
| generate_metadata | 生成或补全元数据 |
| generate_question | 根据考点和比例生成新题 |
| review_generated_question | 检查生成题质量 |

### 3.5 Analytics MCP

负责题库和学习数据统计。

| Tool | Description |
|---|---|
| get_type_stats | 按题型统计频次 |
| get_knowledge_stats | 按知识点统计频次和占比 |
| get_difficulty_stats | 统计难度分布 |
| get_trend_stats | 按年份统计趋势 |
| get_wrong_stats | 统计错题频次 |
| get_student_stats | 统计学生学习趋势和薄弱点 |

### 3.6 Generation MCP

负责 AI 组题和导出。

| Tool | Description |
|---|---|
| calculate_generation_ratio | 根据历史趋势、频率和占比计算组题分布 |
| generate_practice | 生成学生练习 |
| generate_paper | 生成试卷 |
| export_paper | 导出学生版或答案详解版 |

### 3.7 Student MCP

负责学生端学习能力。

| Tool | Description |
|---|---|
| upload_wrong_image | 上传学生 JPG 错题 |
| split_wrong_image | 自动切分多题 |
| create_wrong_question | 创建待确认错题 |
| get_wrong_questions | 获取错题本 |
| start_practice | 开始练习 |
| submit_answer | 提交答案并判分 |
| get_practice_history | 获取练习历史 |

### 3.8 WrongQuestion MCP

负责错题存储、审核和队列。

| Tool | Description |
|---|---|
| save_wrong_question | 保存错题记录 |
| update_wrong_question | 更新错题状态和掌握度 |
| get_pending_status | 获取待审核状态 |
| get_queue_status | 获取队列状态 |

### 3.9 Embedding MCP

负责本地 embedding 和语义查重。

| Tool | Description |
|---|---|
| generate_embedding | 生成题目 embedding |
| search_similar | 语义相似搜索 |
| embedding_health | embedding 服务健康检查 |

---

## 4. 工具执行规则

- 每个工具必须单一职责。
- 工具必须无状态。
- 同一 MCP Server 内工具不得互调。
- 跨 Server 组合只能由 Service 层编排。
- 工具输出必须符合 ACS 和 DSD。
- 失败必须返回结构化错误，不能静默吞掉。
- 不允许 MCP Tool 返回 ACS meta。

---

## 5. 一致性要求

MIS 必须与以下文档保持一致：

- PRD.md
- SAD.md
- ACS.md
- PIPELINE.md
- DSD.md

冲突优先级：

```text
REQUIREMENTS_AND_SOLUTION.md > MIS.md > ACS.md > SAD.md > PRD.md > DSD.md
```
