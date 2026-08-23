# P0 入库流程对抗性审查

Version: 1.1
Date: 2026-08-20
Status: 第二轮审查发现问题，待修复

---

## 1. 审查范围

审查对象：P0 入库流程的全部新增代码

- `backend/app/domains/document/answer_extractor.py` — LLM 答案提取
- `backend/app/domains/document/ingestion.py` — 入库服务
- `backend/app/domains/document/processor.py` — 管线集成（extract_and_ingest）
- `backend/app/worker/document_worker.py` — Worker 集成
- `backend/app/models/tables.py` — 表字段补齐
- `backend/alembic/versions/3d7ee1cb7c3a_*.py` — Migration

## 2. 审查方法

从第一性原理出发，逐条对照：
- 需求基线（REQUIREMENTS_AND_SOLUTION.md）
- 项目规则（rules.md）
- V1 教训固化（V1_LESSONS.md）
- 架构设计（SAD.md、PIPELINE.md、DSD.md）

## 3. 发现的问题

### 3.1 P0-1：选择题回查验证形同虚设

**位置**：answer_extractor.py 第 136-140 行

**问题**：策略 3 对选择题字母做全文搜索，只要原文中任何位置出现过该字母就认为验证通过。例如 LLM 说第 5 题答案是"D"，但原文第 5 题答案其实是"C"，只要原文中其他地方有"D"（比如第 3 题答案），验证就会通过。

**影响**：LLM 对选择题答案的错误无法被回查机制检测到。

**修复方案**：
- 方案 A：去掉策略 3，只用策略 1 和 2（直接子串 + 去空白匹配）
- 方案 B：策略 3 改为局部搜索（在该题附近的原文中搜索，而非全文）
- 推荐方案 A，因为选择题答案通常是单字母，策略 1 和 2 已经足够

### 3.2 P0-2：违反"LLM 不输出内容"原则需记录偏离

**位置**：answer_extractor.py 整体设计

**问题**：rules.md 规定"文档解析的 LLM 只输出标注/行号/元数据，不输出题干原文"。answer_extractor 让 LLM 从原文中"逐字复制"答案和详解内容，本质上是让 LLM 输出了原文内容。

**判定**：这是有意识的偏离。原因是答案区格式多样（HTML 表格、连写、分散、每题独立），代码无法可靠切分，必须依赖 LLM 语义理解。30 份文档验证准确率 100%。

**修复方案**：在 answer_extractor.py 的 docstring 中增加偏离说明，记录偏离原因和验证基础。

### 3.3 P1-1：入库没有去重检查

**位置**：ingestion.py 第 173-191 行

**问题**：每道题直接创建新的 Question 记录，没有检查是否已存在相同题目。如果同一道题出现在两份不同的试卷中，会创建两条记录。

**需求原文**（REQUIREMENTS_AND_SOLUTION.md 3.5）：
> 同一道题在多份试卷中出现时，自动识别并合并为一道题，保留多个来源信息，保留出现次数。

**修复方案**：
- 入库前做 stem 文本相似度匹配（至少精确匹配）
- 匹配到已有题目时只创建新的 QuestionInstance
- 累加 occurrence_count
- **补充（用户要求）**：
  - 重复题不重复入库，但要标注出现次数元数据，用于统计知识点出现频率
  - 相似的题目（stem 高度相似但数据/出题方式微调）也应有相似的元数据标记
  - 相似题目同样应对着知识点的出现频率统计

### 3.4 P1-2：L1 markdown 没有存入 documents 表

**位置**：document_worker.py 第 101-103 行

**问题**：worker 中构造了 l1_markdown 变量，但只传给了 extract_and_ingest()，没有写入 document.ocr_markdown 字段。

**用户明确要求**：原始 PDF 和 OCR 提取的 markdown 应该入库备查。

**修复方案**：在 worker 中，管线成功后将 l1_markdown 写入 document.ocr_markdown。

### 3.5 P1-3：答案提取失败静默降级

**位置**：processor.py 第 208-209 行

**问题**：答案提取失败时只打 warning 日志，然后用管线切片的答案兜底。没有记录到 task result 中，管理员无法知道答案提取是否成功。

**规则原文**（rules.md V1 教训第 10 条）：
> 错误不能静默吞掉；失败、低置信度、来源缺失必须记录结构化原因并进入可审计状态。

**修复方案**：将答案提取的状态（成功/失败/部分失败）记录到 task result 中。

### 3.6 P2-1：入库 status 判断过于简单

**位置**：ingestion.py 第 164-167 行

**问题**：所有低置信度题目统一进入 reviewing，缺少 issue 分类。管理员无法区分"答案缺失"和"题干不完整"等不同严重程度的问题。

**修复方案**：在 Question 记录中增加 review_reason 字段，记录具体的审核原因。

## 4. 验证基础

LLM 答案提取方案经过完整验证：
- 30 份 OCR markdown（test/ocr_markdown/）
- 9 个学科（数学、物理、化学、英语、语文、生物、政治、历史、地理）
- 约 800 道题
- 准确率 100%
- 覆盖格式：HTML 表格、连写、每题独立、解答题解题过程提炼、LaTeX 公式、化学方程式
- 覆盖特殊情况：集团校自创题、OCR 乱码、26 题特殊卷、写作题无答案

## 5. 第一轮修复优先级

| 序号 | 问题 | 级别 | 状态 |
|------|------|------|------|
| 1 | 选择题回查验证形同虚设 | P0 | ⚠️ 部分修复（见第二轮审查） |
| 2 | 记录 LLM 输出内容的偏离原因 | P0 | ✅ 已修复 |
| 3 | L1 markdown 存入 documents 表 | P1 | ⚠️ 部分修复（见第二轮审查） |
| 4 | 答案提取失败记录到 task result | P1 | ⚠️ 部分修复（见第二轮审查） |
| 5 | 入库去重检查 | P1 | ⚠️ 部分修复（精确匹配已实现，LLM 相似判断待后续） |
| 6 | status 判断增加 issue 分类 | P2 | ✅ 已修复 |

---

## 6. 第二轮审查发现的问题（2026-08-20）

### 6.1 P0-1A：找不到题号时回退到全文

**位置**：answer_extractor.py `_find_question_region()` 第 171-173 行

**问题**：OCR 把题号识别错误时（如 "1." 识别为 "l."），区域定位失败，回退到全文搜索。对于选择题，全文搜索字母等于直接通过。

**修复方案**：找不到题号时返回空字符串（验证失败），标记为低置信度，而不是回退到全文。

### 6.2 P1-1B：题号匹配正则不够健壮

**位置**：answer_extractor.py `_find_question_region()` 第 159-162 行

**问题**：只匹配 `.、）)` 四种分隔符，OCR 可能把 `.` 识别为 `．`（全角）或 `。`。只匹配行首，不处理缩进。

**修复方案**：扩展分隔符列表，增加全角字符，处理行内缩进。

### 6.3 P1-3A：`native_markdown` 未写入

**位置**：models/tables.py、document_worker.py

**问题**：`native_markdown` 字段定义了但 worker 中没有写入，永远是 NULL。

**决策**：保留 `native_markdown` 字段。PyMuPDF 在图片 bbox 提取、答案表定位、上下标几何信息方面有独特价值，PPS/PVL 对这些处理不佳。后续管线如果需要 PyMuPDF 的辅助信息，可以直接从 DB 读取 native_markdown，不用重新跑 PyMuPDF。

**修复方案**：在 worker 中把 PyMuPDF 提取的 native L1 也写入 `document.native_markdown`。

### 6.4 P2-3B：`annotated_markdown` 字段名误导

**位置**：models/tables.py

**问题**：字段名叫 `annotated_markdown`，但实际存的是 JSON 格式的 L2 标注数据，不是 markdown。

**修复方案**：改字段名为 `llm_annotated_markdown`，内容可以是 JSON（标注数据），字段名明确表示"LLM 标注后的版本"。

### 6.5 P1-4A：只有日志记录，没有实际重试机制

**位置**：answer_extractor.py、document_worker.py

**问题**：`AnswerExtractionRetryItem` 数据结构定义了，但没有重试队列表、没有重试 worker、没有人工触发 API。失败记录只写入 `document_processing_logs`，没有代码消费并重试。

**修复方案**：后续实现。当前记录到日志已满足"可审计"的最低要求。

### 6.6 P1-5A：LLM 相似判断未实现

**位置**：ingestion.py

**问题**：用户要求"交给 LLM 来判读是否属于高度相似"，当前只实现了精确匹配。

**修复方案**：后续实现。精确匹配已覆盖完全相同的题目场景。

---

## 7. 第二轮修复优先级

| 序号 | 问题 | 级别 | 状态 |
|------|------|------|------|
| 1A | 找不到题号时回退全文 | P0 | ✅ 已修复（返回空字符串） |
| 1B | 题号匹配正则不够健壮 | P1 | ✅ 已修复（扩展分隔符+缩进支持） |
| 3A | native_markdown 未写入 | P1 | ✅ 已修复（保留字段，worker 中写入 PyMuPDF L1） |
| 3B | annotated_markdown 字段名误导 | P2 | ✅ 已修复（改为 llm_annotated_markdown） |
| 4A | 重试机制缺失 | P1 | ✅ 已修复（answer_extraction_retries 表 + retry worker + API） |
| 5A | LLM 相似判断 | P1 | ⏸️ 暂时禁用，待用户重新设计方案 |
