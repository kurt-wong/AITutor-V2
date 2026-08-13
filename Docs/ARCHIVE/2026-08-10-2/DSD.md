# AI Tutor Personal Edition — 数据库结构设计

Version: 4.0
Status: 开发指引基线
Date: 2026-08-10
Supersedes: DSD v3.1
Source of truth: `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`

---

## 1. 目的

本文件定义项目数据库结构，是数据表和字段的唯一权威来源。

所有 Repository、Migration 和 Service 数据访问必须符合本文件。

---

## 2. 存储栈

允许：

- PostgreSQL 16
- pgvector
- MinIO 或 NAS 对象存储
- Redis

禁止：

- Qdrant
- Milvus
- Weaviate
- ChromaDB

---

## 3. 设计原则

### 3.1 Fact-Only

数据库只保存事实：

- 题目内容
- 答案
- 详解
- 元数据
- 来源和出现次数
- 错题记录
- 练习记录
- 掌握度

数据库禁止保存：

- Prompt
- 思维链
- 临时 LLM 输出
- Agent 对话

### 3.2 内容与元数据分离

题目内容字段：

- stem
- options
- answer
- explanation

元数据字段：

- subject
- grade
- year
- school
- question_type
- score
- difficulty
- knowledge_points
- occurrence_count

### 3.3 单学生

当前版本按单学生设计。

用户表预留 role，但业务默认只有一个管理员和一个学生账号。

### 3.4 知识树静态

知识树节点由管理员维护。

AI 只能把题目映射到已有节点，不能创建新节点。

### 3.5 真题与生成题

题目来源类型：

- document：来自原始文档的真题
- generated：AI 生成且审核通过的题
- student：学生 JPG 错题新建的题

---

## 4. 表结构

### 4.1 users

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| username | VARCHAR | 唯一 |
| password_hash | VARCHAR | 登录密码哈希 |
| role | VARCHAR | admin / student |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### 4.2 subjects

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| code | VARCHAR | 唯一编码 |
| name | VARCHAR | 学科名 |
| description | TEXT | |
| created_at | TIMESTAMPTZ | |

### 4.3 documents

保存原始 PDF/DOCX 文件和处理状态。

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| filename | VARCHAR | 原始文件名 |
| file_type | VARCHAR | pdf / docx |
| object_key | VARCHAR | 对象存储 key |
| subject | VARCHAR | 可选上传元数据 |
| grade | VARCHAR | 可选上传元数据 |
| year | INTEGER | 可选上传元数据 |
| school | VARCHAR | 可选上传元数据 |
| upload_status | VARCHAR | queued / processing / completed / failed |
| processing_status | VARCHAR | pending / parsing / annotating / reviewing / completed |
| error_message | TEXT | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### 4.4 document_processing_logs

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| document_id | UUID | FK documents |
| stage | VARCHAR | |
| message | TEXT | |
| created_at | TIMESTAMPTZ | |

### 4.5 questions

核心题目表。

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| subject_id | UUID | FK subjects |
| grade | VARCHAR | 高一/高二/高三 |
| year | INTEGER | 来源年份 |
| school | VARCHAR | 来源学校 |
| question_type_id | UUID | FK question_types |
| score | NUMERIC | 分值，可为空 |
| difficulty | INTEGER | 1-5 |
| stem | TEXT | 题干 |
| options | JSONB | 选项数组 |
| answer | TEXT | 标准答案 |
| explanation | TEXT | 详解 |
| source_type | VARCHAR | document / generated / student |
| source_document_name | VARCHAR | 来源文档名 |
| status | VARCHAR | approved / reviewing / rejected |
| confidence | NUMERIC | 0-1 |
| occurrence_count | INTEGER | 默认 1 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### 4.6 question_images

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| question_id | UUID | FK questions |
| image_key | VARCHAR | 对象存储 key |
| image_type | VARCHAR | diagram / question_image / formula_image |
| description | TEXT | |
| image_order | INTEGER | 排序 |
| created_at | TIMESTAMPTZ | |

### 4.7 question_occurrences

保存同一题在不同来源中的出现记录。

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| question_id | UUID | FK questions |
| source_document_name | VARCHAR | 来源文档名 |
| year | INTEGER | |
| school | VARCHAR | |
| occurrence_no | INTEGER | 同文档内出现序号 |
| created_at | TIMESTAMPTZ | |

### 4.8 question_knowledge

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| question_id | UUID | FK questions |
| knowledge_node_id | UUID | FK knowledge_nodes |
| confidence | NUMERIC | 0-1 |
| is_primary | BOOLEAN | 是否主知识点 |
| created_at | TIMESTAMPTZ | |

### 4.9 knowledge_nodes

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| subject_id | UUID | FK subjects |
| parent_id | UUID | 可空 |
| code | VARCHAR | 唯一编码 |
| name | VARCHAR | 节点名 |
| level | INTEGER | 层级 |
| description | TEXT | |
| created_at | TIMESTAMPTZ | |

### 4.10 question_types

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| subject_id | UUID | FK subjects |
| parent_id | UUID | 可空 |
| code | VARCHAR | 唯一编码 |
| name | VARCHAR | 细粒度题型名 |
| sort_order | INTEGER | 排序 |
| created_at | TIMESTAMPTZ | |

### 4.11 question_embeddings

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| question_id | UUID | FK questions |
| embedding | vector | pgvector |
| embedding_provider | VARCHAR | 本地 provider 名 |
| embedding_dimension | INTEGER | 动态维度 |
| created_at | TIMESTAMPTZ | |

### 4.12 wrong_upload_tasks

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK users |
| image_key | VARCHAR | 学生 JPG key |
| status | VARCHAR | processing / pending_review / approved / rejected |
| detected_count | INTEGER | 切分题数 |
| created_at | TIMESTAMPTZ | |

### 4.13 wrong_upload_items

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| upload_id | UUID | FK wrong_upload_tasks |
| question_id | UUID | 可空，匹配或新建后关联 |
| content_snapshot | JSONB | 识别出的题目内容 |
| metadata_snapshot | JSONB | 识别出的元数据 |
| status | VARCHAR | pending_review / approved / rejected |
| review_comment | TEXT | |
| created_at | TIMESTAMPTZ | |

### 4.14 wrong_questions

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK users |
| question_id | UUID | FK questions |
| source_type | VARCHAR | practice / jpg_upload |
| error_type | VARCHAR | 可空 |
| wrong_count | INTEGER | 默认 1 |
| last_wrong_time | TIMESTAMPTZ | |
| mastery_status | VARCHAR | mastered / reviewing / not_mastered |
| review_count | INTEGER | 默认 0 |
| last_review_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

### 4.15 practice_sessions

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK users |
| trigger_type | VARCHAR | manual / recommendation / admin |
| question_count | INTEGER | |
| status | VARCHAR | in_progress / completed / abandoned |
| started_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

### 4.16 practice_answers

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| session_id | UUID | FK practice_sessions |
| question_id | UUID | FK questions |
| question_snapshot | JSONB | 题目快照 |
| student_answer | TEXT | |
| is_correct | BOOLEAN | |
| duration_seconds | INTEGER | |
| knowledge_point_ids | JSONB | 关联知识点 |
| created_at | TIMESTAMPTZ | |

### 4.17 mastery_records

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK users |
| knowledge_node_id | UUID | FK knowledge_nodes |
| mastery_level | INTEGER | 0-2 |
| total_attempts | INTEGER | |
| correct_count | INTEGER | |
| recent_correct_rate | NUMERIC | 0-1 |
| updated_at | TIMESTAMPTZ | |

### 4.18 generation_jobs

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| task_type | VARCHAR | practice / paper |
| subject | VARCHAR | |
| grade | VARCHAR | |
| parameters | JSONB | 知识点、题型、难度、题量等 |
| ratio_snapshot | JSONB | 历史比例快照 |
| status | VARCHAR | queued / running / pending_review / completed / failed |
| created_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | |

### 4.19 generation_results

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| job_id | UUID | FK generation_jobs |
| question_id | UUID | FK questions |
| review_status | VARCHAR | pending / approved / rejected |
| review_comment | TEXT | |
| created_at | TIMESTAMPTZ | |

### 4.20 system_configs

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| config_key | VARCHAR | 唯一 |
| config_value | TEXT | |
| description | TEXT | |
| updated_at | TIMESTAMPTZ | |

---

## 5. 关系

```text
documents
└── document_processing_logs

questions
├── question_images
├── question_occurrences
├── question_knowledge
└── question_embeddings

knowledge_nodes
└── question_knowledge

question_types
└── questions

wrong_upload_tasks
└── wrong_upload_items

wrong_questions → questions

practice_sessions
└── practice_answers → questions

mastery_records → knowledge_nodes

generation_jobs
└── generation_results → questions
```

---

## 6. 索引建议

普通索引：

- questions(subject_id, grade, year)
- questions(question_type_id)
- questions(status, confidence)
- questions(source_type)
- question_knowledge(question_id, knowledge_node_id)
- question_occurrences(question_id, year)
- wrong_questions(user_id, status)
- practice_answers(session_id, question_id)
- mastery_records(user_id, knowledge_node_id)

向量索引：

```sql
CREATE INDEX idx_question_embedding
ON question_embeddings
USING hnsw (embedding vector_cosine_ops);
```

---

## 7. 一致性要求

DSD 必须与以下文档保持一致：

- PRD.md
- SAD.md
- ACS.md
- MIS.md
- PIPELINE.md

冲突时：

- 产品范围以 REQUIREMENTS_AND_SOLUTION.md 为准。
- 数据库结构以本文件为准。
