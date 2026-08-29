# AI Tutor Personal Edition — API Contract Specification

Version: 3.2
Status: 开发指引基线
Date: 2026-08-11
Supersedes: ACS v3.1
Source of truth: `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`

---

## 1. 合约原则

ACS 只定义：

- 请求结构
- 响应结构
- 错误格式
- 元数据包装

ACS 不定义：

- 业务逻辑
- MCP 工具行为
- LLM 路由
- 数据库结构

调用链必须保持：

```text
Frontend → API → Application Service → Domain Service → Repository → Infra
Agent → MCP Tool → Application Service
```

API 层禁止直连数据库，禁止直接调用 LLM SDK。正常业务不强制经过 MCP，MCP 只用于 Agent 接口层。

---

## 2. 标准响应格式

### 2.1 成功响应

```json
{
  "data": {},
  "meta": {
    "request_id": "uuid",
    "latency_ms": 1234
  }
}
```

### 2.2 错误响应

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  },
  "meta": {
    "request_id": "uuid",
    "latency_ms": 1234
  }
}
```

### 2.3 Meta 规则

meta 只允许：

- request_id
- latency_ms

禁止在 meta 中返回：

- 模型信息
- Prompt
- MCP 执行细节
- LLM 调用链路

---

## 3. 错误码

| Code | Meaning |
|---|---|
| UNAUTHORIZED | 未登录或登录已失效 |
| FORBIDDEN | 无权限 |
| VALIDATION_ERROR | 请求参数不合法 |
| NOT_FOUND | 资源不存在 |
| DOCUMENT_PARSE_FAILED | 文档解析失败 |
| LOW_CONFIDENCE | 结果置信度过低，需要人工审核 |
| GENERATION_FAILED | AI 组题失败 |
| EXPORT_FAILED | 文档导出失败 |
| LLM_FAILURE | LLM Gateway 失败 |
| MCP_TIMEOUT | MCP Tool 超时 |
| TASK_NOT_FOUND | 后台任务不存在 |
| UPLOAD_FAILED | 文件写入对象存储失败 |
| TASK_RETRY_INVALID | 后台任务当前状态不可重试 |

---

## 4. 认证

### POST /api/auth/login

Request:

```json
{
  "username": "string",
  "password": "string"
}
```

Response:

```json
{
  "data": {
    "token": "string",
    "role": "admin | student",
    "expires_at": "2026-08-10T12:00:00Z"
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

### POST /api/auth/logout

### GET /api/auth/me

Response:

```json
{
  "data": {
    "id": "string",
    "role": "admin | student"
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

---

## 4.1 统一后台任务

文档解析、AI 生成、导出、JPG 错题识别等异步能力统一使用 Task 模型。

Task 对象：

```json
{
  "id": "uuid",
  "task_type": "document_parse | generation | export | wrong_question | embedding",
  "status": "queued | running | succeeded | failed | review_required",
  "progress": 0.65,
  "current_stage": "metadata_annotation",
  "error_detail": null,
  "created_at": "2026-08-10T12:00:00Z",
  "updated_at": "2026-08-10T12:00:01Z"
}
```

#### GET /api/tasks/{task_id}

获取任务状态。

#### GET /api/tasks

Query:

- task_type
- status
- page
- page_size

#### POST /api/tasks/{task_id}/retry

重新执行失败任务。

---

## 4.2 系统健康检查

#### GET /api/health

返回后端运行状态和当前环境。

#### GET /api/health/dependencies

检查 PostgreSQL、Redis、MinIO 连通性。

Response:

```json
{
  "data": {
    "status": "ok",
    "dependencies": {
      "postgresql": {"status": "ok", "message": null},
      "redis": {"status": "ok", "message": null},
      "minio": {"status": "ok", "message": null}
    }
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

---

## 5. 管理员后台 API

### 5.1 文档上传与解析

#### POST /api/admin/documents/upload

Request: multipart/form-data

- files: binary[]
- subject: string (optional)
- grade: string (optional)
- year: integer (optional)

Response:

```json
{
  "data": {
    "task_ids": ["uuid"],
    "document_ids": ["uuid"],
    "status": "queued"
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

#### GET /api/admin/documents

Query:

- status: queued | pending | processing | completed | failed
- page
- page_size

#### GET /api/admin/documents/{document_id}

返回文档元数据、处理状态和解析统计。

#### GET /api/admin/documents/{document_id}/status

返回：

```json
{
  "data": {
    "status": "processing",
    "progress": 0.65,
    "current_stage": "metadata_annotation",
    "error_message": null
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

#### GET /api/admin/documents/{document_id}/parse-result

返回文档解析任务原始结果 JSON，包含 `task_id`、`document_id`、`status`、`progress`、`current_stage`、`error_message` 和 `result`。

#### POST /api/admin/documents/{document_id}/retry

重新进入解析队列。

#### GET /api/admin/documents/{document_id}/logs

返回处理日志列表。

#### GET /api/admin/documents/answer-retries

答案提取重试队列。

Query:

- status: pending | retrying | succeeded | failed

Response:

```json
{
  "data": {
    "items": [
      {
        "id": "uuid",
        "document_id": "uuid",
        "status": "pending",
        "retry_count": 0,
        "max_retries": 3,
        "error_detail": "string",
        "created_at": "iso8601",
        "last_retry_at": "iso8601"
      }
    ],
    "total": 0
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

#### POST /api/admin/documents/answer-retries/{retry_id}/retry

人工触发重试：重置重试记录为 pending 状态。

#### PUT /api/admin/documents/{document_id}/review

保存解析结果的人工审核状态和修正内容。

Request:

```json
{
  "question_number": "Q1",
  "status": "approved | rejected | pending",
  "comment": "审核意见",
  "overrides": {
    "stem": "修正后的题干",
    "answer": "B"
  }
}
```

审核状态写入 `result.review_decisions[question_number]`，修正内容写入
`result.review_overrides[question_number]`，随 `GET parse-result` 返回。

### 5.2 审核队列

#### GET /api/admin/review-items

Query:

- type: document | question | generated_question | wrong_question
- subject
- status
- page
- page_size

#### PUT /api/admin/review-items/{review_item_id}

Request:

```json
{
  "status": "approved | rejected | pending",
  "comment": "审核意见",
  "content_override": {},
  "metadata_override": {},
  "images": []
}
```


### 5.3 题库管理

#### GET /api/admin/catalog

题库目录聚合：学科 → 年级 → 题目数（管理后台题库目录树）。

Response:

```json
{
  "data": [
    {
      "name": "数学",
      "question_count": 123,
      "grades": [
        {"name": "高一", "question_count": 100},
        {"name": null, "question_count": 23}
      ]
    }
  ],
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

#### GET /api/admin/questions

Query:

- subject
- grade
- year
- school
- question_type
- knowledge_point
- difficulty
- source_type: document | generated | student
- status
- confidence
- page
- page_size

#### GET /api/admin/questions/{question_id}

返回题目内容、配图、答案、详解、元数据和出现次数。

#### PUT /api/admin/questions/{question_id}

更新题目内容、答案、详解和元数据。

#### DELETE /api/admin/questions/{question_id}

删除题目。

#### POST /api/admin/questions/{question_id}/merge

将候选重复题合并到当前题目。

Request:

```json
{
  "candidate_question_ids": ["uuid"]
}
```

#### PUT /api/admin/questions/{question_id}/images

更新配图列表。

### 5.4 统计分析

#### GET /api/admin/statistics

Query:

- start_year
- end_year
- subject
- grade
- knowledge_point
- question_type

Response:

```json
{
  "data": {
    "total_questions": 0,
    "question_type_distribution": {},
    "knowledge_point_distribution": {},
    "difficulty_distribution": {},
    "year_trend": [],
    "kp_year_trend": []
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

`kp_year_trend`：知识点×年份趋势（ROADMAP P4B #3「按年份看趋势」），数组元素为 `{"knowledge_point": "二次函数", "year": 2024, "count": 3}`，按知识点名 + 年份升序。受 `start_year`/`end_year` 过滤。

#### GET /api/admin/statistics/wrong

返回错题统计，包括单题错题次数和知识点/题型错题频次。

#### GET /api/admin/statistics/student

返回学生学习趋势和薄弱点。

### 5.5 AI 组题

#### POST /api/admin/generation/tasks

Request:

```json
{
  "subject": "mathematics",
  "grade": "senior_high_2",
  "knowledge_points": ["quadratic_function"],
  "question_types": ["single_choice", "calculation"],
  "difficulty_range": [1, 5],
  "question_count": 10,
  "ratio_mode": "auto | manual",
  "manual_ratio": {},
  "export_format": "student | answer_only | both"
}
```

Response:

```json
{
  "data": {
    "task_id": "uuid",
    "status": "queued"
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

#### GET /api/admin/generation/tasks/{task_id}

返回任务状态、生成结果统计和审核状态。

#### POST /api/admin/generation/tasks/{task_id}/review

批量审核生成题。

Request:

```json
{
  "items": [
    {
      "question_id": "uuid",
      "status": "approved | rejected",
      "content_override": {}
    }
  ]
}
```

#### POST /api/admin/generation/tasks/{task_id}/export

Request:

```json
{
  "format": "pdf | docx",
  "include_answers": false
}
```

Response:

```json
{
  "data": {
    "download_url": "string"
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

### 5.6 系统配置

#### GET /api/admin/config

返回 API Key 掩码、模型路由、审核阈值等配置。

#### PUT /api/admin/config

更新系统配置。

#### GET/PUT /api/admin/config/knowledge-tree

查看和更新标准知识树。

#### GET/PUT /api/admin/config/question-types

查看和更新按学科维护的题型规范。

#### GET /api/admin/question-types

返回完整题型树层级结构。

Query:

- subject: MATH / ENG / ... （可选，按学科过滤）

Response:

```json
{
  "subjects": [
    {
      "code": "MATH",
      "name": "数学",
      "types": [
        {
          "code": "MATH-CHOICE",
          "name": "选择题",
          "level": 1,
          "description": null,
          "keywords": [],
          "children": [
            {"code": "MATH-CHOICE-SINGLE", "name": "单项选择", "level": 2, "children": null}
          ]
        }
      ]
    }
  ]
}
```

---

## 6. 学生端 API

### 6.1 错题上传

#### POST /api/student/wrong-questions/upload

Request: multipart/form-data

- file: binary (JPG)

Response:

```json
{
  "data": {
    "task_id": "uuid",
    "upload_id": "uuid",
    "status": "processing",
    "detected_question_count": 0
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

### 6.2 错题本

#### GET /api/student/wrong-questions

Query:

- subject
- knowledge_point
- status
- page
- page_size

#### GET /api/student/wrong-questions/{question_id}

返回错题详情和解析。

#### PUT /api/student/wrong-questions/{question_id}/mastery

Request:

```json
{
  "mastery_status": "mastered | reviewing | not_mastered"
}
```

#### POST /api/admin/wrong-questions/{upload_id}/review

管理员确认或编辑 JPG 错题。

### 6.3 练习

#### POST /api/student/practice

Request:

```json
{
  "trigger": "manual | recommendation | admin",
  "knowledge_points": [],
  "question_count": 10
}
```

Response:

```json
{
  "data": {
    "practice_id": "uuid",
    "questions": []
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

#### POST /api/student/practice/{practice_id}/answer

Request:

```json
{
  "question_id": "uuid",
  "student_answer": "string",
  "duration_seconds": 120
}
```

Response:

```json
{
  "data": {
    "is_correct": true,
    "correct_answer": "string",
    "explanation": "string"
  },
  "meta": {"request_id": "uuid", "latency_ms": 1234}
}
```

#### GET /api/student/practice/history

返回练习历史。

### 6.4 学生统计

#### GET /api/student/statistics

返回学生自己的错题统计、学习趋势和薄弱知识点。

---

## 7. 兼容性规则

- API 合约保持稳定，不随模型路由变化。
- MCP 工具变化不得改变外部 API 响应结构。
- 数据库演进不得破坏 ACS 合约。
- 新错误码必须追加到错误码表。

---

> 变更记录统一记录在根目录 `LOG.md`；历史版本文档见 `docs_archive/2026-08-24/ACS.md`。
