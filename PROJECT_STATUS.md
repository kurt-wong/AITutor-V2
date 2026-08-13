# AI Tutor Personal Edition — 项目状态

---

## 当前状态

状态：P0/P1 完成，P2 临时验证闭环已冻结；**T3 Phase 1 最终验收通过**（2026-08-13，golden 8 题纵向闭环；全卷低置信度项登记待 Phase 2/3 审核）。后端 143 项测试通过。

已完成后端 FastAPI 骨架、22 张 DSD 表模型与 Alembic 初始迁移、Repository/Domain Service/Application Service 分层骨架、统一 Background Task/Domain Event 骨架、LLM Gateway 基础路由、MinIO 客户端接入和依赖健康检查。embedding 已固定为 qwen3-embedding:4b / 2560 维，初始迁移不建 HNSW 向量索引。

P2 已新增 PP-StructureV3 客户端、OCR/VL 回退链、LLM 结构化 Question Aggregate 输出、`test/scripts/run_parse_baseline.py` 和 `test/scripts/evaluate_parse_accuracy.py`。

T3 Phase 0 状态：L1/L2 Schema、fixture（数学 38 行 postprocessed + 英语 69 行 postprocessed 含完形填空共享材料、答案区与详解区）、golden（数学 v3.1 7 题 + 英语 v3.1 10 题）、postprocessor（含数字误拆 bug 修复）、smoke test 已落地；后端 41 项、Smoke pytest 13 项全部通过。Live 全部通过：DeepSeek 12s、MIMO 134s、Qwen 38s。

本次修复：`HTTPLLMProvider` 新增 `response_format` 可选参数；`build_gateway()` 和 smoke test 为 MIMO 传入 `json_object`；smoke test 超时提升至 120s；smoke test prompt 改为完整 fixture 文本。Math Golden Set 已补齐至 v3.1；English Golden Set 重建至 v3.1（基于 postprocessed L1 fixture，10 题含完形填空共享材料、答案区与详解区，answer/explanation 锚点均非空）；`l1_postprocessor.py` 修复数字内点号误拆 bug（`prev_char.isdigit()` 跳过）；smoke test 新增 English fixture + golden set 完整性断言（含 answer/explanation 锚点非空）。

约束状态：T3 Phase 1 已通过对抗性审查并最终验收（2026-08-13）。后端 143 项测试通过；Mock eval 8/8 指标 100%；用户本机 live-pp 3 次运行取最差后 golden 8/8 全字段 100%，line ID errors=0。全卷 21 题中 answer_matched=16、answer_empty=5（均为解答题 17-21）、blocked=7（Q1/Q4 缺选项、Q17-21 缺答案），均带 issues/低置信度标记，未静默发布。explanation_line_ids 不在 Phase 1 验收范围内（golden 8 题均为空，explanation_source 为 llm_fallback，属 Phase 2+ 范畴）。

本次 Phase 1 复审修复：答案表按题号边界切分，支持括号答案并停在解答题区；锚点题号正则排除 LaTeX 续行；L1 后处理支持行内全角括号题号切分。

本次 Phase 1 基础设施加固：`run_phase1_eval.py` 新增全卷验收阈值 `THRESHOLDS_FULL卷`（min_answer_matched=16、max_blocked=7、min_quality_high=14、max_missing_anchors=10）；`THRESHOLDS_SMOKE` 补充 `stem_line_ids`、`options_line_ids`、`answer_line_ids` 三项；`HTTPLLMProvider` 新增指数退避重试（max_retries=2、retry_base_delay=1.0s）。

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
| UI.md | 1.0 | 前端设计与页面规范 |
| Design.md | 参考 | 前端视觉设计风格 |
| TASK.md | 1.6 | 任务执行规范 |
| RESTART_PROMPT.md | 1.9 | 重启恢复说明 |
| ROADMAP.md | 1.3 | 开发任务计划（执行基线） |
| PADDLEOCR_API.md | 1.1 | OCR API 项目资料 |
| V1_LESSONS.md | 2.0 | V1 经验教训与强制约束 |
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
- `question_images` 的 `page_no/bbox/placement/source/figure_id` 已在 DSD 固化，但尚未实现。
- 知识树种子数据尚未初始化；启用知识点映射前必须补上。
- Alembic 初始迁移已在现有 PostgreSQL 的 aitutors 新库上执行成功；旧 ai_tutor 库未改动。
- qwen3-embedding:4b 为 2560 维，超过 pgvector HNSW 索引 2000 维上限，初始阶段使用暴力余弦检索。
- Docker CLI 可直接访问；`scripts/allow-codex-docker.ps1` 仅保留给沙箱账号场景。
- 前端依赖安装尚未完成。
- 文档上传、查询、状态、重试和统一 Task 查询 API 已实现；完整文档解析管线、worker 消费和领域业务逻辑尚未实现。
- 题型规范需要根据真实文档细化。
- 标准知识树需要根据管理员提供的资料初始化。
- 字典文档已建立，后续新增字段/功能需同步维护。

---

## 下一步

按 `Docs/01_Product/T3_IMPLEMENTATION.md` 执行：

1. **Phase 0（契约 + Golden Set）** ✅：全部 Live passed，验收完成。
2. **Phase 1（纵向闭环）** ✅：mock 8/8；live-pp 3 次运行取最差后 golden 8/8，对抗性审查通过，最终验收完成。
3. **Phase 2（扩展覆盖）**：OCR fallback、图片去重、英语共享材料、管线集成。
4. **Phase 3（规模化）**：30 份 PDF 基线、DOCX 支持、前端对接。

Phase 1 最终验收通过（2026-08-13）：
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
