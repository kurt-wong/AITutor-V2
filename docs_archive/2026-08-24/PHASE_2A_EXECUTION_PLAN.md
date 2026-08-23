# Phase 2A 严格执行计划（DSH 控制版）

Version: 1.1
Date: 2026-08-21
Status: Phase 2A 总验收通过（测试缺口已补齐；Step 6 降级口径确认）。
Baseline:

- `Docs/01_Product/PLAN_QUESTION_FAMILY.md` v2.0 §7.1
- `Docs/01_Product/ROADMAP.md` v2.0 P4A
- `Docs/03_Data/DSD.md` v4.6

本文件用于约束 DSH 的后续执行。任何 Step 只有在“代码、migration、测试、真实数据库验证”四者全部闭合后才能标记完成。

---

## 0. DSH 强制执行规则

1. 执行前必须读取 `Docs/01_Product/PLAN_QUESTION_FAMILY.md`、`Docs/03_Data/DSD.md`、`Docs/01_Product/ROADMAP.md` 和本文件。
2. 任何 Step 标记完成前，必须在汇报中粘贴实际命令输出，不能写“已验证”“测试通过”“预期成功”代替证据。
3. `alembic upgrade head --sql` 只是语法检查，不代表 migration 已执行。只有 `python -m alembic current` 显示目标 revision 才算 migration 完成。
4. pytest 必须写具体数字和失败用例名。不允许用“pre-existing”掩盖本步引入的失败；必须给出同一基线命令和失败 traceback。
5. 改 schema 必须同时包含 SQLAlchemy model、Alembic migration、单元测试、真实数据库验证。
6. 不得为了通过测试而放宽验收标准、删除断言或修改测试预期。
7. 每步只改本步范围。Step 未验收不得进入下一步。
8. 遇到环境无法验证时，标记 `blocked` 并停止，不得自行降级为“完成”。
9. 文档更新必须与代码事实一致。禁止先写“完成”再补代码。
10. 本阶段禁止新增 Family、Similarity、Embedding、DOCX、产品 CRUD、错题、练习等功能。
11. 全量 pytest 统一使用“根目录 + 注入 backend/.env 的 DATABASE_URL”命令；后续文中写 `python -m pytest backend\tests -q` 时均指该稳定命令。

---

## 1. Step 0：Step 1 复核与数据回填证据补全

目标：

确认 Step 1 的 migration、model、ingestion、测试都真实成立，并补齐尚未验证的数据回填证据。DSH 不得把“文档里写了完成”当成验收证据。

当前已确认的事实：

- `alembic current` 已为 `20260821_0003`，migration 已应用。
- `question_instances.document_id` 在 model 和 DB 中均为 NOT NULL。
- migration 已使用 COALESCE 回填 year/school，并执行 `op.alter_column(..., nullable=False)`。
- `backend/tests/test_phase2a_step1.py` 已存在。
- `backend/tests/test_phase2a_step0_integration.py` 本身仍不执行 migration；真实回填演练由 `test_phase2a_step0_migration_rehearsal.py` 覆盖。
- 当前全量 pytest 稳定命令实际结果为 **520 passed，0 failed**。
- 当前 `question_instances` 表为 0 行，因此“真实数据回填成功”仍没有被数据验证过。

本步必须补齐的证据：

- 在测试数据库或一次性临时数据库中构造以下数据：
  - 2 个 document，其中 filename 与 Instance.source_document_name 匹配。
  - 3 个 question，覆盖 year/school 缺失的边界。
  - 同一 document 下同一 source_question_number 重复的负面用例。
- 必须先构造旧 schema 数据（Instance 没有 document_id 列），再实际执行 `alembic upgrade`。不能只在当前 schema 插入带 `document_id` 的 Instance 后断言相等。
- 实际执行 migration upgrade，验证：
  - 所有 document 来源 Instance 的 document_id 被正确回填。
  - year/school 使用 COALESCE，不清空 Instance 已有值。
  - `questions.year/school` 被删除。
  - 唯一索引拒绝重复 `(document_id, source_question_number)`。
- 执行 migration downgrade 后，验证 schema 能回退；如果 downgrade 不恢复数据，必须在文档中明确标注为有损，不得宣称无损。

必须新增或补全测试：

- migration 在真实 PostgreSQL 测试库上执行，而不是只读 migration 文件字符串。
- 回填测试断言 document_id、year、school 的实际数据值。
- 唯一索引负面用例实际插入重复数据并断言失败。
- ingestion 创建新 Question 时不再写 `year/school`。
- ingestion 创建 QuestionInstance 时写入 `document_id`。
- 精确匹配路径更新 `occurrence_count` 后与 COUNT 一致。

验证命令：

```powershell
cd D:\Project\AITutors-v2\backend
python -m alembic current
python -m alembic heads
python -m alembic upgrade head
python -m alembic current
```

必须满足：

- upgrade 后 `current` 为 `20260821_0003`。
- 所有命令输出必须粘贴到汇报中。

数据库验证 SQL：

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name IN ('questions', 'question_instances', 'question_knowledge')
ORDER BY table_name, column_name;

SELECT indexname
FROM pg_indexes
WHERE tablename = 'question_instances'
  AND indexname = 'ix_question_instances_doc_qno';

SELECT count(*)
FROM question_instances
WHERE source_type = 'document'
  AND document_id IS NULL;

SELECT count(*)
FROM question_instances
WHERE source_type = 'document'
  AND source_question_number IS NOT NULL
GROUP BY document_id, source_question_number
HAVING count(*) > 1;

SELECT count(*)
FROM questions
WHERE year IS NOT NULL OR school IS NOT NULL;
```

完成判定：

- `alembic current` 等于 `20260821_0003`。
- 数据回填测试在真实 PostgreSQL 上通过。
- 文档来源 Instance 的 `document_id` 全部非 NULL。
- 唯一索引内无重复，且重复插入被拒绝。
- `questions.year/school` 为 0 行残留。
- 全量测试必须使用以下稳定命令从项目根目录运行，结果为 **520 passed，0 failed**，以实际输出为准：

```powershell
cd D:\Project\AITutors-v2
$env:DATABASE_URL = (Select-String -Path backend\.env -Pattern '^DATABASE_URL=').Line -replace '^DATABASE_URL=',''
python -m pytest backend\tests -q
```

- PROJECT_STATUS 中的测试数字必须改为实际输出，禁止继续使用 432。

---

## 2. Step 2：审核决定写回 DB

目标：

管理员审核后，`questions.status` 和 `review_overrides` 真实写入数据库，而不是只写 `task.result_json`。

改动范围：

- `backend/app/application/services.py` 的 `update_document_review`。
- `backend/app/api/routes/documents.py` 审核接口。
- 必要时新增 repository 查询方法。

必须新增测试：

- 审核通过后 `questions.status = 'approved'`。
- 审核驳回后 `questions.status = 'rejected'`。
- `review_overrides` 中的 `stem/options/answer/explanation` 写回对应 Question。
- 题目定位使用 `question_instances(document_id, source_question_number)`，不能用任意同号题。
- `task.result_json` 和 `questions` 表同时更新。

验证命令：

```powershell
python -m pytest backend\tests -q
```

数据库验证 SQL：

```sql
SELECT q.id, q.status, q.stem, q.answer
FROM questions q
JOIN question_instances qi ON qi.question_id = q.id
WHERE qi.document_id = '<document_id>'
  AND qi.source_question_number = '<question_number>';
```

完成判定：

- DB 查询返回管理员审核后的状态和内容。
- 更新的题目确实属于指定 `document_id + question_number`。
- 全量测试通过。

---

## 3. Step 3：Worker 失败语义 + L2 完整持久化

目标：

修正 Worker 把失败当成功的语义，并确保 `llm_annotated_markdown` 保存完整 L2 Annotation。

改动范围：

- `backend/app/worker/document_worker.py`。
- `backend/app/domains/document/processor.py`。
- L2 Annotation JSON 的保存字段。

必须新增测试：

- ingestion 抛出真实异常时，`background_tasks.status = 'failed'`，`documents.processing_status = 'failed'`。
- 答案提取失败时，任务状态仍为 `succeeded`，答案进入 retry queue。
- `llm_annotated_markdown` 包含 `knowledge_points/difficulty/score/corrected_anchors/anchor_status/question_type`。
- 同一文档重跑时，只清理 `source_type = 'document'` 且 `status = 'reviewing'` 的未审核记录。
- 已审核记录和 `review_overrides` 非空记录不被静默覆盖。
- **同一 Question 跨文档共享时，清理一个文档不影响另一个文档的 Instance 和 Question**（只删当前 document_id 下的 Instance；Question 仅在无剩余 Instance 时才删除；有剩余 Instance 时更新 `occurrence_count`）。

验证命令：

```powershell
python -m pytest backend\tests -q
```

数据库验证 SQL：

```sql
SELECT id, status, error_message
FROM background_tasks
WHERE id = '<task_id>';

SELECT id, processing_status
FROM documents
WHERE id = '<document_id>';

SELECT llm_annotated_markdown
FROM documents
WHERE id = '<document_id>';
```

完成判定：

- 异常路径任务为 `failed`，文档为 `failed`。
- 答案提取失败仍走 retry queue，任务为 `succeeded`。
- L2 JSON 字段完整。
- 幂等重跑不会覆盖已审核数据。

---

## 4. Step 4：答案重试关联修正

目标：

答案重试 worker 不再使用 `source_document_name + 顺序` 猜测题目，改为 `document_id + question_instances` 精确关联。

改动范围：

- `backend/app/worker/answer_retry_worker.py`。
- 必要时修正 `backend/app/domains/document/retry_repository.py`。

必须新增测试：

- 同一文档有 3 道空答案题，重试后每道题更新到正确 Question。
- 不同文档有相同题号时，不会互相污染。
- `document_id` 或 `source_question_number` 找不到 Instance 时，记录失败而不是更新错误题目。

验证命令：

```powershell
python -m pytest backend\tests -q
```

数据库验证 SQL：

```sql
SELECT qi.document_id, qi.source_question_number, q.answer
FROM question_instances qi
JOIN questions q ON q.id = qi.question_id
WHERE qi.document_id = '<document_id>'
ORDER BY qi.source_question_number;
```

完成判定：

- 每个题号更新到对应 Question。
- 全量测试通过。

---

## 5. Step 5：精确去重 content_hash

目标：

把去重从“只看 stem”升级为“规范化题干 + 选项 + 题型”的 SHA256，并正确处理答案冲突。

前置条件：

先冻结以下设计，更新 DSD 后再写代码：

- content_hash 的规范化规则。
- 答案冲突记录的承载方式，禁止临时发明表结构。
- 综合题是否参与同一 hash 规则。

改动范围：

- 新增 content_hash 规范化与计算函数。
- `backend/app/domains/document/ingestion.py` 去重逻辑。
- 冲突记录写入逻辑。
- 已有数据回填 migration。

必须新增测试：

- 同一 PDF 上传两次，第二次只创建 Instance，不创建新 Question。
- 题干相同但选项不同，创建不同 Question。
- 题干、选项、题型相同但答案不同，不创建重复 Question，产生审核冲突。
- 回填后 `questions.content_hash` 无 NULL。
- 规范化规则对空白、标点、换行、Unicode 有确定性。

验证命令：

```powershell
python -m pytest backend\tests -q
```

数据库验证 SQL：

```sql
SELECT content_hash, count(*) AS question_count
FROM questions
GROUP BY content_hash
HAVING count(*) > 1;

SELECT count(*)
FROM questions
WHERE content_hash IS NULL;
```

完成判定：

- 同内容只对应一个 Question。
- 答案冲突产生可查询的审核记录，`review_reason` 持久化冲突详情（格式：`answer_conflict:<来源文档名>:<冲突答案>`，供管理员审核时参考）。
- 全量测试通过。

---

## 6. Step 6：知识点映射落库

目标：

打通 `Question -> question_knowledge -> knowledge_nodes`，让知识点频率统计真正有数据支撑。

改动范围：

- `backend/app/domains/document/ingestion.py`。
- 新增或扩展 KnowledgeService 的映射方法。
- 低置信度映射状态。
- 综合题子题级映射。

必须新增测试：

- 入库一道题后，`question_knowledge` 能关联到正确 `knowledge_nodes`。
- 低置信度映射的 `review_status = 'pending'`。
- `mapping_source` 为 `rule`（关键词匹配路径）或 `rule`（UNKNOWN 回退路径）。
- 综合题子题映射到不同知识点。
- 知识树为空或匹配不到时，不静默跳过，必须进入可审核状态（UNKNOWN 回退 + pending）。

> **验收口径说明（2026-08-22 对抗性审查后降级）：**
> PLAN §7.1 Step 6 原文要求「关键词匹配 + LLM 兜底」。经评估，LLM 兜底引入异步调用复杂度、API 成本和延迟，而 333 节点关键词索引 + UNKNOWN 回退 + pending 审核已覆盖主要场景。
> Phase 2A 采用「规则匹配 + UNKNOWN 回退」，`mapping_source` 统一为 `rule`。
> LLM 兜底（`mapping_source='llm'`）推迟到 Phase 2D，与 Similarity/Family 研究同步实现。

验证命令：

```powershell
python -m pytest backend\tests -q
```

数据库验证 SQL：

```sql
SELECT kn.code, kn.name, qk.confidence, qk.mapping_source, qk.review_status
FROM question_knowledge qk
JOIN knowledge_nodes kn ON kn.id = qk.knowledge_node_id
WHERE qk.question_id = '<question_id>';
```

完成判定：

- 题目能查到知识树节点。
- 低置信度记录进入 `pending`。
- 综合题子题映射正确。
- 无命中时回退 `{SUBJ}-UNKNOWN` + `pending`（不静默跳过）。
- 全量测试通过。

---

## 7. Phase 2A 总验收

总验收命令：

```powershell
cd D:\Project\AITutors-v2
python -m pytest backend\tests -q
```

总验收 SQL：

```sql
SELECT 'duplicate_instance' AS check_name, count(*) AS bad_rows
FROM question_instances
WHERE source_type = 'document'
  AND source_question_number IS NOT NULL
GROUP BY document_id, source_question_number
HAVING count(*) > 1

UNION ALL

SELECT 'null_document_id', count(*)
FROM question_instances
WHERE source_type = 'document'
  AND document_id IS NULL

UNION ALL

SELECT 'null_content_hash', count(*)
FROM questions
WHERE content_hash IS NULL

UNION ALL

SELECT 'unmapped_question', count(*)
FROM questions q
WHERE q.source_type = 'document'
  AND NOT EXISTS (
    SELECT 1
    FROM question_knowledge qk
    WHERE qk.question_id = q.id
  );
```

总验收标准：

- pytest 为 437+ passed，0 failed，以实际输出为准。
- 同一文档两次上传只创建 Instance。
- 知识点映射到知识树节点。
- 审核后 `questions.status` 和内容真实变化。
- Worker 异常标 `failed`，答案提取失败走 retry queue。
- `llm_annotated_markdown` 包含完整 L2 Annotation。
- 答案冲突不产生重复 Question。
- 文档来源 Instance 的 `document_id` 全部非 NULL。
- `questions.content_hash` 无 NULL。

---

## 8. DSH 每步汇报模板

每个 Step 完成后，必须按以下格式汇报，不能省略：

```text
Step N 汇报

改动文件：
- <file>

新增/修改测试：
- <test_name>

实际命令输出：
<粘贴完整输出，不允许只写结论>

DB 验证输出：
<粘贴 SQL 结果>

未解决问题：
- <none 或具体问题>

状态：
- 可进入下一步 / blocked
```

如果 DSH 写“测试通过”但没有粘贴命令输出，或写“migration 成功”但 `alembic current` 不是目标 revision，视为未完成，不得进入下一步。
