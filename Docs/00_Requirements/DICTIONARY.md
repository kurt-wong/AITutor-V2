# AI Tutor Personal Edition — 项目字典

Version: 1.0
Status: 开发指引基线（Phase 2 设计已冻结）
Date: 2026-08-21

---

## 1. 用途

本文件用于统一项目沟通中的字段名、功能名和概念名。

所有文档、代码、接口、聊天和任务描述尽量使用本字典中的名称。出现新字段或新功能时，必须同步更新本文件，并在文末“更新记录”追加完整时间戳。

---

## 2. 命名约定

| 场景 | 约定 |
|---|---|
| 数据库字段 | 小写 snake_case |
| 后端字段 | 小写 snake_case |
| API JSON 字段 | 小写 snake_case |
| 枚举值 | 小写 snake_case |
| 类型/领域对象 | PascalCase |
| 文件路径 | 沿用现有目录结构 |

示例：

```text
question_id
source_type
review_status
background_task
Question Aggregate
```

---

## 3. 角色

| 字段/名称 | 含义 |
|---|---|
| admin | 管理员，维护文档、题库、审核、统计、配置和 AI 生成 |
| student | 学生，上传错题、做练习、查看错题本和学习统计 |

---

## 4. 核心概念

| 名称 | 含义 |
|---|---|
| Question Aggregate | 一道题的完整档案，包含内容、配图、元数据、来源、质量和统计 |
| Question Instance | 同一道题在某份来源文档或某个错题场景中的一次出现实例 |
| Background Task | 统一后台任务，用于文档解析、AI 生成、导出、错题识别等异步能力 |
| Domain Event | 系统内部事件，用于解耦统计、推荐、Agent 和学习分析 |
| Knowledge Tree | 管理员维护的标准知识点树，AI 只能映射，不能随意创建节点 |
| Question Type | 按学科维护的细粒度题型规范 |
| OcrPage | PP-StructureV3/OCR 输出的一页 Markdown、公式、表格与图片引用 |
| ParsedQuestion | 文档解析后尚未入库的结构化题目草稿 |
| Question Aggregate JSON | 文档解析与 AI 生成共用的结构化题目交换格式 |
| Native L1 | PyMuPDF 从 PDF 文本层提取的 raw L1，用于页面尺寸、图片 xref/bbox、答案表定位、上下标几何 |
| PPSV3 L1 | PP-StructureV3 从视觉版面识别生成的 raw L1，用于公式符号、复杂版面、扫描页 |
| Canonical L1 | 代码按证据从 Native/PP 双源选择后的最终 L1，每行保留 source/provenance/confidence |
| L1 Source Arbitration | LLM 行级仲裁：输出 line_id、候选 source、冲突结论、evidence，不生成 L1 原文 |
| L1 Markdown | Native L1 或 PPSV3 L1 统一生成的 canonical L1，作为 LLM 标注的不可变原文来源 |
| L2 Annotation Mirror | 保存 LLM 行号/题型/答案位置等标注，不保存 LLM 抄写的题目原文 |
| Line-range Annotation | LLM 输出粗略行号范围，代码从 L1 原文切片生成内容的标注范式 |
| Coarse Line Range | LLM 输出的粗略行号/行范围，不作为最终切片边界 |
| Anchor Correction | 代码根据题号、选项、答案、详解等稳定标记校正 LLM 粗略行号 |
| Corrected Anchor | 锚点校正后的最终行号范围，供代码切片和 L2 落库使用 |
| Anchor Status | 锚点校正状态：exact / nearest / missing / retry |
| Image Placement | 配图在文档中的位置元数据：`page_no/bbox/placement/source` |
| Source Provenance | 题目/答案/详解/图片的来源与生成方式，用于可追溯和审核 |
| Document Artifact Layer | L0 原始文档、L1 原文 Markdown、L2 标注镜像、L3 渲染层的分层架构 |
| Review Queue | 低置信度或待确认内容进入的人工审核队列 |
| Wrong Question Book | 学生的错题本 |
| Practice Session | 一次练习批次 |
| Mastery Level | 学生在某知识点上的掌握程度 |
| Generation Task | AI 生成练习或试卷的任务 |
| content_hash | 规范化文本的 SHA256，用于精确去重。覆盖题干+选项+题型。 |
| mapping_source | 知识点映射来源：llm / rule / manual |
| review_status | 映射审核状态：approved / pending / rejected |
| Structure Signature | LLM 提取的题目结构特征（object/task/method/condition_text），是 Annotation 不是事实 |
| Annotation ≠ 事实 | Question 是事实（不可变），LLM 输出的标注是对事实的解释（可能随 prompt 版本变化） |
| Question Family | 一组结构/解法高度相似的题构成的族（Phase 2D 实现，暂不建表） |
| Primary Family | 每道题唯一的统计归属 Family（Phase 2D 实现） |
| 统计视图 ≠ Family | Knowledge Point × Question Type × Year 是统计视图，不是 Family |
| Exact Duplicate | 文本 hash 完全相同的题，合并为同一 Question 的不同 Instance |
| Similarity | 两道不同题之间的相似关系（Phase 2D 实现） |
| Agent Interface | 供 Codex/Claude 等智能体调用的可选 MCP 接口层 |
| L1Line | L1 行模型：带页码的稳定行 ID（PP 用 P1L001，Native 用 N1L001，canonical 保留 PP 行号），L1 原文不可变 |
| L1Document | L1 文档模型：Native/OCR 统一输出，LLM 只面对这一层 |
| L2QuestionAnnotation | L2 单题标注：题号、题型、section、stem_line_ids、options_line_ids，不含答案行号 |
| Quality Gate | 按题评估质量：切分完整、选项数量、答案匹配、anchor_status，失败不整批丢弃 |

---

## 5. 字段字典

### 5.1 users

| 字段 | 含义 |
|---|---|
| id | 用户 ID |
| username | 登录名 |
| password_hash | 密码哈希 |
| role | 用户角色：admin / student |
| created_at | 创建时间 |
| updated_at | 更新时间 |

### 5.2 documents

| 字段 | 含义 |
|---|---|
| id | 文档 ID |
| filename | 原始文件名 |
| file_type | 文件类型：pdf / docx |
| object_key | 对象存储中的文件 key |
| subject | 上传时填写的学科 |
| grade | 上传时填写的年级 |
| year | 上传时填写的年份 |
| school | 上传时填写的学校 |
| upload_status | 上传状态 |
| processing_status | 处理状态 |
| error_message | 失败原因 |

### 5.3 questions

| 字段 | 含义 |
|---|---|
| id | 题目 ID |
| subject_id | 学科 ID |
| grade | 年级 |
| question_type_id | 题型 ID |
| score | 分值 |
| difficulty | 难度 1-5 |
| stem | 题干 |
| options | 选项 |
| answer | 标准答案 |
| explanation | 详解 |
| content_hash | 规范化文本 SHA256（Phase 2A 新增） |
| source_type | 题目来源：document / generated / student |
| source_document_name | 来源文档名 |
| status | 题目状态 |
| confidence | 置信度 0-1 |
| occurrence_count | 出现次数（Phase 2A 改为派生值） |
| created_at | 创建时间 |
| updated_at | 更新时间 |

> Phase 2A：移除 year/school（移到 question_instances），新增 content_hash，occurrence_count 改为 COUNT(instances) 派生。

### 5.4 question_instances

| 字段 | 含义 |
|---|---|
| id | 出现实例 ID |
| question_id | 关联题目 ID |
| document_id | 来源文档 ID（Phase 2A 新增，替代 source_document_name） |
| source_type | 来源类型 |
| source_document_name | 来源文档名（Phase 2A 后由 document_id 替代） |
| source_page | 来源页码 |
| source_question_number | 来源原始题号 |
| year | 来源年份 |
| school | 来源学校 |
| occurrence_no | 同来源内出现序号 |

> Phase 2A：新增 document_id FK，加 (document_id, source_question_number) 唯一约束。

### 5.5 question_images

| 字段 | 含义 |
|---|---|
| id | 图片关联 ID |
| question_id | 关联题目 ID |
| image_key | 图片对象存储 key |
| image_type | 图片类型：diagram / question_image / formula_image |
| description | 图片描述 |
| image_order | 图片排序 |
| page_no | 配图来源页码 |
| bbox | 配图在来源页面上的坐标 |
| placement | 配图位置：stem / options / answer / explanation / page_context |
| source | 配图来源：native / paddleocr / vl / manual |
| figure_id | 同一物理图在文档级去重中的稳定标识 |

### 5.6 knowledge_nodes

| 字段 | 含义 |
|---|---|
| id | 知识点节点 ID |
| subject_id | 学科 ID |
| parent_id | 父节点 ID |
| code | 节点编码 |
| name | 节点名称 |
| level | 节点层级 |
| description | 节点说明 |

### 5.7 question_knowledge

| 字段 | 含义 |
|---|---|
| id | 映射 ID |
| question_id | 题目 ID |
| knowledge_node_id | 知识点节点 ID |
| confidence | 映射置信度 |
| is_primary | 是否主知识点 |
| mapping_source | 映射来源：llm / rule / manual（Phase 2A 新增） |
| review_status | 审核状态：approved / pending / rejected（Phase 2A 新增） |

### 5.8 question_types

| 字段 | 含义 |
|---|---|
| id | 题型 ID |
| subject_id | 学科 ID |
| parent_id | 父题型 ID |
| code | 题型编码 |
| name | 细粒度题型名 |
| sort_order | 排序 |

### 5.9 question_embeddings

| 字段 | 含义 |
|---|---|
| id | embedding ID |
| question_id | 题目 ID |
| embedding | 向量 |
| embedding_provider | embedding Provider |
| embedding_dimension | 固定 2560（qwen3-embedding:4b） |

### 5.10 background_tasks

| 字段 | 含义 |
|---|---|
| id | 任务 ID |
| task_type | 任务类型 |
| status | 任务状态 |
| progress | 进度 0-1 |
| current_stage | 当前阶段 |
| error_detail | 失败原因 |
| payload_json | 任务入参 |
| result_json | 任务结果摘要 |
| created_at | 创建时间 |
| updated_at | 更新时间 |

### 5.11 domain_events

| 字段 | 含义 |
|---|---|
| id | 事件 ID |
| event_type | 事件类型 |
| entity_type | 实体类型 |
| entity_id | 实体 ID |
| payload_json | 事件数据 |
| created_at | 事件时间 |
| processed_at | 消费时间 |

### 5.12 wrong_questions

| 字段 | 含义 |
|---|---|
| id | 错题记录 ID |
| user_id | 学生 ID |
| question_id | 题目 ID |
| source_type | 来源：practice / jpg_upload |
| error_type | 错误类型 |
| wrong_count | 错题次数 |
| last_wrong_time | 最近错题时间 |
| mastery_status | 掌握状态 |
| review_count | 复习次数 |
| last_review_at | 最近复习时间 |

### 5.13 practice_sessions

| 字段 | 含义 |
|---|---|
| id | 练习批次 ID |
| user_id | 学生 ID |
| trigger_type | 触发方式：manual / recommendation / admin |
| question_count | 题目数量 |
| status | 练习状态 |
| started_at | 开始时间 |
| completed_at | 完成时间 |

### 5.14 practice_answers

| 字段 | 含义 |
|---|---|
| id | 作答记录 ID |
| session_id | 练习批次 ID |
| question_id | 题目 ID |
| question_snapshot | 题目快照 |
| student_answer | 孩子答案 |
| is_correct | 是否正确 |
| duration_seconds | 用时 |
| knowledge_point_ids | 关联知识点 |

### 5.15 mastery_records

| 字段 | 含义 |
|---|---|
| id | 掌握度记录 ID |
| user_id | 学生 ID |
| knowledge_node_id | 知识点节点 ID |
| mastery_level | 掌握等级 |
| total_attempts | 总尝试次数 |
| correct_count | 正确次数 |
| recent_correct_rate | 近期正确率 |

### 5.16 generation_jobs

| 字段 | 含义 |
|---|---|
| id | 生成任务业务 ID |
| task_id | 统一后台任务 ID |
| task_type | 生成类型 |
| subject | 学科 |
| grade | 年级 |
| parameters | 生成参数 |
| ratio_snapshot | 比例快照 |

### 5.17 generation_results

| 字段 | 含义 |
|---|---|
| id | 生成结果 ID |
| job_id | 生成任务业务 ID |
| question_id | 生成题 ID |
| review_status | 审核状态 |
| review_comment | 审核意见 |

### 5.18 system_configs

| 字段 | 含义 |
|---|---|
| id | 配置 ID |
| config_key | 配置键 |
| config_value | 配置值 |
| description | 配置说明 |
| updated_at | 更新时间 |

---

## 6. 功能字典

| 功能 | 描述 | 归属 |
|---|---|---|
| 文档上传与解析 | 上传 PDF/DOCX，提取题目、配图、答案、详解和元数据 | admin |
| 人工审核 | 对低置信度题目、生成题、JPG 错题进行确认或修正 | admin |
| 题库管理 | 查询、查看、编辑、删除题目和配图 | admin |
| 去重合并 | 将同一题的出现实例合并为一道题 | 系统 |
| 统计与分析 | 题型、年份、知识点、难度、错题、学习趋势统计 | admin / student |
| AI 生成实验 | 输入知识点、题型、难度，生成单题实验，不自动入库 | admin |
| AI 完整生成 | 根据趋势、频率、占比生成新题，审核后入库 | admin |
| 试卷导出 | 导出学生版试卷，以及答案和详解独立版 | admin |
| 错题上传 | 学生上传 JPG，系统自动切分、识别、匹配或新建 | student |
| 错题本 | 列表、筛选、详情、重练、标记已掌握 | student |
| 练习 | 生成练习、作答、自动判分、记录历史 | student |
| 学习统计 | 查看错题趋势、掌握度和薄弱点 | student |
| 系统配置 | 管理 API Key、模型路由、知识树、题型规范 | admin |
| 系统健康检查 | 返回后端运行状态和当前环境 | system |
| Agent 接口 | 可选 MCP Tool，供 Codex/Claude 等调用系统能力 | agent |

---

## 7. 状态枚举

| 枚举 | 取值 | 含义 |
|---|---|---|
| source_type | document / generated / student | 题目来源 |
| question_status | approved / reviewing / rejected | 题目状态 |
| task_status | queued / running / succeeded / failed / review_required | 后台任务状态 |
| review_status | pending / approved / rejected | 审核状态 |
| mastery_status | mastered / reviewing / not_mastered | 掌握状态 |
| upload_status | queued / processing / completed / failed | 上传状态 |
| processing_status | pending / parsing / annotating / reviewing / completed / failed / scanned | 文档处理状态（scanned=扫描版 PDF，2026-08-25 新增，跳过 OCR 后续集中处理） |
| trigger_type | manual / recommendation / admin | 练习触发方式 |

---

## 8. 事件类型

| 事件 | 含义 |
|---|---|
| DocumentUploaded | 文档已上传并进入解析队列 |
| DocumentRetryQueued | 文档已重新进入解析队列 |
| TaskQueued | 后台任务已重新入队 |
| QuestionCreated | 题目已创建 |

---

## 9. 更新记录

### 2026-08-10 22:17:19

- 创建本文件，用于统一项目字段、功能和状态枚举。

### 2026-08-10 22:41:06

- 新增“系统健康检查”功能条目。

### 2026-08-11

- 补充 `processing_status` 的 `failed` 状态。
- 新增事件类型字典：文档上传、文档重试、任务重试、题目创建。

### 2026-08-11 00:45:41

- 新增文档解析阶段概念：`OcrPage`、`ParsedQuestion`、`Question Aggregate JSON`。
- 同步 P2 文档解析验证使用的结构化交换格式约定。

### 2026-08-11 07:07:42

- 新增 V1 教训固化概念：`Native Markdown`、`L1 Markdown`、`L2 Annotation Mirror`、`Line-range Annotation`、`Image Placement`、`Source Provenance`、`Document Artifact Layer`。
- 补充 `question_images.page_no/bbox/placement/source/figure_id` 字段语义。
- 修正更新记录章节编号为 `9`。

### 2026-08-11 07:19:47

- 明确 `Line-range Annotation` 是粗略行号标注。
- 新增 `Coarse Line Range`、`Anchor Correction`、`Corrected Anchor`、`Anchor Status`。

### 2026-08-11

- 版本升至 0.7：新增 L1/L2 数据模型概念和 Quality Gate 概念。
- 新增 `L1Line`、`L1Document`、`L2QuestionAnnotation`、`Quality Gate` 条目。

### 2026-08-11 23:49:10

- 版本升至 0.8：新增 Native L1、PPSV3 L1、Canonical L1、L1 Source Arbitration 概念。
- 修正 Native Markdown/L1 Markdown 定义，明确 PyMuPDF 为辅助源。

### 2026-08-26 08:06:54

- `processing_status` 新增 `scanned` 状态：纯扫描版 PDF（无文本层，
  text_coverage 极低）OCR 题号不可靠，标记后跳过 OCR/LLM，后续集中处理。
