# AI Tutor V2 — 题目体系与题族设计计划

Version: 2.0
Date: 2026-08-21
Status: 冻结设计稿（经 MiMo / ChatGPT / Codex 三方对齐）
Source: 项目组内多轮讨论收敛 + 跨 Agent 审查修正

---

## 0. 写这份文档的目的

本文档整理了 V2 关于"题目去重、相似题识别、题族（Question Family）、频率统计"的完整设计思路和工程计划。

**核心共识（三方一致）：**
1. Question / QuestionInstance / Similarity / Family 四层概念分层是正确的
2. 第一优先级是数据底座：题对、来源可追溯、知识点可统计
3. Family / Similarity 全部推迟到有真实数据和可验证样本集之后
4. Knowledge Point ≠ Family，这个语义隔离必须成为 V2 核心原则

---

## 1. 系统定位与数据规模

### 1.1 系统目标

家庭自用、面向高中学生的题库管理与智能辅导平台。核心价值：

> **用万级题库支撑千级有效练习。学生不可能做完所有题，系统需要基于知识点、出题频率、题型趋势等指标引导她最高效地练习。**

设计哲学：**花管理员的时间（建系统），节约学生的时间（高效练题）。**

### 1.2 数据规模预估

| 维度 | 预估 |
|---|---|
| 维护周期 | 5 年（高一到高三 + 复读/竞赛预备） |
| 学科数 | 9 科（数理化生语英政史地） |
| 试卷量级 | 千级（5 年 × 9 科 × 每科每学期 2-3 份 × 不同学校/区） |
| 题目量级 | 万级（每份试卷 20-40 题，大量跨校重叠题） |
| 管理员 | 1 人（非学科专业人员，不会人工打标签） |
| 学生 | 1-3 人 |

**关键约束：**
- 管理员不具备学科专业能力，分类/标注必须由 LLM 自动完成
- 但 Golden Set 可以由项目 owner + AI 辅助建立少量客观样例（见 §7.4）

### 1.3 现有系统状态（2026-08-21，版本 3.7）

| 模块 | 状态 | 说明 |
|---|---|---|
| 文档入库管线 | ✅ 已完成 | PDF → OCR → LLM 标注 → 入库，9 科验证通过 |
| LLM 答案提取 | ✅ 已完成 | 30 份文档、~800 题、准确率 100% |
| 去重（精确匹配） | ✅ 已完成 | stem 完全相同 → 只创建 QuestionInstance |
| 三份文档持久化 | ✅ 已完成 | native_markdown + ocr_markdown + llm_annotated_markdown |
| 知识树种子数据 | ✅ 已完成 | 333 节点、9 科、4 级深度，已入库 |
| 知识点映射落库 | ❌ 未实现 | **当前管线输出 knowledge_points 字符串但未写入 question_knowledge 表** |
| 后端测试 | ✅ 402 passed | 失败项为已知既有问题 |
| 前端审核台 | ✅ 已完成 | 解析审核、结果展示、公式渲染、配图展示 |
| 学生端 | ⬜ 轻量外壳 | Phase 3 继续 |

---

## 2. 设计思路：四个核心概念

### 2.1 概念分层

系统需要区分四个不同层次的概念：

```
Question         = 事实（一道具体题的内容和元数据）
QuestionInstance = 出现事实（这道题在哪份试卷、哪一年出现了一次）
Similarity       = 关系（两道不同题之间的相似程度和类型）
Family           = 分析结果（一组结构/解法高度相似的题构成的族）
```

**关键原则：不要让一个概念同时承担事实、关系和统计分类三种职责。**

### 2.2 Question（题目实体）

Question 只保留内容事实，不保留来源/年份/学校（那些属于 Instance）：

```
Question
├── 内容事实：stem / options / answer / explanation
├── 元数据：subject / question_type / difficulty
├── content_hash：规范化文本 hash（用于 exact dedup）
└── Knowledge Points（N:M，通过 question_knowledge 关联）
```

**Question 上不放的字段：**
- ❌ year / school / source_document — 这些属于 QuestionInstance
- ❌ structure_signature — 这是 Annotation，不是事实（见 §4）
- ❌ primary_family_id — Family 表暂不建（见 §8）
- ❌ occurrence_count — 从 COUNT(instances) 派生

### 2.3 QuestionInstance（出现实例）

同一道题在不同来源中出现，每次创建一个 Instance：

```
Question Q001
├── Instance #1：document_id=D001, page=3, question_number="5", year=2024, school="朝阳期末"
├── Instance #2：document_id=D017, page=1, question_number="3", year=2025, school="海淀一模"
└── Instance #3：document_id=D042, page=5, question_number="8", year=2026, school="西城二模"
```

**出现次数 = COUNT(instances)，不是 Question 上的静态字段。**

**Instance 唯一约束：** 同一文档内同一题号/页码不重复创建 instance。

### 2.4 Similarity（相似关系）— 暂不实现

两道题之间的关系，分为四级：

| 类型 | 含义 | 处理方式 |
|---|---|---|
| EXACT_DUPLICATE | 同一道题（文本 hash 相同） | 合并，只创建 Instance |
| NEAR_DUPLICATE | 几乎一样，仅参数/数字微调 | 独立 Question，建立相似关系 |
| FAMILY_MEMBER | 同一题型/解法结构 | 独立 Question，归入同一 Family |
| UNRELATED | 没有明显关系 | 独立 Question |

**当前只实现 EXACT_DUPLICATE（hash 去重），其余推迟。**

### 2.5 Family（题目族）— 暂不实现

一组结构/解法高度相似的题。例如：

> "已知 f(x)=x²-2x+3，求最小值"
> "已知 f(x)=2x²-4x+5，求最小值"

属于同一个 Family：**二次函数求最值**。

**核心规则（冻结为设计原则，暂不实现）：**
- 每道题只有一个 Primary Family（用于唯一统计归属）
- 可以有多个 Family Membership（用于检索和分析）
- Primary Family ≠ Knowledge Point

---

## 3. 四个相似度维度

不要把"相似题"简单理解成"同一知识点"：

| 维度 | 回答的问题 | 例子 |
|---|---|---|
| Exact Similarity | 是不是同一道题？ | 两份卷子出了同一道原题 |
| Structural Similarity | 题目结构是不是基本一样？ | 都是"二次函数求最值"，只是系数不同 |
| Semantic Similarity | 考查的问题是不是类似？ | 都在考函数性质，但一个求最值一个求零点 |
| Knowledge Similarity | 是不是相同知识点？ | 都涉及"二次函数"这个知识点 |

**这四个维度不应该合并成一个 similarity_score。**

---

## 4. Structure Signature 设计

### 4.1 核心定位

Structure Signature 是 **Annotation（模型对事实的解释）**，不是 Question 的原始事实。

```
Question = 事实（不可变）
Structure Signature = Annotation（LLM 解释，可能随 prompt 版本变化）
```

### 4.2 四层结构（仅结构化学科）

| 层级 | 含义 | 例子 |
|---|---|---|
| Object | 操作对象/数学实体 | quadratic_function / 二次函数 |
| Task | 核心要求 | find_minimum / 求最小值 |
| Method | 主要解法 | vertex_formula / 配方法 |
| Condition | 给定约束/条件 | f(x)=x²-2x+3（保留文本） |

**学科适用性：**
- ✅ 数学、物理、化学：object/task/method 自然适用
- ⚠️ 生物：部分适用（实验题有 structure，概念题不太适用）
- ❌ 英语、语文、政治、历史、地理：不强制输出，LLM 可返回 null

### 4.3 工程策略：只采集 raw，不建独立表

**不给 questions 表加 structure_signature 字段。** 原因：
- 去重合并时，后续试卷的 signature 没有地方保留（命中重复题只创建 Instance，不更新 Question）
- 违反"Question 是事实，Annotation 是解释"原则

**实际做法：**
- Structure Signature 存在于每份文档的 `llm_annotated_markdown`（L2 Annotation JSON）中
- 不做 DB migration，不建独立 Annotation 表
- 等真需要做 Similarity/Family 研究时，再根据"是否需要按实例查询"决定是建独立表还是 per-document JSON 就够

**Annotation 内容示例：**

```json
{
  "question_type": "single_choice",
  "difficulty": "medium",
  "knowledge_points": ["二次函数", "函数最值"],
  "structure_signature": {
    "object": "二次函数",
    "task": "求最小值",
    "method": "配方法",
    "condition": "f(x)=x²-2x+3",
    "confidence": 0.86,
    "source": "llm",
    "annotation_version": "structure-v1"
  }
}
```

> **命名说明（2026-08-22 Phase 2C 实现）：** §4.2 表格第四层用 Condition，本示例曾用
> `condition_text`，实现统一采用 `condition` 键（与 §4.2 表格一致）。

---

## 5. LLM 的角色定位

### 5.1 核心原则

> **LLM 负责理解，规则负责判定。**

- LLM 提取结构特征（object/task/method/condition_text）
- LLM 输出原始语义标注
- 代码做归一化、比较、聚类
- 不让 LLM 直接判断"这两道题是否相似"

### 5.2 Structure Signature 不是无争议事实

LLM 输出的 structure_signature 需要保留：
- **来源**：`source: "llm"`
- **置信度**：LLM 对自己输出的确信程度
- **版本**：prompt 版本，用于后续数据可比性
- **审核状态**：默认 unreviewed

### 5.3 为什么不让 LLM 直接判断相似

| 风险 | 例子 |
|---|---|
| 同知识点不同任务被误判为相似 | "求最小值" vs "求零点"，都是二次函数 |
| 微小改动被忽略 | "与 x 轴交点" vs "与 y 轴交点"，只改两个字 |
| LLM 输出不稳定 | 同一道题两次标注可能输出不同 task |

---

## 6. 统计体系

### 6.1 统计维度

**当前可实现（基于事实层）：**

| 维度 | 数据来源 | 回答的问题 |
|---|---|---|
| 出现频率 | QuestionInstance | 这道具体题出现过多少次？ |
| 知识点频率 | Knowledge Point × Instance × Year | 这个知识点每年考多少次？ |
| 题型频率 | Question Type × Instance × Year | 这个题型每年考多少次？ |

**未来实现（需要 Family）：**

| 维度 | 数据来源 | 回答的问题 |
|---|---|---|
| Family 频率 | Primary Family × Instance × Year | 这个题型族每年出现多少次？ |
| Method 频率 | Method × Instance × Year | 这种解法每年考多少次？ |

### 6.2 重要语义隔离

**Knowledge Point × Question Type × Year 是统计视图，不是 Family。**

例如"二次函数 + 选择题"包含求最值、求零点、求参数、判断单调性等完全不同的题型。作为统计维度有价值，但不能冒充 Family。

### 6.3 核心统计查询示例

**"二次函数知识点在 2024-2026 年的出现趋势"：**

```sql
SELECT qi.year, COUNT(*) as frequency
FROM question_instances qi
JOIN questions q ON qi.question_id = q.id
JOIN question_knowledge qk ON qk.question_id = q.id
JOIN knowledge_nodes kn ON qk.knowledge_node_id = kn.id
WHERE kn.code LIKE 'MATH-ANA-02%'
GROUP BY qi.year
ORDER BY qi.year
```

**"哪些高频知识点学生还没掌握"：**

```sql
SELECT kn.name, COUNT(*) as frequency,
       COALESCE(m.mastery_level, 0) as mastery
FROM knowledge_nodes kn
JOIN question_knowledge qk ON qk.knowledge_node_id = kn.id
JOIN questions q ON qk.question_id = q.id
JOIN question_instances qi ON qi.question_id = q.id
LEFT JOIN mastery_records m ON m.question_id = q.id
                            AND m.student_id = :student_id
GROUP BY kn.id, m.mastery_level
ORDER BY frequency DESC, mastery ASC
LIMIT 20
```

---

## 7. 工程计划

### 7.1 Phase 2A — 数据底座修复（现在做，最高优先级）

> 执行顺序有依赖，必须按序号顺序执行。每项完成后跑 `pytest backend/tests`，基线 407 passed。
> Phase 2A 验收前，不新增 Family/Similarity/Annotation 表设计变更。
> 执行控制：DSH 必须遵守 `Docs/01_Product/PHASE_2A_EXECUTION_PLAN.md`，所有完成声明必须附实际命令和 DB 验证输出。

#### Step 1：DSD 变更 + 最小入库适配

> 本步包含 model/migration 变更和入库逻辑适配，否则 migration 后现有 ingestion 代码会写旧字段导致测试不可能全绿。

**Migration 变更：**

| 变更 | 说明 |
|---|---|
| questions 新增 content_hash | VARCHAR(64)，本步只加列，Step 5 再实现 hash 逻辑 |
| questions 移除 year | 数据迁移到 question_instances |
| questions 移除 school | 数据迁移到 question_instances |
| questions.occurrence_count | 改为缓存字段，由 Instance COUNT 驱动更新 |
| question_instances 新增 document_id | UUID FK documents |
| question_instances 唯一约束 | (document_id, source_question_number) 不重复 |
| question_knowledge 新增 mapping_source | VARCHAR：llm / rule / manual |
| question_knowledge 新增 review_status | VARCHAR：approved / pending / rejected |
| test_models 修复 | EXPECTED_TABLES 加入 answer_extraction_retries |

**数据回填顺序（关键）：**
1. question_instances 新增 document_id 列（nullable）
2. 用 `source_document_name = documents.filename` 回填 document_id
3. 回填 question_instances.year/school（从 questions 表迁移已有数据）
4. 将 document_id 改为 NOT NULL
5. 添加唯一约束 (document_id, source_question_number)
6. 移除 questions.year / questions.school 列

**入库逻辑适配（与 migration 同步）：**
- ingestion 创建 Question 时不再写入 year/school
- Instance 写入 document_id（FK documents）
- occurrence_count 不再手动累加，改为从 COUNT(instances) 派生
- 去重逻辑暂保持现有 stem 比较（Step 5 改为 content_hash）

**验收：**
- Alembic migration 执行成功，DB schema 与 DSD §8 一致
- 已有 question_instances 的 document_id 全部非 NULL
- 同一 (document_id, source_question_number) 无重复
- `SELECT year, school FROM questions` 返回 NULL（已迁移）
- `SELECT document_id, year, school FROM question_instances` 返回正确值
- pytest 全量通过

#### Step 2：审核决定写回 DB

**现状：** `update_document_review` 只把审核决定写进 `task.result_json`，不更新 `questions.status`，不应用 `review_overrides`。管理员审核后题库状态不变。

**题目定位方式：** 审核时通过 `question_instances(document_id, source_question_number)` 唯一定位 Question.id。如果 review_decisions 中直接包含 question_id，则优先使用。验收必须断言更新的是该文档对应的正确题目，不是任意同号题。

**修复：**
- 审核通过 → `questions.status = 'approved'`
- 审核驳回 → `questions.status = 'rejected'`
- `review_overrides` 中的字段修正（stem/options/answer/explanation）写回 questions 表
- 新增单元测试：断言 DB 中 questions 表字段真实变化，不是只断言 task.result_json

**验收：**
- 管理员审核一道 reviewing 状态的题并修正题干后，`SELECT stem, status FROM questions WHERE id = ?` 返回修正后的内容和 approved 状态
- 更新的是该文档对应的正确题目（通过 document_id + question_number 验证）

#### Step 3：Worker 失败语义 + L2 完整持久化

**现状：**
- `document_worker.py:173` 捕获 ingestion 异常后把 task.status 置为 succeeded，文档标 completed
- `document_worker.py:115` 只保存题号/题型/行号/答案到 llm_annotated_markdown，丢掉 knowledge_points/difficulty/score/corrected_anchors/anchor_status

**失败语义区分：**
- **答案提取失败** → 保留 retry queue 机制，不标 task failed（这是正常业务路径）
- **ingestion 真正抛异常** → task.status = failed，document.processing_status = failed

**修复：**
- ingestion 异常 → task.status = failed，document.processing_status = failed
- llm_annotated_markdown 保留完整 L2 Annotation JSON：knowledge_points、difficulty、score、corrected_anchors、anchor_status、question_type，兼容未来 structure_signature 和 annotation_version

**幂等重跑清理范围：**
- 只清理该 document 下 `source_type = 'document'` 且未被人工审核修改过的记录
- 管理员已审核/修正过的题目不静默覆盖，进入冲突或保留
- 具体判断：`questions.status != 'reviewing'` 或 `review_overrides` 非空的记录不清理

**验收：**
- ingestion 抛异常时，`SELECT status FROM background_tasks WHERE id = ?` 返回 failed，`SELECT processing_status FROM documents WHERE id = ?` 返回 failed
- 答案提取失败时 task status 仍为 succeeded（进入 retry queue）
- llm_annotated_markdown JSON 包含 knowledge_points、corrected_anchors、anchor_status 字段
- 同一文档重跑后，未审核的旧记录被清理，已审核的记录保留

#### Step 4：答案重试关联修正

**现状：** `answer_retry_worker.py:131` 按 `source_document_name + 顺序` 匹配题目更新答案，代码有 TODO。同文档多道空答案题可能更新错题。

**修复：** 改用 `document_id + question_instances` 精确关联。Step 1 已完成 document_id 回填，本步只需修改重试 worker 的匹配逻辑。

**验收：** 同一文档有 3 道空答案题，重试后每道题的答案更新到正确的 Question 上（通过 document_id + question_number 验证）。

#### Step 5：精确去重 content_hash

**现状：** 去重只比较 stem 文本（`ingestion.py:310`），题干相同但选项不同的选择题会被错误合并。

**修复：**
- content_hash = SHA256(规范化题干 + 选项 + 题型)
- hash 相同 → 同一道 Question，只创建 QuestionInstance
- hash 相同但 answer/explanation 冲突 → 不创建重复 Question，在该 Question 上生成审核冲突记录（标记哪个来源的答案与现有不同），管理员确认后决定保留哪个
- hash 不同 → 创建新 Question
- 已有数据回填 content_hash

**验收：**
- 上传同一份 PDF 两次，第二次只创建 Instance 不创建新 Question
- 题干+选项+题型相同但答案不同的题，不创建重复 Question，产生审核冲突记录
- `SELECT content_hash FROM questions` 无 NULL 值

#### Step 6：知识点映射落库

**现状：** 管线输出 `knowledge_points` 字符串但 `ingestion.py` 没有创建 `question_knowledge` 记录。知识树 333 节点已入库但题目-节点映射链路断裂。

**前置：** Step 3 已确保 llm_annotated_markdown 保留完整 knowledge_points。

**修复：**
- ingestion 时从 L2 Annotation 中读取 knowledge_points 字符串，映射到 knowledge_nodes（关键词匹配 + LLM 兜底）
- 写入 question_knowledge，带 confidence / mapping_source / review_status
- 低置信度（< 0.7）映射进入审核队列（review_status = 'pending'）
- 综合题（is_composite=true）支持子题级映射
- KnowledgeService 新增 `map_question_to_knowledge()` 方法

> **Phase 2A 实施说明（2026-08-22）：** LLM 兜底推迟到 Phase 2D。
> Phase 2A 采用「规则匹配（关键词索引）+ UNKNOWN 回退」，`mapping_source` 统一为 `rule`。
> 理由：333 节点关键词索引 + UNKNOWN 回退 + pending 审核已覆盖主要场景；LLM 兜底引入异步调用复杂度和 API 成本，收益不确定。

**验收：**
- 入库一道数学题后，`SELECT kn.code, kn.name FROM question_knowledge qk JOIN knowledge_nodes kn ON qk.knowledge_node_id = kn.id WHERE qk.question_id = ?` 返回对应的知识树节点
- 低置信度映射的 review_status = 'pending'
- 综合题的子题各自映射到不同知识点

**Phase 2A 总验收：**
- pytest 全量通过（预期 408+ passed，0 failed）
- 上传同一份 PDF 两次，第二次只创建 Instance
- 知识点正确映射到知识树节点
- 审核通过后 questions.status 和内容真实变化（DB 查询验证）
- Worker 异常时任务标 failed 不标 succeeded；答案提取失败走 retry queue
- llm_annotated_markdown 包含完整 L2 Annotation
- 答案冲突产生审核记录，不创建重复 Question

### 7.2 Phase 2B — 基础统计与搜索

| # | 任务 | 难度 | 说明 |
|---|---|---|---|
| 1 | 知识点 × 题型 × 年份统计 API | 中 | 基于 question_instances + question_knowledge + questions 的聚合查询 |
| 2 | 条件搜索 | 中 | 按学科/题型/知识点/年份/学校筛选题目 |
| 3 | 高频知识点排行 | 低 | 哪些知识点出现最多？按年份看趋势 |

### 7.3 Phase 2C — Annotation 原始积累

| # | 任务 | 难度 | 说明 |
|---|---|---|---|
| 1 | Structure Signature 采集 | 低 | 在现有 annotation prompt 里为数学/物理/化学增加可选 structure_signature 字段。只存到 llm_annotated_markdown JSON，不做 DB migration。 |
| 2 | Annotation 版本标记 | 低 | 在 llm_annotated_markdown 中记录 prompt 版本号，便于后续数据可比性。 |

### 7.4 Phase 2D — Similarity / Family 研究（前置条件满足后）

**启动前置条件（不是固定题数阈值）：**
- 目标学科有足够样本量
- 建立了可验证的 Golden Dataset（见下方）
- Structure Signature raw 数据有足够分布

**Golden Set 建立方式：**
- 不需要学科专业能力
- 只需要少量客观样例：同一道题改数字、改选项、改问法、材料题换材料
- 每个结构化科目 50-100 条边界案例
- 项目 owner + AI 辅助即可建立

| # | 任务 | 难度 | 说明 |
|---|---|---|---|
| 1 | Structure Signature 分布分析 | 中 | 从 raw 数据中统计 object/task/method 变体分布 |
| 2 | Normalizer 实现 | 中 | 同义词映射 + LLM 兜底 |
| 3 | Family 自动聚类 | 高 | 归一化后 object+task 相同的题归入同一 Family |
| 4 | question_families 表 | 中 | 到这一步才建表 |
| 5 | Similarity Engine | 高 | Embedding 召回 + 结构比较 |
| 6 | Family × Year 频率统计 | 中 | 基于 Instance 聚合 |

### 7.5 Phase 3+ — 未来做

| 任务 | 说明 |
|---|---|
| Family 趋势分析 UI | 前端展示 Family × Year 频率曲线 |
| 掌握度 × Family 交叉 | "哪些高频 Family 学生还没掌握" |
| AI 出题基于 Family | 基于高频 Family + 学生薄弱点生成新题 |

---

## 8. 数据模型变更（DSD）

### 8.1 当前实施的变更（Phase 2A）

**questions 表变更：**

| 变更 | 说明 |
|---|---|
| 新增 content_hash | VARCHAR(64)，规范化文本 SHA256 |
| 移除 year | 移到 question_instances |
| 移除 school | 移到 question_instances |
| occurrence_count | 改为派生值或缓存字段 |

**question_instances 表变更：**

| 变更 | 说明 |
|---|---|
| 新增 document_id | UUID FK documents，替代 source_document_name |
| 唯一约束 | (document_id, source_question_number) 不重复 |

**question_knowledge 表（已有 schema，需要实现写入逻辑）：**

| Field | Type | Note |
|---|---|---|
| id | UUID | PK |
| question_id | UUID | FK questions |
| knowledge_node_id | UUID | FK knowledge_nodes |
| confidence | NUMERIC | LLM 映射置信度 |
| is_primary | BOOLEAN | 是否主知识点 |
| mapping_source | VARCHAR | llm / rule / manual |
| review_status | VARCHAR | approved / pending / rejected |
| created_at | TIMESTAMPTZ | |

**content_hash 冲突处理：**
- hash 相同但 answer 或 explanation 不同 → 进入审核队列，不静默覆盖
- hash 相同且内容一致 → 只创建 Instance

### 8.2 暂不建的表

以下表在 Phase 2D 之前不建，避免空表增加迁移负担：

| 表 | 推迟原因 |
|---|---|
| question_families | Family 定义未确定，建表会锁死模型 |
| question_similarity | Similarity 引擎未实现 |
| question_annotations（独立） | 当前 llm_annotated_markdown JSON 足够 |

### 8.3 未来预留的设计原则（冻结但不实现）

| 原则 | 说明 |
|---|---|
| Primary Family 唯一归属 | 每道题只有一个 Primary Family，用于统计报表 |
| Family Membership N:M | 一道题可以属于多个 Family，用于检索/分析 |
| Knowledge Point ≠ Family | 同知识点不同任务属于不同 Family |
| 结构化学科优先 | Structure Signature 只对数学/物理/化学强制，其余可选 |
| Annotation ≠ 事实 | LLM 输出的所有标注都带 source/confidence/version |

---

## 9. 关键设计决策汇总

| # | 决策 | 结论 | 来源 |
|---|---|---|---|
| 1 | Question vs Instance 分开 | ✅ 是 | 三方一致 |
| 2 | year/school 只放 Instance | ✅ 是 | Codex 提出，三方同意 |
| 3 | Instance 关联 document_id | ✅ 是 | ChatGPT 提出，三方同意 |
| 4 | occurrence_count 改派生 | ✅ 是 | 三方一致 |
| 5 | Knowledge Point 映射是 P0 | ✅ 是 | Codex 提出，三方一致 |
| 6 | 综合题子题级知识点映射 | ✅ 是 | ChatGPT 提出 |
| 7 | content_hash 覆盖题干+选项+题型 | ✅ 是 | Codex 提出 |
| 8 | hash 冲突进审核不静默覆盖 | ✅ 是 | ChatGPT 提出 |
| 9 | Knowledge Point × Type × Year ≠ Family | ✅ 是 | ChatGPT 提出 |
| 10 | Family 表现在不建 | ✅ 是 | Codex 提出，ChatGPT 同意 |
| 11 | Structure Signature 不放 questions 表 | ✅ 是 | ChatGPT 提出，理由充分 |
| 12 | Structure Signature 存在 L2 Annotation JSON | ✅ 是 | ChatGPT 提出 |
| 13 | 结构化学科优先，其余可选 | ✅ 是 | Codex 提出，三方同意 |
| 14 | 5000 题不是硬阈值 | ✅ 是 | ChatGPT 提出 |
| 15 | Golden Set 可由 owner+AI 建立 | ✅ 是 | ChatGPT 修正 |
| 16 | Embedding 现在不管 | ✅ 是 | 三方一致 |
| 17 | LLM 只提取不判定相似 | ✅ 是 | 三方一致 |
| 18 | Annotation 带 source/confidence/version | ✅ 是 | ChatGPT 提出 |

---

## 10. 风险与待讨论问题

### 10.1 已知风险

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| Knowledge Point 映射不准 | 知识点统计失真 | 低置信度进审核，保留 mapping_source |
| LLM structure_signature 输出漂移 | 未来归一化困难 | 记录 annotation_version，先积累再归一化 |
| 综合题子题映射复杂 | 英语完形/阅读等子题知识点不同 | ingestion 支持 sub_question 级别映射 |
| 管理员精力有限 | 试卷上传速度制约数据积累 | 管线已自动化，上传即入库 |

### 10.2 待讨论问题

1. **content_hash 规范化规则**：标点/空格/Unicode/LaTeX 的归一化到什么程度？
2. **Instance 唯一约束的边界**：同一份试卷的不同页出现同一道题（如续页），怎么处理？
3. **综合题子题映射的 question_id**：子题是独立 Question 还是父题的 sub_questions 字段？当前 ingestion 已有 is_composite/sub_questions 支持。
4. **exam_type 标准化**：期末/一模/二模/月考/周测，是否需要统一枚举？当前管线大概率拿不到稳定值，建议暂不建列。
5. **现有精确匹配去重的迁移**：改为 hash 后是否需要处理已有数据的 hash 回填？

---

## 附录 A：完整数据关系图

```
Source Document (documents)
       │
       ▼
Question Instance (question_instances)
  year / school / document_id / page / question_number
       │
       ▼
Question (questions)
  stem / options / answer / explanation / content_hash
  subject / question_type / difficulty
       │
       ├── Knowledge Points (question_knowledge → knowledge_nodes)
       │     N:M, 带 confidence / mapping_source / review_status
       │
       └── Annotation (llm_annotated_markdown JSON)
             ├── question_type / difficulty / knowledge_points
             └── structure_signature (math/physics/chemistry only)
                   object / task / method / condition_text
                   confidence / source / annotation_version

=== 以下为未来阶段，暂不实现 ===

Similarity (question_similarity)
  question_id_a ↔ question_id_b
  similarity_type / similarity_score

Family (question_families)
  canonical_name / subject / object+task+method canonical
  ← Primary Family (1:1, 统计归属)
  ← Family Membership (N:M, 检索/分析)
```

## 附录 B：术语表

| 术语 | 定义 |
|---|---|
| Question | 一道具体题，包含内容和元数据（事实层） |
| QuestionInstance | 一道题在某份试卷/某年的一次出现（事实层） |
| content_hash | 规范化文本的 SHA256，用于 exact dedup |
| Knowledge Point | 知识树节点，通过 question_knowledge 关联到 Question |
| Structure Signature | LLM 提取的题目结构特征（Annotation，不是事实） |
| Exact Duplicate | 文本 hash 完全相同的题 |
| Near Duplicate | 结构相同、仅参数微调的题（未来） |
| Family | 一组结构/解法高度相似的题（未来） |
| Primary Family | 每道题唯一的统计归属 Family（未来） |
| 统计视图 | Knowledge Point × Question Type × Year（不是 Family） |
