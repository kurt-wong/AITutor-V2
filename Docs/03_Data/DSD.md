# AI Tutor Personal Edition — 数据库结构设计

Version: 4.5
Status: 开发指引基线
Date: 2026-08-11
Supersedes: DSD v4.3
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
| processing_status | VARCHAR | pending / parsing / annotating / reviewing / completed / failed |
| error_message | TEXT | |
| native_markdown | TEXT | 电子文本 PDF 的 L1 Native Markdown（P2 落地） |
| ocr_markdown | TEXT | 扫描件/OCR 路径的 L1 Markdown（P2 落地） |
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
| question_type_id | UUID | FK question_types |
| original_question_type | VARCHAR(50) | LLM 原始细粒度题型 code（cloze/grammar_fill/seven_to_five/essay/writing 等），可为空 |
| section_id | VARCHAR(100) | 来源卷面 section/共享材料区标识，可为空 |
| score | NUMERIC | 分值，可为空 |
| difficulty | INTEGER | 1-5 |
| stem | TEXT | 题干 |
| options | JSONB | 选项数组 |
| answer | TEXT | 标准答案 |
| answer_structure | JSONB | 结构化答案元数据（多答案/范围/扩展结构），可为空 |
| word_bank | JSONB | 选词填空题组共享词库，可为空 |
| explanation | TEXT | 详解 |
| source_type | VARCHAR | document / generated / student |
| source_document_name | VARCHAR | 来源文档名 |
| status | VARCHAR | approved / reviewing / rejected |
| confidence | NUMERIC | 0-1 |
| occurrence_count | INTEGER | 缓存字段，由 Instance COUNT 驱动 |
| content_hash | VARCHAR(64) | SHA256（规范化题干+选项+题型），Step 5 已实现，可为 NULL（历史数据） |
| is_composite | BOOLEAN | 是否为综合题，默认 false |
| sub_questions | JSONB | 综合题子题元数据（可递归 sub_sub_questions） |
| review_reason | VARCHAR(200) | 审核原因分类 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

说明：

- year / school 已迁移到 question_instances（Phase 2A Step 1，2026-08-21）。
- content_hash 规范化/计算见 `app/domains/document/content_hash.py`（Step 5 已实现，20260821_0005 回填）。
- occurrence_count 为缓存字段，由 COUNT(question_instances) 驱动更新。

### 4.6 question_images

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| question_id | UUID | FK questions |
| image_key | VARCHAR | 对象存储 key |
| image_type | VARCHAR | diagram / question_image / formula_image |
| description | TEXT | |
| image_order | INTEGER | 排序 |
| page_no | INTEGER | 配图来源页码 |
| bbox | JSONB | 配图在来源页面上的坐标 |
| placement | VARCHAR | stem / options / answer / explanation / page_context |
| sub_question_qno | VARCHAR(100) | 答案图绑定的子题号，可为空 |
| source | VARCHAR | native / paddleocr / vl / manual |
| figure_id | VARCHAR | 同一物理图在文档级去重中的稳定标识 |
| created_at | TIMESTAMPTZ | |

说明：

- 物理图存储去重：同一 `figure_id` 在对象存储中只保留一份。
- 题-图关联允许多对多：共享材料题场景下，同一 `figure_id` 可通过多条 `question_images` 记录关联到多道题。
- 无显式证据的跨题广播必须抑制（详见 `V1_LESSONS.md` 3.4/3.26）。

### 4.7 question_instances

保存同一题在不同来源中的出现实例。

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| question_id | UUID | FK questions |
| document_id | UUID | FK documents，NOT NULL（Phase 2A Step 1 新增） |
| source_type | VARCHAR | document / generated / student |
| source_document_name | VARCHAR | 来源文档名（冗余保留，便于查询） |
| source_page | INTEGER | 来源页码，可为空 |
| source_question_number | VARCHAR | 来源原始题号，可为空 |
| year | INTEGER | 从 questions 迁移（Phase 2A Step 1） |
| school | VARCHAR | 从 questions 迁移（Phase 2A Step 1） |
| occurrence_no | INTEGER | 同一来源内出现序号 |
| created_at | TIMESTAMPTZ | |

说明：

- document_id 为 Phase 2A Step 1 新增，NOT NULL，替代 source_document_name 作为精确关联。
- 唯一约束：`(document_id, source_question_number)` WHERE source_question_number IS NOT NULL。
- year / school 从 questions 表迁移而来（Phase 2A Step 1）。

### 4.8 question_knowledge

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| question_id | UUID | FK questions |
| knowledge_node_id | UUID | FK knowledge_nodes |
| confidence | NUMERIC | 0-1 |
| is_primary | BOOLEAN | 是否主知识点 |
| mapping_source | VARCHAR(20) | llm / rule / manual（Phase 2A Step 1 新增） |
| review_status | VARCHAR(20) | approved / pending / rejected，默认 approved（Phase 2A Step 1 新增） |
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
| embedding | vector(2560) | pgvector，qwen3-embedding:4b |
| embedding_provider | VARCHAR | Ollama |
| embedding_dimension | INTEGER | 固定 2560 |
| created_at | TIMESTAMPTZ | |

### 4.12 wrong_upload_tasks

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| task_id | UUID | FK background_tasks |
| user_id | UUID | FK users |
| image_key | VARCHAR | 学生 JPG key |
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
| task_id | UUID | FK background_tasks |
| task_type | VARCHAR | practice / paper |
| subject | VARCHAR | |
| grade | VARCHAR | |
| parameters | JSONB | 知识点、题型、难度、题量等 |
| ratio_snapshot | JSONB | 历史比例快照 |
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

### 4.21 background_tasks

统一后台任务表。文档解析、AI 生成、导出、错题识别等异步能力共用。

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| task_type | VARCHAR | document_parse / generation / export / wrong_question / embedding |
| status | VARCHAR | queued / running / succeeded / failed / review_required |
| progress | NUMERIC | 0-1 |
| current_stage | VARCHAR | 当前阶段 |
| error_detail | TEXT | 失败原因 |
| payload_json | JSONB | 任务入参 |
| result_json | JSONB | 任务结果摘要 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### 4.22 domain_events

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| event_type | VARCHAR | QuestionCreated / QuestionReviewed 等 |
| entity_type | VARCHAR | question / wrong_question / practice_session |
| entity_id | UUID | |
| payload_json | JSONB | 事件数据 |
| created_at | TIMESTAMPTZ | |
| processed_at | TIMESTAMPTZ | 消费者处理时间，可为空 |

---

## 5. 关系

```text
documents
└── document_processing_logs

questions
├── question_images
├── question_instances
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

background_tasks
├── wrong_upload_tasks
└── generation_jobs

domain_events
└── 事件实体：question / wrong_question / practice_session
```

---

## 6. 索引建议

普通索引：

- questions(subject_id, grade, year)
- questions(question_type_id)
- questions(status, confidence)
- questions(source_type)
- question_knowledge(question_id, knowledge_node_id)
- question_instances(question_id, year)
- question_images(question_id, source, page_no)
- wrong_questions(user_id, status)
- practice_answers(session_id, question_id)
- mastery_records(user_id, knowledge_node_id)
- background_tasks(task_type, status)
- domain_events(event_type, created_at)

向量索引：
- 当前 embedding 为 2560 维，超过 pgvector HNSW 索引 2000 维上限，初始阶段不建向量索引。
- 家庭题库规模下先使用暴力余弦检索；后续如需向量索引，先做降维或更换不超过 2000 维的模型。

---

## 7. L1/L2 中间态说明

L1（行编号原文）和 L2（LLM 标注镜像）是文档解析的中间态，**不落库**。

- L1 是不可变的行编号原文，Native/OCR 输出统一为同一个 L1Document。
- L2 是 LLM 标注结果的结构化镜像，只存储行号引用和元数据。
- 最终入库的是 L3（由 L1 + L2 切片生成的题目内容）。
- L2 标注的行号经过锚点校正后，由代码从 L1 切片生成 stem/options/answer/explanation。

详细定义见 `Docs/01_Product/T3_IMPLEMENTATION.md`。

---

## 8. Phase 2A Schema（已实施）与未来 Family/Similarity 计划

> §8.1-8.3 描述的 Phase 2A schema 变更**已全部实施**（migration
> `20260821_0003`、`20260821_0005`、`20260827_0001`，2026-08-21/27 执行，
> `alembic current` 确认在 head）。当前 DB 即本节结构。
> §8.4/8.5 的 Family/Similarity 部分为**未来计划**，Phase 2D 之前不建。
> 代码审计（2026-08-21）补充：Phase 2A 还包含审核写回 DB、Worker 失败语义
> 修正、L2 完整持久化三项代码修复，详见 PLAN §7.1 和 ROADMAP P4A。

### 8.1 questions 表变更（已实施）

| 变更 | 类型 | 说明 |
|---|---|---|
| 新增 content_hash | VARCHAR(64) | 规范化文本 SHA256，用于 exact dedup。覆盖题干+选项+题型。答案/详解冲突进审核不静默覆盖。 |
| 移除 year | — | 已移到 question_instances。Question 只保留内容事实。 |
| 移除 school | — | 已移到 question_instances。 |
| occurrence_count | — | 派生值：COUNT(question_instances)。保留为缓存字段但由 Instance 驱动更新。 |

### 8.2 question_instances 表变更（已实施）

| 变更 | 类型 | 说明 |
|---|---|---|
| 新增 document_id | UUID FK documents | 替代 source_document_name 文本字段（NOT NULL）。 |
| 唯一约束 | — | 部分唯一索引 ix_question_instances_doc_qno：(document_id, source_question_number)（两者均非 NULL 时唯一）。 |

### 8.3 question_knowledge 表变更（已实施）

| 变更 | 类型 | 说明 |
|---|---|---|
| 新增 mapping_source | VARCHAR | llm / rule / manual，记录映射来源。 |
| 新增 review_status | VARCHAR | approved / pending / rejected，低置信度映射进审核。 |

综合题（is_composite=true）子题级知识点映射已承载：父题 `questions.sub_questions`
JSONB 字段关联（Phase 2A 实现时决定并落地）。

### 8.4 暂不建的表（未来计划）

以下表在 Phase 2D 之前不建：

| 表 | 推迟原因 |
|---|---|
| question_families | Family 定义未确定，建表会锁死模型 |
| question_similarity | Similarity 引擎未实现 |
| question_annotations（独立表） | 当前 llm_annotated_markdown JSON 足够 |

### 8.5 设计原则（已实施 vs 未来）

已实施：

| 原则 | 说明 |
|---|---|
| Annotation ≠ 事实 | LLM 输出的标注都带 source/confidence/version |
| Structure Signature 存 L2 JSON | 不进 questions 主表，存在 llm_annotated_markdown 中 |

未来（Family/Similarity 引擎落地时生效）：

| 原则 | 说明 |
|---|---|
| Primary Family 唯一归属 | 每道题只有一个 Primary Family，用于统计报表 |
| Family Membership N:M | 一道题可以属于多个 Family，用于检索/分析 |
| Knowledge Point ≠ Family | 同知识点不同任务属于不同 Family |

---

## 9. 一致性要求

DSD 必须与以下文档保持一致：

- PRD.md
- SAD.md
- ACS.md
- MIS.md
- PIPELINE.md

冲突时：

- 产品范围以 REQUIREMENTS_AND_SOLUTION.md 为准。
- 数据库结构以本文件为准。

---

## 10. 变更记录

### 2026-08-11

- `documents.processing_status` 枚举补充 `failed`，与后台任务失败状态一致。

### 2026-08-11 07:07:42

- 固化 V1 教训：`documents` 增加 L1 Native/OCR Markdown 字段。
- `question_images` 增加 `page_no/bbox/placement/source/figure_id`，用于无猜图、文档级去重和来源可追溯。

### 2026-08-11

- 版本升至 4.5：`question_images` 多对多语义说明（物理图存储去重 + 题图关联多对多 + 无证据广播抑制）。
- 新增 L1/L2 中间态说明（不落库，详见 T3_IMPLEMENTATION.md）。

### 2026-08-21

- 新增 §8 Phase 2A 设计冻结：questions 移除 year/school、新增 content_hash、occurrence_count 改派生；question_instances 新增 document_id FK（NOT NULL）+ 部分唯一索引（WHERE source_question_number IS NOT NULL）；question_knowledge 新增 mapping_source/review_status。
- 明确暂不建 question_families、question_similarity、独立 question_annotations 表。
- 冻结设计原则：Primary Family 唯一归属、KP ≠ Family、Annotation ≠ 事实、Structure Signature 存 L2 JSON。

### 2026-08-21

#### Phase 2A Step 1 实施

- questions 表：移除 year/school 列，新增 content_hash VARCHAR(64)。
- question_instances 表：新增 document_id UUID FK documents（nullable），部分唯一索引 ix_question_instances_doc_qno（WHERE document_id IS NOT NULL AND source_question_number IS NOT NULL）。
- question_knowledge 表：新增 mapping_source VARCHAR(20)、review_status VARCHAR(20) DEFAULT 'approved'。
- 索引变更：ix_questions_subject_grade_year → ix_questions_subject_grade（移除 year），新增 ix_questions_content_hash。
- Alembic migration：20260821_0003_phase2a_data_foundation.py。
- 版本升至 4.6。

### 2026-08-27（P0 文档状态修正）

- **§8 状态漂移修正**：标题/引言去掉「待实现/当前 DB 仍为旧结构」表述，改为
  「已实施 + 未来计划」；§8.1-8.3 标注已实施（migration 20260821_0003/0005、
  20260827_0001，`alembic current` 在 head）；§8.5 拆分为「已实施原则」与
  「未来 Family/Similarity 原则」。
- §4.5 两处过时说明同步修正：content_hash「当前可为 NULL」→「Step 5 已实现，
  可为 NULL（历史数据）」；「本步只加列」→「Step 5 已实现，20260821_0005 回填」。


### 2026-08-28 23:50:00

- 新增 questions.original_question_type VARCHAR(50)：保留 LLM 原始细粒度题型（cloze/grammar_fill/seven_to_five/essay/writing 等）。
- 新增 questions.section_id VARCHAR(100)：保留卷面 section/共享材料区标识。
- Alembic migration：20260828_0001_add_question_original_type_section.py。


### 2026-08-29 00:05:00

- questions.sub_questions JSONB 支持递归 sub_sub_questions，用于化学综合题 ⅠⅡⅢⅣ / ①②③④ 等多层子问。
- P0-3 实现：L2QuestionAnnotation/L2SubQuestion 递归结构、line_annotator 解析、content_slicer 切片、ingestion 序列化、前端递归渲染。


### 2026-08-29 00:15:00

- questions 新增 answer_structure JSONB：保存结构化答案（可包含 accepted_answers/range 等），原始答案仍保留在 answer TEXT。
- Alembic migration：20260829_0001_add_question_answer_structure.py。


### 2026-08-29 00:35:00

- questions 新增 word_bank JSONB：词库独立存储，单题与多题词库路径均支持。
- Alembic migration：20260829_0002_add_question_word_bank.py。
- P0-1 统计补强：入库优先使用 original_question_type 建立细粒度 question_type_id。

### 2026-08-29 12:30:00

- P0-2：essay/writing 作为原始细粒度 code 入库，question_type_id 可创建 essay/writing；无 schema 变更。
- P1-3：填空位标记增加普通数字上下文保护，英语正文数字误标风险收敛。
- P1-4：七选五 A-G 标签完整性进入锚点校验，缺失时 retry。
- P2-2：前端展示层增强，不涉及数据 schema。

### 2026-08-29 15:30:00

- P1-2：question_images 新增 sub_question_qno VARCHAR(100)，用于答案图子题粒度绑定；Alembic migration 20260829_0003。
- P0-5：化学式文本标准化，无 schema 变更。

