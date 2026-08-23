# AI Tutor Personal Edition — 项目状态

---

## 当前状态

**Phase 2A 总验收通过；Phase 2B/2C 已实现；入库管线 P0-A/P0-B/P0-C/P0-G 止血补丁完成；答案验证器独立化完成（以原始 PDF 为主判据）；9 科答案基线已建立（答案 mismatch=0，严格通过率 76%）；英语 P0-A 材料合并验证通过（11/11 材料进 stem）；OCR 链加固完成（PPS 排队 + paddle 10010 熔断 + mimo 短超时降级）；架构方向决策：先量化再止血再单科原型再逐科推广（2026-08-25，版本 6.10）。**

> **全量回归确认（2026-08-22 00:39）**：修复收集错误（`run_pipeline` 恢复至 pipeline.py，4 个引用方零改动）+ 4 项测试与生产代码不同步（processor 已迁移 `run_simple_pipeline`，patch 目标同步）+ DB 历史题清理（9 道英语卷题，stats 测试恢复干净库前提）+ 沙箱 temp 权限根治（`backend/tests/conftest.py` 固定 temp 根到工作区 `tmp/pytest`，`processor._download_pdf` 改工作区 tmp，新增 `test_temp_root.py`）。全量 pytest（用户本机，注入 backend/.env DATABASE_URL）**549 passed，0 failed，9 warnings**（546 → 549，+3 temp 根测试；收集错误与 temp 权限间歇失败均已消除）。
> **已知记录口径修正**：此前 LOG 中 534/537/539/542/546 等数字与当前工作树不一致（processor 迁移后测试未同步、收集错误被隐藏），本次全量 549 passed 为权威基线。

> migration 20260821_0003 + 20260821_0005 已执行到 PostgreSQL，head 确认。
> SQL 验证：questions.year/school 已移除，content_hash 已添加；question_instances.document_id NOT NULL；question_knowledge 新增 mapping_source/review_status。
> 稳定全量命令实际为 453 passed，0 failed（本环境，Step 2 前基线）；448/450+失败数字来自工作目录/沙箱环境敏感性，不作为基线。
> **Step 0 验收通过**：真实回填演练纳入 pytest（`test_phase2a_step0_migration_rehearsal.py`，一次性临时库，7 项断言：document_id 回填、COALESCE 不清空已有值、year/school 0 残留、唯一索引拒绝重复、downgrade 有损回退）+ 脚本版 `backend/scripts/step0_backfill_verify.py`（8/8 项）+ ingestion 真实路径测试 2 条（Step 0 集成 18 项通过）。
> **Step 1 验收通过**：migration 已执行（20260821_0003）、29 条结构测试通过、DB 与 DSD §8 一致（列/索引/约束 SQL 验证）、Step 0 回填证据关联确认。
> **Step 2 验收通过**：审核写回 DB（`update_document_review` 同时更新 task.result_json 与 questions 表；question_instances 唯一定位），集成测试 11 项 + `backend/scripts/step2_db_verify.py` DB 验证通过。
> **Step 3 验收通过**：Worker 失败语义 + L2 完整持久化已实现；`_cleanup_unreviewed_records` 仅删除当前 document_id 下的 Instance，跨文档共享的 Question 保留并更新 occurrence_count。回归测试覆盖跨文档共享、混合审核状态、FK 依赖保留场景。Step 3 测试 13 项通过。
> **Step 4 验收通过**：答案重试关联修正（`answer_retry_worker.py` 不再按 `source_document_name + 顺序` 猜测题目，改用 `question_instances(document_id, source_question_number)` 精确关联；找不到 Instance 记录失败；已有答案不覆盖）。Step 4 测试 5 项通过；`backend/scripts/step4_db_verify.py` DB 验证：同文档 Q1→A、Q2→B、Q3→C 精确更新，无串题。
> **Step 5 验收通过**：精确去重 content_hash（`content_hash.py`：SHA256(规范化题干+选项+题型+子题)，NFKC+全角转半角+去空白标点+小写确定性规范化；ingestion 去重从"只看 stem"升级为 content_hash 匹配；hash 相同答案不同 → 不建重复 Question，review_reason 持久化冲突详情 `answer_conflict:{来源文档}:{冲突答案}` + 降 reviewing）。Step 5 测试 12 项通过；migration 20260821_0005 回填已执行；DB 验证：重复 content_hash 组数=0、NULL=0。
> **Step 6 验收通过**：知识点映射落库（`KnowledgeService.map_question_to_knowledge`：seed 关键词索引匹配知识树节点 → question_knowledge 写入，mapping_source='rule'；低置信度<0.7 → review_status='pending'；knowledge_points 为空或无命中 → 回退 {SUBJ}-UNKNOWN 节点 + pending（不静默跳过）；综合题子题级映射）。Step 6 测试 7 项通过；`backend/scripts/step6_db_verify.py` DB 验证："函数单调性"→MATH-ANA（函数与导数）confidence=1.0/review=approved。
> **总验收（2026-08-21）**：全量 pytest 520 passed、0 failed（用户本机验证）；Phase 2A 专项测试 96 项通过。Step 3 跨文档清理已修复 + 4 项回归测试；Step 5 冲突详情已持久化到 `review_reason`（格式 `answer_conflict:{来源文档}:{冲突答案}`）；Step 6 验收口径降级为”规则匹配 + UNKNOWN 回退”，LLM 兜底推迟到 Phase 2D。

> Task 2.5 管线门禁已通过。P0 入库流程已实现并通过 30 份文档验证。
> 系统功能验收：9 份全新 PDF 全流程执行，171 题提取，153 题直接入库（89.5%）。
> 三科重验收：地理 27 题 ✅、数学 21 题 ✅、历史 43 题 ✅。
> 历史选择题答案准确性验证：40 题全部正确（100%）。
> **Phase 2B 已实现（2026-08-22 两轮对抗性审查修复后）**：`GET /api/admin/questions` 条件搜索（学科/题型/知识点/年份/学校/难度/来源/状态/**confidence 精确匹配** + 分页）+ `GET /api/admin/statistics` 统计聚合（total/question_type_distribution/knowledge_point_distribution/difficulty_distribution/year_trend/**kp_year_trend 知识点×年份出现频率**，高频知识点按次数降序；**start_year/end_year 全局过滤影响 total 和所有分布**）+ `GET /api/admin/questions/{id}` 详情（**含配图 images + occurrence_count 从 COUNT(instances) 派生**，SQL 下沉 Repository 层由真实 DB 集成测试覆盖）。测试 27 项（search_stats 18 项 + API 9 项）。
> **Phase 2C 已实现（2026-08-22 两轮对抗性审查修复后）**：Structure Signature 采集（line_annotator prompt 加 structure_signature 可选字段：**object/task/method/condition 四层**，仅数学/物理/化学）+ Annotation 版本标记（`ANNOTATION_PROMPT_VERSION` 写入 llm_annotated_markdown）+ **structure_signature 序列化附带 source='llm'/confidence（复用题目级标注置信度）/annotation_version 元数据**（PLAN §5.2）+ `_serialize_l2_for_persistence` 提取为独立函数。测试 10 项（prompt 四层字段说明、LLM 输出解析含 condition、规范化四层键、worker 序列化含元数据）。
> 含 Phase 2B/2C 两轮修复后全量 pytest 540 passed（用户本机预期，0 failed；沙箱环境 537 passed + 3 项 temp 权限问题）。
> **Phase 2 全量审查（2026-08-22）**：6 单元 workflow 审查发现并修复 3 项阻断（statistics knowledge_point 过滤静默忽略、综合题子题映射塌缩、回填 migration 0005 无测试执行）；新增 `test_statistics_knowledge_point_filter` + `test_phase2a_step5_backfill_rehearsal.py` + 强化 `test_composite_sub_questions_map_to_nodes`。全量 pytest 542 passed（用户本机预期；沙箱 539 passed + 3 项 temp 权限）。
> **高优先级遗留修复完成（2026-08-22）**：`answer_retry_worker` 提取失败未超限时恢复 `pending`，超限标 `failed`，`max_retries` 生效；2C 综合题合并保留 `structure_signature`，`SlicedQuestion` 与 `PipelineResult.to_dict()` 同步透传。新增 4 项回归测试；全量 pytest 546 passed、0 failed。
> 待处理：Phase 2D Similarity/Family（前置条件：样本量 + golden set + Structure Signature raw 分布）。

### 三科管线门禁

| 科目 | 复现性 | 结构门禁 | answer_empty | high_conf | 状态 |
|------|--------|----------|-------------|-----------|------|
| **数学** | ✅ 0 diff | ✅ 21/21 | 0% | 19/21=90.5% | 管线通过 |
| **物理** | ✅ 0 diff | ✅ 20/25 | 0% | 19/20=95.0% | 管线通过 |
| **英语** | ✅ 0 diff | ✅ 19/54 | 0% | 13/19=68.4% | 管线通过 |

### Golden 准确率（需求目标：≥95%）

| 科目 | answer | stem_line_ids | options_line_ids | 判定 |
|------|--------|---------------|-----------------|------|
| **数学** | 8/8=100% | 8/8=100% | 8/8=100% | ✅ 达标 |
| **英语** | 10/19=52.6% | 9/19=47.4% | 12/19=63.2% | ❌ 未达标 |
| **物理** | 0/20=0% | 4/20=20% | 3/20=15% | ❌ 未达标（golden 为 draft） |

### 新科目状态

| 科目 | L1 fixture | paper manifest | golden draft | 复现性 |
|------|------------|----------------|--------------|--------|
| **化学** | ✅ 304 行 | ✅ 20 groups | ⏸️ 6 题（管线 draft，stem 为空）| 1 diff |
| **生物** | ✅ 327 行 | ✅ 40 groups | ⏸️ 10 题（管线 draft，stem 为空）| 1 diff |
| **语文** | ✅ 415 行 | ✅ 8 groups | ⏸️ 15 题（管线 draft）| 4 diff |

### 系统功能验收结果（2026-08-20）

**验收方式**：9 份全新教师版 PDF（覆盖 9 科），全流程执行（PDF → OCR → LLM 标注 → LLM 答案提取 → 入库预览）

| 学科 | 题数 | approved | reviewing | skipped | 答案来源(LLM/管线) | 错误 |
|------|------|----------|-----------|---------|-------------------|------|
| 物理 | 24 | 21 | 1 | 2 | 24/0 | 0 |
| 生物 | 12 | 12 | 0 | 0 | 12/0 | 0 |
| 政治 | 28 | 26 | 2 | 0 | 28/0 | 0 |
| 历史 | 43 | 40 | 1 | 2 | 40/0 | 1 |
| 语文 | 11 | 7 | 4 | 0 | 11/0 | 0 |
| 化学 | 23 | 17 | 6 | 0 | 23/0 | 0 |
| 地理 | 0 | 0 | 0 | 0 | 0/0 | **1** |
| 数学 | 21 | 21 | 0 | 0 | 0/21 | 1 |
| 英语 | 9 | 9 | 0 | 0 | 9/0 | 0 |
| **总计** | **171** | **153** | **14** | **4** | **147/21** | **3** |

**89.5% 直接入库，不需要人工干预。**

**全部修复完成**：
- ✅ gateway 重试+兜底策略（MIMO 失败 → 间隔5秒重试 → 切换 DeepSeek）
- ✅ JSON 截断容错（`_try_fix_truncated_json`，补全截断括号再解析）
- ✅ answer_matcher 主观题答案修复（short_answer 跳过可疑检查，从 answer_line_ids 切片）
- ✅ 选择题回查验证改为区域搜索（不全文搜索）
- ✅ 三份文档持久化（native_markdown + ocr_markdown + llm_annotated_markdown）
- ✅ 答案提取重试队列（answer_extraction_retries 表 + retry worker + API）
- ✅ status issue 分类（review_reason 字段）
- ✅ 精确匹配去重（stem 完全相同 → 只创建 QuestionInstance）

**三科重验收结果**：
- 地理：27 题入库，30 题答案提取 verified，4 题丢弃（源文件缺失，预期行为）✅
- 数学：21 题入库，21 题全部 high_confidence，答案全部正确 ✅
- 历史：43 题入库，40 题选择题答案全部正确（100%）✅

**答案准确性验证**：
- 历史选择题 40 题逐题对比：LLM 提取的答案与原文"故选X"100% 一致
- LLM 能正确识别各种格式：`故选：C。`、`故选B`、`D正确`、`A."xxx"...`
- 答案全部从原文提取，无编造内容

**待办**：
- Native/PP 行号编码分离（P1L001 vs N1L001）✅ 已完成
- 知识树种子数据入库 ✅ 已完成（333 节点，9 科，4 级深度）
- Phase 2A 数据底座修复：Step 1 ✅ 完成，Step 2-6 ⬜ 待实现（设计已冻结，见 PLAN_QUESTION_FAMILY v2.0 / ROADMAP v2.0 / DSD §8）
- Phase 2D Similarity/Family 研究 ⏸️ 暂缓（前置条件：样本量 + golden set）

**关于 golden draft 的说明**：
Golden 是冻结回归机制，不是 live 验收。P0 的 9 科验证是真实 PDF + 真实 OCR + 真实 LLM 的 live 验收，每次跑都可能因 OCR/LLM 服务/ PDF 版本产生不同结果；它能证明"当前版本能跑通"，不能证明"以后改动不会破坏之前已跑通的结果"。Golden 的用途恰恰是后者：改了解析逻辑后，同一份冻结输入必须仍产生相同/正确的输出。
但化学/生物/语文当前 draft 是管线输出，不是人工核对过的标准答案集（化学/生物 stem_line_ids 大量为空），让修复后的管线重跑仍是自证，没有验收意义。且人工核对成本高，Phase 2 前没有必须用它们做回归的场景。
后续如果改 L1、锚点校正、答案匹配等高风险逻辑，再针对受影响科目补小规模人工 golden，或把 P0 验收产物冻结为 regression snapshot。历史反例：数学 Q11 曾 confidence=1.0 但答案错误，结构 manifest 和 answer_empty 门禁都拦不住，只有内容级 golden 或内容级校验能拦住。

### 对抗性审查结论（2026-08-20 v4 — 三轮审查完成）

**第一轮修复（6项）**：
- ✅ 选择题回查验证改为区域搜索（去掉全文搜索）
- ✅ 记录 LLM 输出内容的偏离原因（docstring）
- ✅ 三份文档入库（native_markdown + ocr_markdown + llm_annotated_markdown）
- ✅ 答案提取失败记录到 task result + 重试队列
- ✅ 精确匹配去重（stem 完全相同 → 只创建 QuestionInstance）
- ✅ status issue 分类（review_reason 字段）

**第二轮修复（6项）**：
- ✅ 找不到题号时返回空字符串（不回退全文）
- ✅ 题号匹配正则扩展（全角分隔符 + 缩进支持）
- ✅ native_markdown 保留并写入（PyMuPDF L1 持久化）
- ✅ 字段名修正（annotated_markdown → llm_annotated_markdown）
- ✅ 答案提取重试机制（answer_extraction_retries 表 + retry worker + API）
- ⏸️ LLM 相似题目判断（暂时禁用，待重新设计方案）

**第三轮审查结论**：
- 所有原始 6 个问题已修复
- 新发现 2 个低优先级问题（长答案全文搜索风险可接受、字段名含"markdown"但存JSON）
- 新发现 1 个 P1 问题（retry worker 题目匹配过于简单，TODO 已标记）
- **结论：可进入系统功能验收**

**遗留项（未变）**：
- 知识树未初始化
- DOCX 零支持（管线层面）
- embedding 维度超限
- 沙箱 temp 目录权限

**行号编码分离（已完成）**：
- PP 用 `P1L001`，Native 用 `N1L001`；canonical L1 保留 PP 行号体系。
- native 行号通过 `raw_sources["native_line_id"]` 溯源，不暴露给 LLM 标注阶段。
- 涉及 `native_markdown.py`、`l1_postprocessor.py`、`pipeline.py`、`simple_pipeline.py`、`l1_arbiter.py`。

已完成后端 FastAPI 骨架、22 张 DSD 表模型与 Alembic 初始迁移、Repository/Domain Service/Application Service 分层骨架、统一 Background Task/Domain Event 骨架、LLM Gateway 基础路由、MinIO 客户端接入和依赖健康检查。embedding 已固定为 qwen3-embedding:4b / 2560 维，初始迁移不建 HNSW 向量索引。

P2 已新增 PP-StructureV3 客户端、OCR/VL 回退链、LLM 结构化 Question Aggregate 输出、`test/scripts/run_parse_baseline.py` 和 `test/scripts/evaluate_parse_accuracy.py`。

T3 Phase 0 状态：L1/L2 Schema、fixture（数学 38 行 postprocessed + 英语 69 行 postprocessed 含完形填空共享材料、答案区与详解区）、golden（数学 v3.1 7 题 + 英语 v3.1 10 题）、postprocessor（含数字误拆 bug 修复）、smoke test 已落地；后端 41 项、Smoke pytest 13 项全部通过。Live 全部通过：DeepSeek 12s、MIMO 134s、Qwen 38s。

本次修复：`HTTPLLMProvider` 新增 `response_format` 可选参数；`build_gateway()` 和 smoke test 为 MIMO 传入 `json_object`；smoke test 超时提升至 120s；smoke test prompt 改为完整 fixture 文本。Math Golden Set 已补齐至 v3.1；English Golden Set 重建至 v3.1（基于 postprocessed L1 fixture，10 题含完形填空共享材料、答案区与详解区，answer/explanation 锚点均非空）；`l1_postprocessor.py` 修复数字内点号误拆 bug（`prev_char.isdigit()` 跳过）；smoke test 新增 English fixture + golden set 完整性断言（含 answer/explanation 锚点非空）。

约束状态：T3 Phase 1 已通过对抗性审查并最终验收（2026-08-13）。后端 143 项测试通过；Mock eval 8/8 指标 100%；用户本机 live-pp 3 次运行取最差后 golden 8/8 全字段 100%，line ID errors=0。全卷 21 题中 answer_matched=16、answer_empty=5（均为解答题 17-21）、blocked=7（Q1/Q4 缺选项、Q17-21 缺答案），均带 issues/低置信度标记，未静默发布。explanation_line_ids 不在 Phase 1 验收范围内（golden 8 题均为空，explanation_source 为 llm_fallback，属 Phase 2+ 范畴）。

本次 Phase 1 复审修复：答案表按题号边界切分，支持括号答案并停在解答题区；锚点题号正则排除 LaTeX 续行；L1 后处理支持行内全角括号题号切分。

本次 Phase 1 基础设施加固：`run_phase1_eval.py` 新增全卷验收阈值 `THRESHOLDS_FULL卷`（min_answer_matched=16、max_blocked=7、min_quality_high=14、max_missing_anchors=10）；`THRESHOLDS_SMOKE` 补充 `stem_line_ids`、`options_line_ids`、`answer_line_ids` 三项；`HTTPLLMProvider` 新增指数退避重试（max_retries=2、retry_base_delay=1.0s）。

本次语义锚点修复：LLM 输出 `stem_markers` 作为定位计划，代码从 PP/native 原文切片；新增 `semantic_anchor.py`、`llm_annotation` 诊断块和 `run_9subject_validation.py`。丰台物理 Q3/Q19 根因已定位为题号正则误判 `3.2025年...` 为小数并修复。后端 325 项测试通过；9 科小规模验证由用户决定启动。

## 9 科验证结果（2026-08-18 最终）

| 科目 | 题数 | 综合题 | 入库 | 丢弃 | 丢弃率 | OCR | 状态 |
|---|---|---|---|---|---|---|---|
| 英语 | 11 | 10 | 11 | 0 | 0.0% | PPS | ✅ |
| 语文 | 11 | 5 | 11 | 0 | 0.0% | PPS | ✅ |
| 数学 | 23 | 0 | 21 | 2 | 8.7% | PPS | ✅ |
| 物理 | 20 | 6 | 19 | 1 | 5.0% | PPS | ✅ |
| **化学** | **25** | **3** | **25** | **0** | **0.0%** | **VL** | ✅ |
| 生物 | 26 | 1 | 26 | 0 | 0.0% | PPS | ✅ |
| 历史 | 43 | 3 | 39 | 4 | 9.3% | PPS | ✅ |
| 政治 | 28 | 0 | 27 | 1 | 3.6% | PPS | ✅ |
| 地理 | 16 | 16 | 14 | 2 | 12.5% | PPS | ✅ |

备注：

- 化学 VL 单独跑 0% 丢弃（25/25），VL API 稳定时完美。
- 历史 LLM JSON 解析偶发失败（9.3%）。
- 地理 16/16 全是综合题（11 组单选题组 + 5 道材料分析题），2 道丢弃为预期行为：Q19 选项是图片（OCR 无法提取），Q23-Q25 试卷缺失。实际丢弃率 0%。
- 地理走 PPS（图片/表格多，PPS 提取 112 张图 vs VL 50 张，无公式需求）。

### 9 科答案基线（2026-08-24，以原始 PDF 为主判据）

> 验证方法：答案验证器 `test/scripts/answer_verifier.py`，四层独立证据对比（pdf_raw_text 主判据 → native_markdown 交叉验证 → ocr_markdown 辅助证据 → DB）。

| 学科 | DB 题数 | matched | mismatched | unverifiable | 严格通过 |
|---|---|---|---|---|---|
| 化学 | 26 | 26 | 0 | 0 | 25/26 |
| 历史 | 42 | 42 | 0 | 0 | 35/42 |
| 地理 | 25 | 20 | 0 | 5 | 25/25 |
| 政治 | 28 | 28 | 0 | 0 | 28/28 |
| 数学 | 5 | 5 | 0 | 0 | 5/5 |
| 物理 | 19 | 13 | 0 | 6 | 7/19 |
| 生物 | 24 | 22 | **2** | 0 | 22/24 |
| 英语 | 22 | 20 | 0 | 2 | 6/22 |
| 语文 | 7 | 6 | 0 | 1 | 3/7 |
| **合计** | **198** | **162** | **2** | **14** | **156/209** |

**严格通过率: 156/209 (75%)**

**mismatched（真实错误，必须修复）**：
- 生物 Q6: DB='D'，PDF='C' → 管线 answer_matcher 或 LLM 标注错误
- 生物 Q7: DB='D'，PDF='A' → 管线 answer_matcher 或 LLM 标注错误

**unverifiable 明细**：
- `free_text_answer`: 5 题（物理实验/计算题，长文本答案）
- `missing_db_question`: 11 题（不在 DB 中，无法验证）
- `composite_subquestion`: 1 题（英语综合题子题未完全映射）

### 9 科答案基线更新（2026-08-25，P0-C 收敛 + composite 回退后）

> P0-C 修复：答案表来源感知（native 优先，OCR 冲突保留 LLM），生物 Q6/Q7 mismatch 2→0；
> composite 子题映射回退父题 free_text，生物 Q21-Q26 unverifiable→matched。
> 全 9 科：matched 193、unverifiable 16、**mismatched 0**、严格通过 **158/209 (76%)**。
> 报告：`test/results/e2e_semantic_report_9subjects_p0c_v4.txt`

### 英语 P0-A 材料合并验证（2026-08-25）

> 重跑英语入库（deepseek-vl OCR，task fb994ca9 succeeded）：
> - **composite 材料 11/11 (100%) 进 stem**（修复前 12/23，Q26 stem 63→1731 字符）
> - stem 核心 10/11 (91%)、位置 7/11 (64%)、选项 7/11 (64%)、答案 10/11 (91%)
> - 注意：重跑后 LLM 合并为 11 个大综合题（覆盖 Q1-Q46），与之前 23 题结构不同，严格通过率 3/11 不可直接对比
> - 剩余问题：选项归属 64%（综合题选项跨 section）、位置 64%（stem 越界串题）、Q46 作文缺库

### OCR 链加固（2026-08-25，paddle/mimo 故障不再卡死管线）

> 诊断结论（实测）：
> - **paddle**：服务端"任务提交队列已满"（HTTP 400 code 10010，官方错误码表无此码）——共享队列状态，重试 155s 大概率仍满
> - **mimo-vl**：服务端间歇性断连/挂起（同请求有时成功有时断连），8 页连续请求放大
> - **deepseek-vl**：稳定可用
>
> 修复（4 个 commit）：
> | Commit | 内容 |
> |---|---|
> | 5351f1e | PPS 也走 PaddleOCRQueue(max_concurrent=1) + fail_task session 毒化修复 |
> | 8574109 | paddle 10010 熔断（连续 2 次 → 熔断 300s，15s 快速失败原 155s） |
> | 38904c3 | VL provider 单页失败快速降级（不再 8 页 × 3 次重试） |
> | 11ba7b2 | mimo-vl 短超时 45s + max_retries=1（挂起 90s 内降级 deepseek） |
>
> 测试：test_paddle_circuit_breaker.py 9 + test_vl_fast_fail.py 3 + test_vl_model_queue.py 12 = 24 passed

### 安全问题（2026-08-25）

> 诊断脚本硬编码 MIMO/DeepSeek/PaddleOCR API key（dacad48 引入），已修复（92a8c07）：
> - 9 个脚本改从 backend/.env 读取（load_dotenv），缺失时 SystemExit
> - 工作树无残留硬编码密钥
> - ⚠️ 密钥已进入 git 历史（dacad48），**需要轮换** MIMO/DeepSeek/PaddleOCR 三个 key
> - 可选：git filter-repo/BFG 重写历史彻底清除

**答案验证器证据模式**：
| 模式 | 适用场景 | 示例 |
|---|---|---|
| `table_mode` | 题号行+答案行表格 | 化学、政治、数学、物理、生物 |
| `prefix_mode` | 题号+答案列表 | 英语选择题、语文选择题 |
| `inline_mode` | 故选X项、答案：X | 历史 |
| `free_text_mode` | 长文本/公式答案 | 化学填空题、物理计算题 |
| `composite_mode` | 综合题子题分布 | 语文综合题、英语完形 |

**验证原则**：
1. 以原始 PDF 文本层为主判据（PyMuPDF `page.get_text("text")`）
2. native_markdown 为交叉验证（验证管线 native 阶段是否忠实）
3. ocr_markdown 为辅助证据
4. 三者冲突时标记为 unverifiable，人工复查
5. unverifiable 不能算通过

---

## 文档基线

| 文档 | 版本 | 说明 |
|---|---|---|
| REQUIREMENTS_AND_SOLUTION.md | 0.2 | 真实需求与方案基线 |
| DICTIONARY.md | 0.8 | 字段、功能、状态字典 |
| PRD.md | 3.1 | 产品需求 |
| SAD.md | 4.5 | 系统架构 |
| ACS.md | 3.2 | API 合约 |
| MIS.md | 2.1 | MCP 工具规范，定位为 Agent 接口层 |
| PIPELINE.md | 5.0 | 文档入库管线 |
| DSD.md | 4.5 | 数据库结构 |
| UI.md | 1.1 | 前端设计与页面规范 |
| Design.md | 参考 | 前端视觉设计风格 |
| TASK.md | 1.6 | 任务执行规范 |
| RESTART_PROMPT.md | 2.2 | 重启恢复说明 |
| ROADMAP.md | 1.3 | 开发任务计划（执行基线） |
| PADDLEOCR_API.md | 1.1 | OCR API 项目资料 |
| V1_LESSONS.md | 2.1 | V1 经验教训与强制约束 |
| T3_IMPLEMENTATION.md | 2.0 | T3 实施基线（Annotation Paradigm） |

---

## 已知差距

- 已建立 `test/pdf/manifest.csv`，收集 30 份教师版 PDF，覆盖 9 科；`test/annotations/` 尚无 30 份人工标注 JSON，字段级准确率尚未形成真实基线。
- `run_parse_baseline.py` 的 mock 模式已验证；DeepSeek/MIMO/Qwen base/model 已配置，live 联调前需将 `LLM_GATEWAY_MODE=live` 并验证 Provider 可达性。
- PyMuPDF 已降级为辅助工具；`ppsv3_l1.py`（PP-StructureV3 L1 转换器）已实现；`l1_arbiter.py`（LLM 行级仲裁）已实现；pipeline 已集成双源 L1 + bbox 对齐 + LLM 仲裁。
- ✅ Golden 已基于 postprocessed PP L1 重建（v4.0），8 题行号/内容全部对齐（2026-08-12）。
- `explanation_line_ids`：golden 中 8 题均为空（`explanation_source: "llm_fallback"`），**已明确移出 Phase 1 验收范围**。Explanation 依赖 LLM 生成，属 Phase 2+ 范畴。
- ✅ `_normalize_answer()` 猜测逻辑已删除（2026-08-12）。
- ✅ `content_slicer._build_anchor_map()` 已改用 `(question_number, field)` 精确映射（2026-08-12）。
- ✅ PP L1 bbox 提取已修复，双源合并 + LLM 仲裁端到端验证通过（2026-08-12）。
- `question_images` 的 `page_no/bbox/placement/source/figure_id` 已在 DSD 固化，管线已生成，前端已按 `question_images` 展示配图。
- 知识树种子数据尚未初始化；启用知识点映射前必须补上。
- Alembic 初始迁移已在现有 PostgreSQL 的 aitutors 新库上执行成功；旧 ai_tutor 库未改动。
- qwen3-embedding:4b 为 2560 维，超过 pgvector HNSW 索引 2000 维上限，初始阶段使用暴力余弦检索。
- Docker CLI 可直接访问；`scripts/allow-codex-docker.ps1` 仅保留给沙箱账号场景。
- 前端依赖与构建已完成；解析审核台视觉优化完成，学生端仍为轻量外壳。
- 文档上传、查询、状态、重试和统一 Task 查询 API 已实现；完整文档解析管线、worker 消费和领域业务逻辑尚未实现。
- 题型规范需要根据真实文档细化。
- 标准知识树需要根据管理员提供的资料初始化。
- 字典文档已建立，后续新增字段/功能需同步维护。
- 化学表格选项（P2）：PPS/VL 对 HTML table 选项都是短板。
- 数学答案可疑（P2）：Q21/Q22 LaTeX 答案被质量门标记。
- 历史 JSON 解析（P2）：LLM 偶发输出无效 JSON，需加重试。
- VL API 队列保护（P2）：连续多科跑 VL 时队列满风险，需单提交者保护。
- `is_composite` / `sub_questions` 已进入 L2/切片管线，但 `questions` 表的 DB model / Alembic migration 尚未补齐。

---

## 下一步

### P0 — Phase 2A 数据底座修复（当前，设计已冻结）

设计基线：`Docs/01_Product/PLAN_QUESTION_FAMILY.md` v2.0
ROADMAP 基线：`Docs/01_Product/ROADMAP.md` v2.0 P4A
执行控制：`docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md` v1.1
代码审计：2026-08-21，发现审核不写回 DB、Worker 失败语义错误、L2 Annotation 被裁剪

| Step | 任务 | 状态 | 验收 |
|---|---|---|---|
| 0 | Step 1 复核 + 真实回填演练 | ✅ 验收通过 | pytest 迁移演练（`test_phase2a_step0_migration_rehearsal.py`，一次性临时库，7 项断言：document_id 回填、COALESCE、year/school 删除、唯一索引拒绝重复、downgrade 有损）+ 脚本版（`backend/scripts/step0_backfill_verify.py`，8/8）+ ingestion 真实路径 2 条；Step 0 集成 18 项通过 |
| 1 | DSD 变更 + 最小入库适配 | ✅ 验收通过 | migration 已执行 (20260821_0003)；model/DB document_id NOT NULL；29 条结构测试通过；DB 与 DSD §8 一致（列/索引/约束 SQL 验证）；Step 0 回填证据关联确认 |
| 2 | 审核决定写回 DB | ✅ 验收通过 | questions.status 和 override 内容真实变化（`backend/scripts/step2_db_verify.py` 证据）；question_instances 唯一定位；Step 2 集成测试 11 项通过 |
| 3 | Worker 失败语义 + L2 完整持久化 | ✅ 验收通过 | ingestion 异常 → task failed + document failed；答案提取失败 → retry queue（task 仍 succeeded）；llm_annotated_markdown 完整 L2 字段（`backend/scripts/step3_db_verify.py` 8/8）；幂等重跑只清理未审核记录 |
| 4 | 答案重试关联修正 | ✅ 验收通过 | `answer_retry_worker` 改用 question_instances(document_id, source_question_number) 精确关联；同文档 3 道空答案各自正确更新；不同文档同题号不污染；找不到 Instance 记录失败；已有答案不覆盖（`backend/scripts/step4_db_verify.py`） |
| 5 | 精确去重 content_hash | ✅ 验收通过 | `content_hash.py` SHA256(规范化题干+选项+题型+子题)；ingestion 按 content_hash 匹配；hash 相同答案不同 → review_reason='answer_conflict' + 降 reviewing，不建重复 Question；migration 20260821_0005 回填；DB 验证重复组=0/NULL=0 |
| 6 | 知识点映射落库 | ✅ 验收通过 | `KnowledgeService.map_question_to_knowledge`：关键词匹配知识树节点写 question_knowledge（mapping_source='rule'）；低置信度 → pending；空/无命中 → 回退 {SUBJ}-UNKNOWN + pending；综合题子题级映射（`backend/scripts/step6_db_verify.py`：函数单调性→MATH-ANA） |

### P1 — 基础统计与搜索 ✅ 已实现（2026-08-21 Phase 2B）

- ✅ 知识点 × 题型 × 年份统计 API（`GET /api/admin/statistics`：total / question_type_distribution / knowledge_point_distribution / difficulty_distribution / year_trend）
- ✅ 条件搜索（`GET /api/admin/questions`：学科/题型/知识点/年份/学校/难度/来源/状态 + 分页）
- ✅ 高频知识点排行（knowledge_point_distribution 按出现次数降序）
- 实现：`QuestionRepository.search/statistics`、`QuestionApplicationService.search_questions/get_statistics`、`app/api/routes/questions.py`；测试 12 项（`test_phase2b_search_stats.py` 9 + `test_phase2b_api.py` 3）

### P2 — Similarity / Family（暂缓）

9. Phase 2D Similarity/Family 研究 — 前置条件：样本量 + golden set + Structure Signature raw 分布。
10. **blocked 比例纳入门禁** — 英语 31.6% blocked 需要关注。

### P0 — 入库管线数据质量修复（2026-08-22 审计驱动，进行中）

> 背景：30 份教师版 PDF 真实入库验证（23 份完成、444 题）后，对管线做 4 模块深度审计（line_annotator / content_slicer / answer_matcher+quality_gate / ingestion+配图），发现 5 个 P0 + 4 个 P1 问题。完整审计结论已整合到 `bugs.md`。
> 修复原则：每个修复必须配套严格测试并通过验证，绝不虚空通过。

| # | 问题 | 根因 | 严重度 | 状态 |
|---|---|---|---|---|
| 1 | 配图覆盖率低（1426→221 张，15.5%） | `_build_question_images` 读 `q.stem_line_ids`/`q.options_line_ids` 属性，但 SlicedQuestion 无此属性（行号在 stem_anchor.corrected_line_ids）→ stem/options 分支永不执行；中心点判定过严；native 图被丢弃 | P0 | ✅ 已修复（2026-08-22） |
| 2 | 题型 423 题 question_type_id 全 NULL | question_types 表无种子数据 + `_get_question_type_id` 只查不建 | P0 | ✅ 已修复（2026-08-22） |
| 3 | 难度 88% NULL | prompt L457 标 difficulty 为"可选字段" + 无判断依据 + 无校验回填 | P0 | ✅ 已修复（2026-08-22） |
| 4 | 英语综合题材料并入题干仍 0.9 approved | quality_gate 无材料混入/stem 异常检测（L143-144 自述放弃）；0.9 是结构分非内容分 | P0 | ✅ 已修复（2026-08-22） |
| 5 | 综合题材料并入题干（根因层） | prompt L518 明文要求 stem_line_ids=材料全文+子题行号 + content_slicer L210 显式并入 | P0 | ✅ 已修复（2026-08-22） |
| 6 | 合并综合题答案丢失 | `_slice_single_question` 不传 answer，子题 12-20 答案入库前丢失 | P1 | ✅ 已修复（2026-08-22） |
| 7 | 答案合并绕过 V1_LESSONS 3.8 | LLM answer_map 无条件覆盖教师版答案表答案 | P1 | ⬜ 待修复 |
| 8 | 配图元数据丢失 | `_build_question_images` 只输出 3 个 key，page_no/bbox/source/figure_id 落 None | P1 | ✅ 已修复（2026-08-22，随 P0-1 修复） |
| 9 | dedup figure_mapping 不被消费 | 被去重图片位置不再参与关联，多对多失效 | P2 | ⬜ 待修复 |

### P0/P1 — 管线对抗性审查驱动修复（2026-08-23）

> 背景：三方对抗性审查（Claude + Codex + MiMo）+ 真实 e2e 运行（10 份 PDF，9 成功 / 1 失败）。审查结论已整合到 `bugs.md`。

| 编号 | 问题 | 状态 | 验收证据 |
|---|---|---|---|
| P0-A | ingestion 无逐题事务隔离（单题失败 → session 毒化 → 整份文档陪葬） | ✅ 已修复 | 3 项测试 + 诊断脚本（commit e4b9150） |
| P0-B | stem 结束位置未校验（LLM 标注范围包含下一题行） | ✅ 已修复 | 8 项测试（函数级 + 集成级 + anchor 同步）（commit e4b9150 + 4196ab7 + c23b25d） |
| P0-C | 综合题 e2e 回归测试（当前 e2e 只覆盖无综合题的数学 PDF） | ⬜ 待修复 | — |
| P1-A | 子题号归一化覆盖不完整（`line_annotator.py:192` 已有正则但部分 LLM 格式命中不了） | ⬜ 待修复 | — |
| P1-B | reviewing 题在学生端 API 的可见性核查 | ⬜ 待修复 | — |
| P1-C | 答案表解析加固 + 覆盖 LLM 时题型一致性校验 | ⬜ 待修复 | — |
| P1-D | 任务失败原因可靠落库（当前 processing/running 但 result_json 为空） | ⬜ 待修复 | — |

### P2 — 扩展

7. DOCX 支持。
8. embedding 维度优化。
9. 化学表格选项、历史 JSON 重试等收口项。

Phase 1 管线验证通过（2026-08-13）：
- ✅ PP L1 bbox 提取修复（paddle_client 解析 block_bbox 数组，ppsv3_l1 使用 bbox 构建 L1Line）
- ✅ l1_arbiter gateway.generate bug 修复
- ✅ pipeline.py 移除硬编码 mock=True
- ✅ 双源 L1 合并生效（mock: dual_source_lines=104，native_only_lines=69；live-pp: dual_source_lines=104，native_only_lines=69）
- ✅ LLM 行级仲裁端到端执行（mock: llm_audited=104, conflicts=94；live-pp: llm_audited=104, conflicts=42）
- ✅ 锚点校正器工作（mock: exact=32；live-pp: exact=53）
- ✅ 内容切片正确（mock: stem_content 100%；live-pp: golden 内容 100%）
- ✅ 答案匹配正确（mock: answer 100%；live-pp: golden answer 100%，20:33 全卷 answer_matched=16/21）
- ✅ 质量门评估（mock: high=8, low=0, blocked=0；live-pp: high=14, medium=2, low=5, blocked=7）
- ✅ Phase 1 复审修复：答案表括号答案、LaTeX 续行题号、行内全角括号题号切分
- ✅ 题型归一化：中文 `填空题`/`解答题` 等映射到 canonical 枚举，prompt 明确 canonical 题型
- ✅ 对抗性审查结论：golden 8 题全字段 100%；全卷低置信度项均已按题标记，未静默发布
- ✅ eval 脚本增强：支持 --live 模式，增加 anchor_status/provenance/quality 检查
- ✅ run_ppsv3_eval.py 标记 DEPRECATED
- ✅ l1_arbiter 补充 5 项单元测试（arbitrate_lines + apply_arbitration）
- ✅ 后端 143 项测试全部通过

Phase 0 已完成（全部验收通过，详见更新记录 2026-08-11）。

---

## 更新记录

### 2026-08-10 21:56:55

- 按新规范调整本文件：顶部保留当前状态快照，所有新增变更记录追加到文末。
- 新增 `RESTART_PROMPT.md` 到文档基线。

### 2026-08-10 22:10:28

- 采纳 Question Aggregate、统一 Background Task、Domain Event 和字段级验收指标。
- 调整 MCP 定位：正常业务不强制 MCP，MCP 仅作为 Agent 接口层。
- 增加 Phase 0 至 Phase 5 的开发路线。

### 2026-08-10 22:17:19

- 新增 `DICTIONARY.md`，统一记录核心字段、功能、状态枚举。
- 在 `rules.md` 和 `TASK.md` 增加字典维护要求。

### 2026-08-10 22:41:06

- 初始化 Phase 0 项目骨架。
- 新增后端 FastAPI 骨架、前端 React/Vite 骨架、Docker Compose、`.env`、`.env.example` 和 README。
- 后端 `compileall` 通过，`docker compose config` 通过。
- 前端 `npm install` 因环境限制超时，尚未生成 `package-lock.json` 和 `node_modules`。

### 2026-08-10 23:07:14

- 扩展 Phase 0 后端分层骨架。
- 新增 22 张 DSD 表 SQLAlchemy 模型、异步数据库会话和 Alembic 初始迁移。
- 新增 Repository、Domain Service、Application Service 分层骨架。
- 新增统一 Background Task、Domain Event 发布/消费骨架和 LLM Gateway mock/live 路由。
- 新增 ACS 标准响应包装（`request_id`、`latency_ms`）及对应测试。
- 后端 5 项测试通过；Alembic offline SQL 生成通过；Docker API 权限不足，未实际执行数据库迁移。

### 2026-08-10 23:30:50

- 定位 Codex Windows 沙箱与 Docker Desktop 权限隔离原因：沙箱账号 `CodexSandboxOffline` 无法访问 Docker Desktop 用户会话命名管道。
- 新增 `scripts/allow-codex-docker.ps1`，用于持久授权：Codex permission profile 放行 localhost/`.docker` 配置/Docker 管道，并将沙箱账号加入 `docker-users`。
- 待重启 Docker Desktop 与 Codex 后验证 Docker CLI 与 localhost 数据库端口连通性。

### 2026-08-10 23:54:42

- 复用现有 aitutor-postgres(15432)/aitutor-redis(16379)/aitutor-minio(9000)，移除误建的新容器。
- 在现有 PostgreSQL 中新建 aitutors 库执行 Alembic 初始迁移，旧 ai_tutor 库未改动。
- 确认 embedding 使用本地 Ollama qwen3-embedding:4b（2560 维）；因 HNSW 上限 2000 维，初始迁移不建向量索引，改用暴力余弦检索。
- docker-compose.yml 改用 pgvector/pgvector:pg16，并新增 EMBEDDING_PROVIDER/MODEL/DIMENSION 配置。
- 后端测试 5 项通过，docker compose config 通过，alembic upgrade head 成功。

### 2026-08-11 00:08:00

- 新增 `Docs/01_Product/ROADMAP.md`，将开发任务计划固化为执行基线。
- 新增 `Docs/02_Architecture/PADDLEOCR_API.md`，保存 PaddleOCR-VL-1.6 与 PP-StructureV3 API 示例资料。
- 明确测试数据、测试脚本和测试结果统一放在 `test/`，并写入 `rules.md` 与 `TASK.md`。

### 2026-08-11 00:30:16

- 完成 P0 收口：接入现有 MinIO，新增依赖健康检查 `/api/health/dependencies`，本地启动后端并验证 PostgreSQL/Redis/MinIO 全部连通。
- 生成 `test/pdf/manifest.csv`，新增 `test/scripts/generate_pdf_manifest.py` 与 `test/scripts/validate_pdf_baseline.py`，30 份 PDF、9 科基线校验通过。
- 补齐 `backend/scripts/validate_docs_vs_code.py`，当前文档与代码校验通过。
- 完成 P1：实现文档上传、MinIO 对象写入、文档记录/Background Task/Domain Event 创建，以及文档与任务查询、状态、重试、日志 API。
- 后端测试由 5 项增加到 12 项，全部通过；使用真实 PDF 完成上传、MinIO 落盘、状态查询和重试验证。

### 2026-08-11 00:45:41

- P2 文档解析验证代码闭环落地：新增 PP-StructureV3 客户端、OCR/VL 回退链、LLM 结构化 Question Aggregate 提取和文档解析编排。
- 新增 `test/scripts/run_parse_baseline.py`、`test/scripts/evaluate_parse_accuracy.py`、`test/annotations/README.md` 与 mock fixtures。
- 后端测试由 12 项增加到 20 项，全部通过；`validate_docs_vs_code.py` 通过；AST 语法检查通过。

### 2026-08-11 07:07:42

- 新增 `Docs/05_Development/V1_LESSONS.md`，固化 V1 在解析、配图、来源、审核、测试和部署中的已验证教训。
- 更新 `rules.md`、`TASK.md`、`PIPELINE.md`、`SAD.md`、`ROADMAP.md`、`DICTIONARY.md`、`DSD.md`、`RESTART_PROMPT.md`。
- 明确正式 T3 前必须将 `question_extractor.py` 改为行号标注范式，并补齐 Native PDF 优先和图片位置元数据。

### 2026-08-11 07:19:47

- 补充“LLM 行号不准”风险：LLM 行号仅作粗定位，代码必须做锚点校正。
- 固化 `llm_anchor/corrected_anchor/anchor_status` 契约；未校正行号禁止直接切片入库。

### 2026-08-11 07:29:33

- 按差距分析补充 `V1_LESSONS.md` 至 1.2，新增 3.16-3.29 共 14 条解析/审核/图片/答案区教训。
- 更新 `RESTART_PROMPT.md` 至 0.8，明确后续 T3/P3 必须遵守新增约束。

### 2026-08-11 07:33:00

- 配置 DeepSeek OpenAI 兼容地址：`https://api.deepseek.com`，模型：`deepseek-v4-flash`。
- `LLM_GATEWAY_MODE` 保持 `mock`，未擅自切换 live。

### 2026-08-11 07:35:00

- 配置 MIMO OpenAI 兼容地址：`https://api.xiaomimimo.com/v1`，模型：`mimo-v2.5`。
- `LLM_GATEWAY_MODE` 保持 `mock`，未擅自切换 live。

### 2026-08-11 07:44:54

- 配置 Qwen VL OpenAI 兼容地址与模型；API Key 仅写入 `backend/.env`，不写入文档/示例文件。
- DeepSeek/MIMO/Qwen 三类 Provider 参数已齐备，`LLM_GATEWAY_MODE` 保持 `mock`。

### 2026-08-11 09:30:00

- T3 Phase 0 完成：L1/L2 Schema、LLM fixture + Golden Set、LLM Provider Smoke Test、L1 后处理规则。
- 新增 `test/fixtures/l1_snapshot.json`（数学 L1 fixture，18 行，7 题）。
- 新增 `test/fixtures/l1_snapshot_english.json`（英语 L1 fixture，11 行，5 题）。
- 新增 `test/annotations/golden/math_exercise_2024.json`（数学 Golden Set，7 题）。
- 新增 `test/annotations/golden/english_exercise_2024.json`（英语 Golden Set，5 题）。
- 新增 `test/scripts/llm_smoke_test.py`（8 项测试全部通过）。
- 新增 `backend/app/domains/document/l1_postprocessor.py`（题号换行、选项切分、行号重编）。
- 新增 `backend/tests/test_l1_postprocessor.py`（8 项单元测试全部通过）。
- 修复 3 个 Bug：小数误拆、中文字符误跳、IndexError。
- 完整测试结果：36 项全部通过。
- 更新 `PROJECT_STATUS.md`：状态更新为 Phase 0 完成，准备进入 Phase 1。
- 更新 `LOG.md`：记录 Phase 0 完成详情。

### 2026-08-11 09:30:00

- 新增 `T3_IMPLEMENTATION.md`（v1.0），作为 T3 Annotation Paradigm 实施的执行基线。
- 冻结 `question_extractor.py` 和 `parser.py` LLM 路径（加 DEPRECATED 标记）。
- 更新 `V1_LESSONS.md` 至 1.3：图片去重语义修正（物理图存储去重 + 题图多对多 + 无证据广播抑制）。
- 更新 `DSD.md` 至 4.5：question_images 多对多语义 + L1/L2 中间态说明。
- 更新 `DICTIONARY.md` 至 0.7：新增 L1/L2/Quality Gate 概念。
- 按 T3_IMPLEMENTATION.md Phase 0-3 建立四阶段 Task 列表和依赖关系。

### 2026-08-11 14:06:37

- 记录本机 live 验证结果：DeepSeek passed，MIMO 超时，Qwen JSON 解析失败。
- 修正 Phase 0 状态为“待最终验收”，不再标记为已完成。
- 记录沙箱外网限制与真实本机网络可访问性的区别。
- 更新 RESTART_PROMPT 至 1.2，并补充后续验证清单。

### 2026-08-11 16:24:02

- 补齐 English L1 fixture 详解区（P1L059-P1L069）。
- 更新 English Golden Set 至 v3.1：10 题 `explanation_line_ids` 非空，`expected_anchor` 补齐 `explanation_line_ids`，`explanation_source` 改为 `document_inline_explanation`。
- smoke test 升级 English golden 断言：`explanation_line_ids` 与 `expected_anchor.explanation_line_ids` 非空；English fixture 行数更新为 69。
- 同步测试数：后端 41 + Smoke 13 = 54。

### 2026-08-11 23:49:10

- T3 Phase 1 改为架构重构中，不再标记验收通过。
- L1 架构调整为 PyMuPDF native + PP-StructureV3 双源，canonical L1 按证据生成。
- 同步更新 PIPELINE/T3/V1_LESSONS/DICTIONARY/ROADMAP/SAD/TASK/rules。

### 2026-08-12 Phase 1 真实验证修复

- 修复 PP L1 bbox 提取：paddle_client.py 解析 `prunedResult.parsing_res_list` 中的 `block_bbox`（数组格式 `[x1,y1,x2,y2]`），ppsv3_l1.py 优先使用 blocks 构建带 bbox 的 L1Line。
- 修复 l1_arbiter.py `gateway.generate()` → `gateway.complete()` 方法名 bug。
- 移除 pipeline.py 硬编码 `build_ocr_chain(mock=True)`，改为从 settings 读取。
- backend/.env 切换 `LLM_GATEWAY_MODE=live`、`OCR_MOCK_MODE=false`。
- run_phase1_eval.py 增强：支持 `--live` 模式（真实 PP OCR + 真实 LLM），增加 anchor_status/provenance/quality_gate 健康指标检查。
- run_ppsv3_eval.py 标记 DEPRECATED（自证逻辑）。
- l1_arbiter.py 新增 5 项单元测试（arbitrate_lines + apply_arbitration）。
- 后端测试 97 → 102 项全部通过。
- Live Eval 结果（DeepSeek + PP-StructureV3）：question_number/type/answer/options_line_ids/answer_line_ids/stem_content/options_content 均 100%，dual_source_lines=7，LLM 仲裁 125 行审计 7 冲突。

### 2026-08-12 对抗审查修复

- 对抗审查发现虚假数字（exact:42, nearest:6, retry:5 等）与所有数据源不匹配，已更新为真实数据。
- 修复 bbox 坐标系不匹配问题：PP 使用像素坐标（~150 DPI），PyMuPDF 使用 PDF points（72 DPI），比例约 2:1。
- pipeline.py 新增 `_estimate_bbox_scale_factor()` 和 `_normalize_bbox()` 函数，自动估算并归一化坐标系。
- mock 评估 dual_source_lines 从 7 提升到 87（归一化后 IoU 匹配成功）。
- 后端测试 110 项全部通过。

### 2026-08-13 19:26:10

- 对抗式审查更新 Phase 1 状态：mock/golden 子集通过，live-pp 全卷未达最终验收。
- 后端测试由 110 提升至 136：`pytest backend/tests -q` = 136 passed。
- Mock eval：8/8 指标 100%，dual_source_lines=102，native_only_lines=71，llm_audited=102，conflicts=92。
- Live-pp（2026-08-13 19:17 结果）：golden 8/8 字段 100%，全卷 21 题、answer_matched=14、blocked=7、quality high=10；验收状态为未最终验收。
- 同步更新 RESTART_PROMPT.md 与 adversarial_review_phase1.md。

### 2026-08-13 19:44:35

- Phase 1 复审修复完成：`answer_matcher` 答案表按题号边界切分，支持括号答案并停在解答题区；`anchor_corrector`/`pipeline` 题号正则排除 LaTeX 续行；`l1_postprocessor` 支持行内全角括号题号切分。
- 新增 6 项回归测试，后端 `pytest backend/tests -q` = 142 passed。
- Mock eval：8/8 指标 100%，answer/document_answer_table 8/8，dual_source_lines=104，blocked=0。
- 沙箱外网仍受 `WinError 10013` 限制，live-pp 未重跑；Phase 1 最终验收仍需本机执行 `python test/scripts/run_phase1_eval.py --live-pp` 后复审。

### 2026-08-13 20:33:00

- 用户本机重跑 live-pp：21 题、721639ms、golden answer/answer_line_ids 8/8，但 question_type=6/8、options_line_ids=6/8；失败项为 Q11/Q13 的 LLM 题型 `填空题`。
- 修复题型归一化：`content_slicer` 将中文 `填空题`/`解答题` 等映射为 canonical 枚举；`line_annotator` prompt 明确 canonical 题型。
- 新增题型归一化与 prompt 回归测试，后端 `pytest backend/tests -q` = 143 passed。
- 用同一 live-pp 结果按新映射复算：question_number/type/answer/stem_line_ids/options_line_ids/answer_line_ids/stem_content/options_content 全部 8/8 100%。
- 最终验收仍需用新代码在本机重跑 `python test/scripts/run_phase1_eval.py --live-pp`。

### 2026-08-13 21:50:57

- 用户用新代码重跑 live-pp：3 次运行取最差后 `PASS`，golden 8/8 全字段 100%，line ID errors=0。
- 对抗性审查完成：后端 `pytest backend/tests -q` = 143 passed；mock eval 8/8；live-pp golden 8/8。
- 审查结论：Phase 1 可按“golden 8 题纵向闭环”验收通过；全卷 7 blocked / 5 answer_empty 均带低置信度标记，作为 Phase 2/3 审核边界登记。
- 同步更新 PROJECT_STATUS.md、RESTART_PROMPT.md、LOG.md 与 adversarial_review_phase1.md。

### 2026-08-16 21:16:25

- 修复 PDF 视觉 OCR 回退：PDF 先逐页渲染 PNG 再调用 MIMO/Qwen；Paddle 队列满自动重试；batch 增加 per-PDF 异常与增量 summary。
- 新增 OCR fallback 测试；后端全量 **319 passed**；ACS 补齐 `parse-result`。
- Task 2.5 仍 NOT_ACCEPTED；live OCR smoke/batch 需用户本机重跑。

### 2026-08-17 13:20:32

- 语义锚点落地：`stem_markers` 只作定位计划，最终内容从 PP/native 原文切片；新增 `semantic_anchor.py`、题号校验、跨行题号容错。
- `PipelineResult.to_dict()` 新增 `llm_annotation` 诊断块，保存真实 LLM 响应与 marker 状态。
- 丰台物理 Q3/Q19 根因：`anchor_corrector` 题号正则把 `3.2025年...` 误判为小数；已修复并新增回归测试。
- 后端全量 **325 passed**；`compileall` 通过。
- `physics_validation` 3/4 runs 完成；九中 run2 挂起后已停止。
- 新增 9 科每科一份 PDF 验证脚本 `test/scripts/run_9subject_validation.py`，Task 2.5 仍 NOT_ACCEPTED。

### 2026-08-17 23:42:03

- 综合题透传修复完成：`content_slicer` 不再丢失 `is_composite/sub_questions`；英语验证 10 道综合题、45 个子题全部输出。
- Change 2 完成：解答题标题不再误判为答案区；Change 3 完成：LLM 重试会收到失败锚点提示。
- 数学验证：23 题、入库 21、丢弃率 8.7%；化学验证：25 题、入库 20、丢弃率 20.0%，Q12 已正确识别为综合题。
- 后端全量 **328 passed**；Task 2.5 仍 NOT_ACCEPTED。
- 待办：小规模验证化学/生物/地理是否应路由到 PaddleOCR-VL，再决定学科路由。

### 2026-08-18 00:20:00

- 解析审核前端闭环完成：文档审核接口支持保存 `review_overrides`，前端支持逐题审核、意见、字段修正、筛选和导出审核 JSON。
- 新增 `test/scripts/check_review_ui.py` 与截图；`validate_docs_vs_code.py` 通过。
- 后端全量 **332 passed**，前端 `npm run build` 通过。

### 2026-08-18 00:45:00

- 解析结果显示页增强完成：默认显示效果模式，KaTeX 渲染公式，按 `question_images` 展示配图。
- 保留审核操作模式；`check_review_ui.py` 已覆盖公式与配图渲染断言。

### 2026-08-18 00:46:00

- 前端视觉优化完成：`AdminHome.tsx` 增加品牌导航和毛玻璃 `result-toolbar`，将显示/审核切换、筛选、结果操作合并到顶部工具条。
- `theme.css` 按 `Docs/Design.md` 重写设计 token；`StudentHome.tsx` 改为轻量仪表盘外壳；`index.html` 补充 Inter fallback。
- 新增 `test/scripts/check_review_ui_responsive.py`；`npm run build` 通过，桌面与 390px 移动视口 Playwright 验证通过。

### 2026-08-18 18:48:33

- 9 科最终验证结果已写入：总丢弃率约 5%，化学 VL 0%，历史 9.3%，地理 12.5% 为预期行为。
- 地理状态改为 ✅：16/16 综合题（11 组单选题组 + 5 道材料分析题）；Q19 图片选项、Q23-Q25 试卷缺失为预期丢弃，实际丢弃率 0%。
- OCR 学科路由确认：化学走 PaddleOCR-VL-1.6，其余走 PP-StructureV3。
- 根目录恢复为权威文档；删除 `Docs/` 下重复的 `PROJECT_STATUS.md`、`LOG.md`、`RESTART_PROMPT.md`。

### 2026-08-20 07:15:00

#### 试卷结构门禁修复与 paper_structure.py 恢复

- `paper_structure.py` 已恢复为完整实现（groups-level 验证、composite/shared_material 检查、bottom_question_numbers 覆盖检查）。
- 试卷结构门禁测试全部通过（8/8）。
- 后端全量测试 378 passed；剩余 2 failed + 1 error 均为 DSH 沙箱 temp 目录权限问题（WinError 5），非代码 bug。
- 英语结构门禁状态更新为 ✅ PASS。

### 2026-08-20 08:30:00

#### Task 2.5 三科门禁验收通过

- **复现性归一化完成**：复合题按子题契约比较（is_composite + sub_questions + answer_line_ids），不再比较顶层 answer/stem_line_ids 的 LLM 格式化漂移。独立题保持严格比较。
- **adversarial_check 一致性**：`adversarial_check_live_validation.py` 直接复用 `rlv.check_reproducibility()`，独立复算与 report 一致。
- **报告重建完成**：从现有 math/english/physics run 文件重建 report.json，mode=live_pp，overall=PASS，failures=[]。
- **门禁验证通过**：`adversarial_check_live_validation.py --require-live-pp` FAIL=0，WARN=1（mock block empty 降级为 WARN，重建场景预期行为）。
- **三科门禁结果**：
  - 数学：复现性 0 diff，结构 top=21/bottom=21，answer_empty=0%
  - 物理：复现性 0 diff，结构 top=20/composite=2/bottom=25，answer_empty=0%
  - 英语：复现性 0 diff，结构 top=19/composite=8/bottom=54，answer_empty=0%
- **新科目 manifest 落地**：语文(8 groups/24 bottom)、化学(20 groups/20 bottom)、生物(40 groups/40 bottom)。
- Task 2.5 状态从 NOT_ACCEPTED 更新为**通过**。

### 2026-08-20 18:00:00

#### P0 入库流程实现

- 新增 `answer_extractor.py`：LLM 答案提取模块，从 OCR markdown 中提取题号→答案映射。
- 新增 `ingestion.py`：入库服务，将管线结果 + LLM 答案合并后写入 questions/question_instances/question_images。
- 修改 `processor.py`：新增 `extract_and_ingest()` 方法，管线成功后调用答案提取和入库。
- 修改 `document_worker.py`：管线成功后构造 L1 markdown，调用入库，结果写入 task result。
- 修改 `models/tables.py`：QuestionImage 补齐 page_no/bbox/placement/source/figure_id；Question 补齐 is_composite/sub_questions。
- 新增 Alembic migration `3d7ee1cb7c3a`。
- 新增 `test_answer_extractor.py`：18 项单元测试全部通过。
- 后端全量测试 395 passed。

#### LLM 答案提取方案验证

- 30 份 OCR markdown、9 个学科、约 800 道题，LLM 答案提取准确率 100%。
- 覆盖格式：HTML 表格、连写、每题独立、解答题解题过程提炼、LaTeX 公式、化学方程式。
- 覆盖特殊情况：集团校自创题、OCR 乱码、26 题特殊卷、写作题无答案。
- 验证方法：subagent 并行处理，逐份对照原文确认。

#### 对抗性审查（第二轮）

发现 6 个问题（2 P0 + 3 P1 + 1 P2），详见 PROJECT_STATUS.md 对抗性审查结论。

### 2026-08-20 22:40:51

#### Native/PP L1 行号编码分离完成

- PP 行号使用 `P1L001`，Native 行号使用 `N1L001`。
- canonical 双源 L1 保留 PP 行号体系；native 行号只写入 `raw_sources["native_line_id"]`，不暴露给 LLM 标注阶段。
- `pipeline._merge_dual_source()` 改为按 `(page, line_no)` 对齐 Native/PP，避免行号前缀不同后丢失证据绑定。
- `simple_pipeline._build_pp_canonical()` 同步写入 `native_line_id`。
- 更新 native fixture 为 `N1L001` 编码，并补充 merge/postprocessor/simple_pipeline 回归测试。
- 后端全量测试 407 passed；另有 1 个既有 `test_models` DSD 表清单失败（`answer_extraction_retries` 未列入 `EXPECTED_TABLES`），与本次改动无关。

版本升至 3.6。

### 2026-08-21

#### 化学/生物/语文 golden draft 降级

- "化学/生物/语文 golden draft 生成"从当前前置待办降级为"暂不生成"。
- 当前 draft 是管线输出，不是人工 golden；P0 的 9 科 live 验证和 golden 回归是不同机制，不应混为一谈。
- 新科目状态表 golden draft 列更新为 ⏸️（管线 draft，非人工 golden）。
- 待办区新增 golden 机制说明，明确后续补 golden 的触发条件。

### 2026-08-21

#### 知识树种子数据入库

- 从 V1 迁移 9 科知识树 seed 数据到 V2（`backend/app/domains/knowledge/tree_seed/`，12 个文件）。
- 新增种子脚本 `backend/scripts/seed_knowledge_tree.py`，适配 V2 UUID 模型。
- 数据库实际入库：9 subjects、333 knowledge_nodes、292 条 parent_id 关系。
- 版本升至 3.7。

### 2026-08-21

#### Phase 2A Step 1 完成：DSD 变更 + 最小入库适配

- Model 变更：Question 移除 year/school，新增 content_hash；QuestionInstance 新增 document_id（NOT NULL）；QuestionKnowledge 新增 mapping_source/review_status。
- Alembic migration 20260821_0003：已执行到 PostgreSQL，head 确认。回填使用 COALESCE，year/school 迁移到 Instance，部分唯一索引，drop questions.year/school。
- 入库逻辑适配：Question 不写 year/school，Instance 写 document_id，occurrence_count 改为 COUNT 驱动。
- 新增 29 条 Step 1 验收测试（test_phase2a_step1.py），覆盖 column/index/ingestion behavior/migration structure。
- 测试：448 passed（含 29 条 Step 1 + 16 条 Step 0 集成），4 failed（pre-existing），1 error（pre-existing）。
- SQL 验证：questions.year/school 已移除，content_hash 已添加；document_id NOT NULL；mapping_source/review_status 已添加。
- 版本升至 3.9。

#### 2026-08-21 Step 0 复核完成

- 新增 16 条 Step 0 集成测试（test_phase2a_step0_integration.py），在真实 PostgreSQL 上验证：
  - document_id 回填、COALESCE 行为、NULL year/school 允许
  - 唯一约束负面用例（重复 (document_id, source_question_number) 被拒绝）
  - NULL source_question_number 允许重复（部分索引排除 NULL）
  - Question 不写 year/school、Instance 写 document_id
  - occurrence_count = COUNT(instances)
  - document_id NOT NULL 约束（不提供时 DB 拒绝）
- 数据库验证脚本 step0_db_verify.py 执行通过。
- 全量 pytest 448 passed。
- migration 已确认执行到 `20260821_0003`；当前 `question_instances=0` 行，真实数据回填证据需按 `docs_archive/2026-08-24/PHASE_2A_EXECUTION_PLAN.md` Step 0 补齐。

#### 2026-08-21 Step 0 复核修正

- 稳定全量命令实际为 453 passed，0 failed：
  ```powershell
  cd D:\Project\AITutors-v2
  $env:DATABASE_URL = (Select-String -Path backend\.env -Pattern '^DATABASE_URL=').Line -replace '^DATABASE_URL=',''
  python -m pytest backend\tests -q
  ```
- 现有 `test_phase2a_step0_integration.py` 的“回填”测试是直接插入带 `document_id` 的 Instance，未执行旧 schema 到新 schema 的 migration，不能作为回填证据。
- `test_occurrence_count_updates_with_instances` 是手工更新 `occurrence_count`，未验证 ingestion 的真实更新路径。
- `test_pipeline_merge.py` 的 fixture 路径已改为基于 `__file__` 的绝对路径，消除 backend 目录下运行失败。

### 2026-08-21 07:02:01

#### Phase 2A Step 2 代码实现完成（审核决定写回 DB）

> 注：Step 0 未验收、Step 1 ⚠️ 为外部复核结论（真实 migration 回填演练缺失）。Step 2 代码已实现并通过测试，但按执行计划「Step 未验收不得进入下一步」，正式验收待 Step 0/1 前置完成后确认。本记录仅登记实现状态与证据，不代表验收通过。

**代码变更：**
- `backend/app/domains/question/repository.py`：新增 `find_by_document_and_question_number()`，通过 `question_instances(document_id, source_question_number)` JOIN 唯一定位 Question，禁止按题号全局匹配任意同号题。
- `backend/app/domains/question/service.py`：新增 `get_question()`、`find_by_document_and_question_number()`、`apply_review()`（status + overrides 写回，flush）。
- `backend/app/application/services.py`：`DocumentApplicationService` 新增可选 `question_service` 注入；`update_document_review` 重构为「先定位题目（只读）→ 写 task.result_json → 写 questions 表 → commit」；定位优先级：显式 question_id（API body 或已有 review_decisions 携带）→ `(document_id, source_question_number)`；定位失败返回 `QUESTION_NOT_FOUND` 且不污染 result_json。
- `backend/app/api/dependencies.py`：注入 `QuestionService`。
- `backend/app/api/routes/documents.py`：审核接口支持可选 `question_id`（UUID 校验），新增 `QUESTION_NOT_FOUND` → 404 错误映射。

**测试：**
- 新增 `backend/tests/test_phase2a_step2_integration.py`：11 项，覆盖执行计划 Step 2 全部必须测试（定位不串题、approved/rejected DB 写回、overrides 写回、部分 overrides、question_id 优先、QUESTION_NOT_FOUND、端到端真实 DB SELECT 验证）。
- `backend/tests/test_document_api.py`：Fake 服务签名同步 `question_id` 参数。
- Step 2 集成测试 11 passed（真实 PostgreSQL，根目录 + 注入 DATABASE_URL）。
- 全量 pytest（根目录 + 注入 DATABASE_URL）：**461 passed**，2 failed + 1 error 为沙箱 temp 权限（WinError 5，用户本机可写），Step 2 前基线同样存在，无回归。
- DB 验证：`backend/scripts/step2_db_verify.py` 输出 `SELECT q.status, q.stem, q.answer ... WHERE qi.document_id=<doc> AND qi.source_question_number='12'` = `approved / Step2 修正后的题干 / D`；`review_decisions[12]` 与 `review_overrides[12]` 同步写入 task.result_json。
- migration 无变更（Step 2 无 schema 变更），`alembic current` = `20260821_0003 (head)`。

版本升至 4.0。

### 2026-08-21 07:30:00

#### Phase 2A Step 0 验收通过：真实回填演练 + ingestion 真实路径补齐

**背景**：外部复核指出 Step 0 未验收——现有集成测试只验证当前 schema 插入/约束，未执行 migration upgrade，不能证明旧数据回填；`test_occurrence_count_updates_with_instances` 是手工更新 count，未走 ingestion 真实路径。

**新增 `backend/scripts/step0_backfill_verify.py`（一次性临时库演练）：**
- 创建临时库 `aitutors_step0_verify`（演练后删除，主库无污染）
- `alembic upgrade 3d7ee1cb7c3a`（旧 head）→ 插入旧 schema 数据（2 docs / 3 questions / 3 instances，覆盖 year/school 缺失边界）→ `alembic upgrade 20260821_0003`（真实执行回填 migration）→ 验证 SQL → `alembic downgrade 3d7ee1cb7c3a`（回退验证）
- 验证结果（8/8 项）：
  1. questions.year/school 残留列 = 0 ✅
  2. document_id 回填 3/3 `doc_id匹配=True`（source_document_name = documents.filename）✅
  3. COALESCE 不清空已有值：Q2 保留 `year=2030, school=已有学校`；Q1 从 question 回填 `2024/朝阳中学`；Q3 部分回填 ✅
  4. NULL document_id 计数 = 0 ✅
  5. 唯一索引 `ix_question_instances_doc_qno` 存在 ✅
  6. 回填后重复 (document_id, source_question_number) 组数 = 0 ✅
  7. 负面用例：重复插入被 `UniqueViolationError` 拒绝 ✅
  8. downgrade 回退：year/school 列恢复、document_id 移除、数据有损（已标注，行保留）✅
- 修正：`command.upgrade` 到祖先 revision 是 no-op，downgrade 必须用 `command.downgrade`

**Step 0 集成测试补齐（`test_phase2a_step0_integration.py` 新增 2 条 ingestion 真实路径）：**
- `test_ingestion_creates_question_without_year_school`：真实 `ingest_pipeline_result` → Question 无 year/school 字段、Instance 写 document_id、year/school 从 document 带出
- `test_ingestion_exact_match_creates_instance_and_updates_count`：同一 PDF 上传两次（两个 Document）→ 第二次只创建 Instance、不创建新 Question、occurrence_count = COUNT(instances)（ingestion 更新路径，非手工）
- 语义确认：同一 document_id + 同题号重复受唯一索引保护（属 Step 3 幂等重跑清理范围）；精确去重对应「不同 Document 上传相同内容」

**证据：**
- 演练脚本输出：`test/results/step0_backfill_verify2.txt`（8/8 项验证通过，临时库已清理）
- 主库验证：`alembic current` = `20260821_0003 (head)`；`alembic heads` 一致；`upgrade head` 无操作
- Step 0 集成测试：**18 passed**（16 原有 + 2 新增，真实 PostgreSQL）
- 全量 pytest（根目录 + 注入 DATABASE_URL）：**463 passed**，2 failed + 1 error 为沙箱 temp 权限（WinError 5，用户本机可写），无回归

**完成判定对照（PHASE_2A_EXECUTION_PLAN Step 0）：**
- `alembic current` = `20260821_0003` ✅
- 数据回填测试在真实 PostgreSQL 上通过 ✅
- 文档来源 Instance document_id 全部非 NULL ✅
- 唯一索引内无重复，重复插入被拒绝 ✅
- questions.year/school 0 行残留 ✅
- pytest 463 passed（沙箱剩余项仅 temp 权限）✅

版本升至 4.1。

### 2026-08-21 08:00:00

#### Phase 2A Step 1/2 正式验收 + Step 3 实现验收（Worker 失败语义 + L2 完整持久化）

**Step 1 正式验收（此前为 ⚠️）：**
- 29 条结构测试全部通过（`test_phase2a_step1.py`：列/索引/模型/迁移结构）
- DB 与 DSD §8 一致 SQL 验证：questions 无 year/school 有 content_hash；instances 有 document_id NOT NULL；qk 有 mapping_source/review_status；唯一索引 `ix_question_instances_doc_qno` 存在；document_id NULL 计数=0；重复组数=0；questions.year/school 列已删除
- 主库数据：documents=2, questions=0, question_instances=0
- Step 0 回填证据已关联确认 → Step 1 验收通过

**Step 2 正式验收（此前为"代码已实现"）：**
- Step 2 集成测试 11 项重跑通过（真实 PostgreSQL）
- 前置（Step 1）已验收 → Step 2 验收通过

**Step 3 实现 + 验收：**
- 代码变更（`backend/app/worker/document_worker.py`）：
  1. **失败语义修复**：ingestion 异常不再置 task succeeded + document completed，改为 `task.status='failed'`（error_detail="ingestion failed: ..."）+ `document.processing_status='failed'`（含 error_message）；答案提取失败仍走 retry queue（extract_and_ingest 内部捕获，不在此路径）
  2. **L2 完整持久化**：`llm_annotated_markdown` 从仅 6 字段扩展为完整 L2 JSON——文档级（subject/grade/year/school/metadata_confidence/warnings/anchor_status_summary/corrected_anchors）+ 题目级（question_type/section_id/knowledge_points/difficulty/score/confidence/source_page/is_composite/sub_questions/全部行号字段）
  3. **幂等重跑清理**：新增 `_cleanup_unreviewed_records()`，ingestion 前删除该文档 `source_type='document'` 且 `status='reviewing'` 的记录；已审核（approved/rejected）保留，不静默覆盖
- 新增 `backend/tests/test_phase2a_step3_worker.py`：7 项（ingestion 异常→failed、ingestion 正常→succeeded/completed、答案提取失败→retry queue、L2 完整字段、清理只删未审核、跨文档不误删、已驳回保留）
- 同步旧测试 `backend/tests/test_worker_status.py`：mock session 补 scalars/get/delete/flush（幂等清理调用）+ pipeline 成功路径 mock extract_and_ingest 返回 IngestionResult（12 项通过）
- 新增 `backend/scripts/step3_db_verify.py`：真实 DB 验证幂等清理（reviewing 删/approved 留）+ L2 序列化 8/8 字段 OK
- 全量 pytest（根目录 + 注入 DATABASE_URL）：**470 passed**，2 failed + 1 error 为沙箱 temp 权限（WinError 5，用户本机可写），无回归（463 → 470，+7 Step 3）

**执行计划 Step 3 完成判定对照：**
- ingestion 异常 → task failed + document failed ✅（测试 + 代码路径）
- 答案提取失败 → task 仍 succeeded + retry queue ✅（测试）
- llm_annotated_markdown 含 knowledge_points/difficulty/score/corrected_anchors/anchor_status/question_type ✅（测试 + DB 脚本 8/8）
- 同一文档重跑只清理未审核记录 ✅（集成测试 + DB 脚本）
- 已审核记录和 review_overrides 非空记录不被静默覆盖 ✅（approved/rejected 保留测试）

版本升至 4.2。

### 2026-08-21 08:30:00

#### Phase 2A Step 4 实现 + 验收：答案重试关联修正

**背景**：`answer_retry_worker.py:127-142` 原实现按 `source_document_name + 顺序` 猜测题目（TODO 标注），同文档多道空答案题会串题。

**代码变更（`backend/app/worker/answer_retry_worker.py`）：**
- `_process_one_retry` 答案更新路径重写：
  - 遍历 `answer_result.answers`（题号 → 答案），每个题号用 `QuestionRepository.find_by_document_and_question_number(item.document_id, q_num)` 精确定位（内部 JOIN `question_instances(document_id, source_question_number)`）
  - 找不到 Instance → 记录失败（`mark_failed`，错误含 "not found via question_instances"），不更新任何题目
  - 只填充空答案（`answer` 为空时），已有答案（人工审核/管线结果）不覆盖
  - document 不存在或无 ocr_markdown → mark_failed（既有路径保留）
- 删除 `source_document_name + 顺序` 猜测逻辑与 TODO

**新增 `backend/tests/test_phase2a_step4_retry.py`：5 项（真实 PostgreSQL，mock 答案提取）**
- `test_retry_updates_each_question_correctly`：同一文档 3 道空答案题 → Q1→A、Q2→B、Q3→C，retry succeeded
- `test_retry_does_not_pollute_other_documents`：不同文档同题号 → 只更新本文档
- `test_retry_missing_instance_marks_failed`：题号无对应 Instance → mark_failed，不更新错误题
- `test_retry_document_not_found_marks_failed`：document 无 ocr_markdown → mark_failed（FK 约束验证：不存在的 document_id 插入被 DB 拒绝，测试改为真实 document 无 markdown 路径）
- `test_retry_does_not_overwrite_existing_answer`：已有答案保留

**新增 `backend/scripts/step4_db_verify.py`：** 真实 DB 执行执行计划验证 SQL → `Q1→A、Q2→B、Q3→C`（同 document_id 精确关联，无串题），retry status=succeeded，数据已清理。

**证据：**
- Step 4 测试：**5 passed**（真实 PostgreSQL）
- 全量 pytest（根目录 + 注入 DATABASE_URL）：**475 passed**，2 failed + 1 error 为沙箱 temp 权限（WinError 5，用户本机可写），无回归（470 → 475，+5 Step 4）
- DB 验证：`test/results/` 下 step4 脚本输出（Q1/Q2/Q3 精确更新）

**执行计划 Step 4 完成判定对照：**
- 每个题号更新到对应 Question ✅（DB 验证 + 测试）
- 同一文档 3 道空答案题各自正确更新 ✅
- 不同文档同题号不污染 ✅
- document_id/source_question_number 找不到 Instance → 记录失败 ✅
- 全量测试通过 ✅

版本升至 4.3。

### 2026-08-21 09:00:00

#### Phase 2A Step 5 实现 + 验收：精确去重 content_hash

**设计冻结（执行计划前置条件）：**
- content_hash 规范化规则：SHA256(规范化题干 + 规范化选项 + 规范化题型 + 规范化子题)；规范化 = Unicode NFKC + 全角转半角 + 去空白/标点 + 小写，选项/子题排序保证确定性
- 答案冲突承载：不建新表，复用 Question.review_reason='answer_conflict' + status 降为 reviewing（可查询，符合"禁止临时发明表结构"）
- 综合题：子题 qno+type+answer 参与 hash，不同子题配置视为不同题目

**代码变更：**
- 新增 `backend/app/domains/document/content_hash.py`：`normalize_text` / `normalize_options` / `normalize_sub_questions` / `compute_content_hash`
- `backend/app/domains/document/ingestion.py`：
  - `_ingest_one_question` 去重从 `_find_exact_match`（只看 stem）改为 `_find_by_content_hash`（content_hash 匹配）
  - 创建 Question 时写 content_hash
  - hash 相同但答案不同 → 不创建重复 Question，`review_reason='answer_conflict'` + status 降 reviewing（保留原答案）
- 新增 `backend/alembic/versions/20260821_0005_backfill_content_hash.py`：回填已有 questions 的 content_hash（含 question_types 联查题型、子题参与），兜底保证无 NULL；已执行到主库（0 条回填，主库 questions=0）

**新增 `backend/tests/test_phase2a_step5_content_hash.py`：10 项**
- 规范化确定性 6 项（空白/标点/全角/Unicode、选项顺序无关、不同选项不同 hash、不同题型不同 hash、SHA256 64hex、子题参与）
- ingestion 集成 4 项（同 PDF 两次只建 Instance、同 stem 异选项建不同 Question、答案冲突不建重复且标记 answer_conflict、content_hash 非 NULL）

**证据：**
- Step 5 测试：**10 passed**（真实 PostgreSQL）
- 全量 pytest（根目录 + 注入 DATABASE_URL）：**485 passed**，2 failed + 1 error 为沙箱 temp 权限（WinError 5，用户本机可写），无回归（475 → 485，+10 Step 5）
- DB 验证：重复 content_hash 组数=0、content_hash NULL=0、alembic 版本=20260821_0005

**执行计划 Step 5 完成判定对照：**
- 同内容只对应一个 Question ✅（集成测试 + DB 验证）
- 答案冲突产生可查询的审核记录 ✅（review_reason='answer_conflict' 断言）
- 全量测试通过 ✅

版本升至 4.4。

### 2026-08-21 09:30:00

#### Phase 2A Step 6 实现 + 验收 + Phase 2A 总验收通过

**Step 6：知识点映射落库**
- `KnowledgeService.map_question_to_knowledge`（新方法）：
  - 关键词匹配：seed `get_subject_index(subject_code)` 关键词索引 → node code → DB `knowledge_nodes`（rule 匹配）
  - confidence = 命中知识点数 / 总知识点数；≥0.7 → `review_status='approved'`，<0.7 → `pending`
  - knowledge_points 为空或无命中 → 回退 `{SUBJ}-UNKNOWN` 节点（查找或创建，level=1）+ `pending`（rules.md「不静默跳过」）
  - `mapping_source='rule'`（∈ llm/rule/manual）
  - 综合题子题级：子题 knowledge_points 分别映射（is_primary=False）
- `KnowledgeNodeRepository.find_by_code`（新增）
- `ingestion.py`：`_ingest_one_question` 创建 Question 后自动调用映射；映射失败不阻断入库，写 `KnowledgeMappingFailed` DomainEvent（可审计）
- 新增 `backend/tests/test_phase2a_step6_knowledge.py` 7 项（真实 PostgreSQL）
- 新增 `backend/scripts/step6_db_verify.py`：DB 验证 "函数单调性"→`MATH-ANA`（函数与导数）confidence=1.000/source=rule/review=approved

**Phase 2A 总验收（执行计划 §7）：**
- 全量 pytest（根目录 + 注入 DATABASE_URL）：**492 passed**，2 failed + 1 error 为沙箱 temp 权限（WinError 5，用户本机可写），无回归（485 → 492，+7 Step 6）
- 总验收 SQL 4/4 OK：duplicate_instance=0、null_document_id=0、null_content_hash=0、unmapped_question=0（主库无 document 来源题目数据，均为 0 符合预期；各 Step 行为已由集成测试在真实 DB 验证）
- 各 Step 验收证据：step0/2/3/4/6_db_verify.py 脚本 + 每步集成测试

**Phase 2A 六步全部验收通过：Step 0 真实回填演练 → Step 1 DSD 变更 → Step 2 审核写回 → Step 3 Worker 语义 + L2 → Step 4 答案重试关联 → Step 5 content_hash 去重 → Step 6 知识点映射。**

版本升至 4.5。

### 2026-08-21 10:00:00

#### Phase 2B 基础统计与搜索实现（P1 三任务全部完成）

按 `PLAN_QUESTION_FAMILY.md` §7.2 / `ROADMAP.md` P4B 实现，遵循 ACS §5.3-5.4 合约。

**代码变更：**
- `backend/app/domains/question/repository.py`：
  - `search()`：条件搜索（JOIN question_instances 支持 year/school、JOIN question_knowledge+knowledge_nodes 支持知识点），支持学科/年级/年份/学校/题型/知识点/难度/来源/状态过滤 + distinct 分页
  - `statistics()`：聚合查询 → total_questions / question_type_distribution / knowledge_point_distribution（高频知识点按次数降序，limit 50）/ difficulty_distribution / year_trend（基于 instances.year）
- `backend/app/domains/question/service.py`：`search` / `statistics` 透传
- `backend/app/application/services.py`：`QuestionApplicationService.search_questions` / `get_statistics`
- `backend/app/api/routes/questions.py`（新增）：`GET /api/admin/questions`（13 个筛选参数 + 分页）、`GET /api/admin/questions/{id}`、`GET /api/admin/statistics`（ACS §5.4 合约）
- `backend/app/api/dependencies.py`：`get_question_application_service`
- `backend/app/api/router.py`：注册 questions 路由

**测试：**
- `backend/tests/test_phase2b_search_stats.py`：9 项（真实 PostgreSQL）——按学科/题型/年份/学校/知识点搜索、分页、统计聚合、高频知识点降序、学科过滤
- `backend/tests/test_phase2b_api.py`：3 项（TestClient + dependency override）——搜索端点、非法 source_type 400、统计端点合约
- 修复 2 个实现 bug：fixture qno 碰撞（唯一索引）、`_error_response` 未包 JSONResponse（400 状态码丢失）

**证据：**
- Phase 2B 测试 12 项通过（2 次运行稳定）
- 全量 pytest（根目录 + 注入 DATABASE_URL）：**504 passed**，2 failed + 1 error 为沙箱 temp 权限（WinError 5，用户本机可写），无回归（492 → 504，+12 Phase 2B）
- API 冒烟：`GET /api/admin/statistics` 200（keys 符合 ACS 合约）、`GET /api/admin/questions` 200（total=0，主库无题目数据）

**Phase 2B 三任务对照（ROADMAP P4B）：**
- ✅ 知识点 × 题型 × 年份统计 API（statistics 端点）
- ✅ 条件搜索（questions 端点，学科/题型/知识点/年份/学校）
- ✅ 高频知识点排行（knowledge_point_distribution 降序）

版本升至 4.6。

### 2026-08-21 10:30:00

#### Step 0 真实 Migration Rehearsal 纳入 pytest 验收

**背景**：用户复核指出 `test_phase2a_step0_integration.py` 未执行真实 migration（只在当前 schema 插数据），`step0_db_verify.py` 在空表上验证结论为空洞结论。要求补充真实 migration rehearsal 纳入 pytest 验收。

**实现**：
- 新增 `backend/tests/test_phase2a_step0_migration_rehearsal.py`：在一次性临时数据库（`aitutors_step0_pytest`）上执行完整 migration upgrade/downgrade 演练，7 项 pytest 断言：
  1. `questions.year/school` 列已删除
  2. `document_id` 通过 `source_document_name = documents.filename` 正确回填（3/3 匹配）
  3. COALESCE 不清空已有值（Q2 保留 year=2030/school=已有学校）
  4. `document_id` NULL 计数 = 0
  5. 唯一索引存在 + 重复插入被 `UniqueViolationError` 拒绝
  6. 无重复 `(document_id, source_question_number)`
  7. downgrade 回退：year/school 恢复、document_id 移除、instance 行保留（有损标注）
- 修复 2 个环境问题：`Config("alembic.ini")` 相对路径从根目录失败 → 改用 `Path(__file__)` 定位；`monkeypatch` 替代手动 `settings.database_url` save/restore（保证异常时恢复）
- `step0_backfill_verify.py` 独立脚本保留（等价验证，但不是 pytest 形式）

**证据**：
- 迁移演练测试单独通过（1 passed，1.32s）
- 全量 pytest（根目录）：**513 passed**，2 failed + 1 error 为沙箱 temp 权限（用户本机可写），无回归
- 之前全量套件中的迁移演练失败已消除（monkeypatch + 绝对路径修复）

版本升至 4.7。

### 2026-08-21 11:00:00

#### Phase 2C Annotation 原始积累实现（PLAN §7.3 两任务全部完成）

**代码变更：**
- `backend/app/domains/document/schemas_l2.py`：L2QuestionAnnotation 新增 `structure_signature: dict | None`（Phase 2C：Structure Signature，Annotation 非事实）
- `backend/app/domains/document/line_annotator.py`：
  - `ANNOTATION_PROMPT_VERSION = "v2.1-structure-v1"`（prompt 版本号常量）
  - prompt 规则 2a 新增 structure_signature 字段说明（仅数学/物理/化学，含 object/task/method，无法判断时输出 null）
  - prompt 输出格式示例加 structure_signature
  - 解析处传入 `_normalize_structure_signature(q_data.get("structure_signature"))`
  - 新增 `_normalize_structure_signature()`（规范化：只保留 object/task/method 字符串键，非 dict/空→None）
- `backend/app/worker/document_worker.py`：
  - 提取 `_serialize_l2_for_persistence()` 独立函数（Phase 2A Step 3 + Phase 2C 完整 L2 序列化）
  - 序列化包含 `annotation_version`（文档级）+ `structure_signature`（题目级）

**测试：**
- 新增 `backend/tests/test_phase2c_annotation.py`：12 项
  - prompt 包含 structure_signature 字段说明
  - LLM 输出 structure_signature → 正确解析
  - LLM 未输出 → None（不编造）
  - 规范化：非 dict→None、空值→None、部分键保留
  - worker 序列化包含 annotation_version + structure_signature

**证据：**
- Phase 2C 测试 12 项通过
- 全量 pytest（根目录）：**513 passed**，2 failed + 1 error 为沙箱 temp 权限，无回归

**Phase 2C 两任务对照（PLAN §7.3）：**
- ✅ Structure Signature 采集（prompt 可选字段，仅数学/物理/化学，存 llm_annotated_markdown JSON）
- ✅ Annotation 版本标记（ANNOTATION_PROMPT_VERSION 写入 llm_annotated_markdown）

版本升至 4.8。

### 2026-08-21 11:30:00

#### 对抗性审查缺口修复

按审查结论修复 3 处缺口：
- **Step 2**：`test_review_end_to_end_writes_db` 增加 `task.result_json` 同步断言（commit 后新连接 SELECT 验证 review_decisions + review_overrides 真实落库）。执行计划要求「断言 DB 中 questions 表字段真实变化，不是只断言 task.result_json」——现已同时验证两者。
- **Step 3**：新增 `test_ingestion_exception_persists_task_and_document_status`（真实 DB 验证 ingestion 异常后 `background_tasks.status='failed'` + `documents.processing_status='failed'` 落库）+ `test_llm_annotated_markdown_persists_l2_fields`（真实 DB 验证 `documents.llm_annotated_markdown` 包含 knowledge_points/difficulty/score/corrected_anchors/anchor_status/question_type/sub_questions）。
- **Step 6**：审查确认 `_make_math_subject` 使用真实 MATH subject + `subject_code="MATH"`（复用 seed 脚本已入库的 333 节点），非测试专用 subject。无缺口。

全量 pytest：**515 passed**，2 failed + 1 error 仅沙箱 temp 权限，无回归（513 → 515，+2 真实 DB 验证）。

### 2026-08-21 12:00:00

#### 对抗性审查第三轮：真实 Bug 修复（FK 依赖遗漏）

`_cleanup_unreviewed_records` 未删除 `question_images`/`question_knowledge`/`question_embeddings` 的 FK 依赖记录，重跑有配图或知识点映射的文档时触发 `ForeignKeyViolationError`。

修复：cleanup 先按 question_id 删除 QuestionImage/QuestionKnowledge/QuestionEmbedding 记录，再删 instance，最后删 question。新增 `test_rerun_cleanup_handles_fk_dependents` 验证 FK 依赖清理（questions 有 images + knowledge 时 cleanup 不报错，全部清理干净）。

全量 pytest：**516 passed**，2 failed + 1 error 仅沙箱 temp 权限，无回归（515 → 516，+1 FK 依赖测试）。

### 2026-08-22 00:39:59

#### 全量回归确认 + 收集错误修复 + 测试不同步修复 + temp 权限根治

本次会话执行全量 pytest 回归确认，发现并修复 4 类问题，最终全量 **549 passed，0 failed，9 warnings**（用户本机注入 `backend/.env` DATABASE_URL 验证）：

1. **🔴 收集错误（2 ERROR）修复：`run_pipeline` 恢复**。工作树 8-21 23:24 重构删除了 `pipeline.py` 的 `async def run_pipeline`，但 4 个引用方未同步（`test_pipeline.py`、`test_pipeline_empty_sources.py`、`test_validation_harness.py` 经 `run_phase1_eval.py`、`test/scripts/run_phase1_eval.py`），全量 pytest 收集阶段中断。修复：从 HEAD 移植 `run_pipeline` 到 `pipeline.py`（约 190 行）+ 补 Fix 1 空源语义（双源全空 → `status="failed"` + `stage_errors` 记 `l1_generation`）。`simple_pipeline.py` docstring 约定 "pipeline.py 保持不变，作为 fallback"，恢复符合设计意图。
2. **🔴 测试与生产代码不同步（4 项）**：processor 已迁移 `run_simple_pipeline`（8-21 22:59）但测试仍 patch 旧入口——`test_phase2_critical_fixes.py` 3 处 `patch("processor.run_pipeline")` → `run_simple_pipeline`；`test_processor_progress.py` patch 目标从 `pipeline` 模块改为 `simple_pipeline` 模块 + 补 `extract_l1_from_ocr` patch。
3. **🟡 DB 历史数据清理**：`test_phase2b_search_stats` 2 项失败（`12 vs 3`）根因为真实库残留 9 道历史题（8 approved + 1 rejected，英语期末卷），无过滤统计 = 9 + 3 fixture；测试假设干净库（事务回滚无法遮蔽事务前已提交数据）。按用户决定删除历史题（question_knowledge/question_instances/questions 按 FK 顺序清理，documents/background_tasks 保留），stats 测试恢复 19 passed。
4. **🟡 沙箱 temp 权限根治（Codex 并行完成）**：`backend/tests/conftest.py` 将 `--basetemp`/`tempfile.tempdir`/`TEMP`/`TMP`/`TMPDIR` 固定到工作区 `D:\Project\AITutors-v2\tmp\pytest`；`processor._download_pdf()` 临时目录改工作区 `tmp`；新增 `test_temp_root.py`；`.gitignore` 加 `tmp/`。消除 `C:\Users\...\Temp\dsh-*` WinError 5 间歇失败。

- 全量 pytest（用户本机）：**549 passed，0 failed，9 warnings**（546 → 549，+3 temp 根测试；收集错误与 temp 权限间歇失败均已消除）。
- 版本升至 5.3。

### 2026-08-22 22:31:39

#### VL 模型选择更新

- 管线 VL 首选 MIMO V2.5（`mimo-v2.5`），回退 DeepSeek Vision（`deepseek-v4-flash-vision-exp`），移除 Qwen VL。
- `build_gateway` 与 `build_ocr_chain` 的 VL provider 顺序均为 `mimo-vl` → `deepseek-vl`。
- 相关测试 39 passed；未跑全量 pytest。

### 2026-08-24 23:00:00

#### 答案验证器独立化 + 9 科答案基线建立

**背景**：9 科 e2e 语义验收基准报告完成（严格通过率 44%），但答案验证部分存在假阳性问题（短答案直接匹配导致 76% 通过率不可信）。用户要求以原始 PDF 为主判据，建立可信的答案基线。

**答案验证器 (`test/scripts/answer_verifier.py`)**：
- 新建独立模块，从 e2e_semantic_report.py 分离答案验证逻辑
- 四层独立证据对比：pdf_raw_text（主判据）→ native_markdown（交叉验证）→ ocr_markdown（辅助证据）→ DB
- 5 种证据模式：table_mode、prefix_mode、inline_mode、free_text_mode、composite_mode
- 验证状态：matched / mismatched / unverifiable（带原因分类）
- unverifiable 原因：free_text_answer、missing_db_question、composite_subquestion

**P0-A composite 材料合并修复**：
- 修复 `content_slicer._slice_single_question`：composite 题合并 `shared_material_line_ids` + `stem_line_ids`，材料行在前，去重
- 17/17 测试通过
- 需重跑英语入库验证

**物理空单元格列错位修复**：
- 答案表有空单元格时（如物理 Q4/Q7），解析器忽略空格导致列错位
- 修复：答案验证器保留空单元格，不忽略空白答案格
- 验证：物理 Q5/Q6/Q8 不再误报为 mismatch

**9 科答案基线**：
- matched: 162/198
- mismatched: 2/198（生物 Q6, Q7 — 真实答案错误）
- unverifiable: 14/198
- 严格通过: 156/209 (75%)

**测试**：
- `test/scripts/test_answer_verifier.py`：4 项通过
- `backend/tests/test_composite_material_separate.py`：17 项通过

**版本升至 6.8。**

### 2026-08-24 23:30:00

#### 文档治理规则补充

- 状态类文档更新必须按时间戳顺序在文末追加，禁止直接在文档头更新。
- 本次同步更新 `rules.md`、`RESTART_PROMPT.md`、`bugs.md` 和本文档。

### 2026-08-24 23:45:00

#### Docs 规划文档精简

- `Docs/ARCHIVE/` 移至根目录 `docs_archive/`。
- 归档完成后的执行计划、实验管线、表选项提取、试卷结构门禁原文档。
- 关键内容整合进 `TASK.md`、`PIPELINE.md`；规划文档内变更记录统一迁移到 `LOG.md`。

### 2026-08-24 23:55:00

#### 文档更新映射规则补充

- `rules.md` 新增日常文档更新映射表。
- `Docs/` 禁止创建状态类/执行记录类/审查报告类/临时方案类文档，新增 `Docs` 文档必须经用户确认。

### 2026-08-25 02:30:00

#### 英语 stem 位置/选项归属修复完成（版本 6.11）

- **PPS/PVL 队列满载解决**：paddle 提交 HTTP 200 + jobId 返回；英语重跑 PP-StructureV3 OCR 2.8s 直接成功，10010 熔断不再触发。后端已用新代码重启，依赖健康检查全 ok。
- **英语位置 7/11 → 11/11**：修复 `semantic_anchor.resolve_stem_range`（综合题 short_answer 信任 end_marker，min(end_marker, next_q-1)）与 `_truncate_stem_at_next_question`（文档顺序 + 题号过滤混合边界，解决 OCR 噪声题号 "48、49" 把 Q46 截空）。
- **选项归属 7/11 → 11/11**：验证脚本假阳性（多行选项拼接文本在 section 中不连续），改为 L2 options_line_ids 行号区间判断；DB 选项数据本身正确。
- **Q46 作文缺库解决**：DB 11/11（此前 10/11），作文 prompt 完整入库。
- **验收（真实重跑）**：stem/位置/材料/选项 11/11，严格通过 10/11 (91%)（此前 3/11）。剩余 Q46 答案 free_text_answer 不可验证（作文自由文本固有边界）。
- 全量 pytest 629 passed，剩余失败均为沙箱 temp ACL 与 DB 数据前置，无回归。

**当前状态**：
- 9 科答案基线 mismatch=0、严格通过率 76%（英语重跑后需按新口径复算）
- 英语：位置/选项 11/11、严格 10/11
- **下一步**：T0-4 provider_used 落盘 → T0-5 Phase 2D 前置评估 → 英语答案 free_text 验证改进（可选）→ 轮换泄露 API key（待用户操作）

### 2026-08-25 03:30:00

#### provider_used 落盘完成 + Phase 2D 前置评估（版本 6.12）

- **T0-4 provider_used 落盘**：`PipelineResult` 新增 `ocr_provider_used`/`ocr_model_used`，写入 task result（background_tasks.result_json）。实时验证：英语重跑 `ocr_provider_used=paddleocr`、`ocr_model_used=PP-StructureV3`，11/11 入库稳定。
- **T0-5 Phase 2D 前置评估**：样本 191 题（数学 5、语文 7 过少）、golden 仅 3 科、Structure Signature 覆盖率 20%（限数学/物理/化学）——**前置条件未满足，暂不启动**。
- 英语最终验收稳定：位置/选项/stem/材料 11/11，DB 11/11，严格 10/11 (91%)。

**当前状态**：
- 英语：位置/选项 11/11、严格 10/11（91%）；T0 剩余项：轮换泄露 API key（待用户操作）
- Phase 2D：前置条件未满足（样本量/golden/签名覆盖率），待积累
- **下一步**：英语答案 free_text 验证改进（可选）→ 扩充样本 + 补齐 9 科 Structure Signature → Phase 2D
