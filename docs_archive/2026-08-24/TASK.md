# AI Tutor Personal Edition — 任务执行规范

Version: 1.6
Status: 开发指引基线
Date: 2026-08-11

---

## 1. 任务原则

- 单任务制：同一时间只推进一个任务。
- 每任务建议不超过 4 小时，必须产出可运行结果。
- 禁止 big-bang 式交付。
- 文档优先，代码修改必须遵循项目文档。
- 动文档解析管线前必须阅读 `Docs/05_Development/V1_LESSONS.md`，并按其中 P0 约束执行。
- 开发任务计划以 `Docs/01_Product/ROADMAP.md` 为准。

---

## 2. 开发顺序

新功能按以下顺序推进：

1. 先确认需求边界。
2. 定义或复核 Question Aggregate，并同步更新 `DICTIONARY.md`。
3. 在 DSD.md 定义数据模型，包括统一 Task 和 Domain Event。
4. 在 ACS.md 定义 API 合约。
5. 实现 Domain Service 和 Repository。
6. 实现 Application Service。
7. 接入 AI Gateway。
8. 实现 API。
9. 实现前端页面。
10. 只有 Agent 需要调用时，才在 MIS.md 定义并实现 MCP Tool。
11. 更新测试、日志和项目状态。

---

## 3. 完成标准

一个任务完成必须满足：

- 功能按文档实现。
- API 返回符合 ACS。
- 数据写入符合 DSD。
- 高置信度路径和低置信度审核路径都有覆盖。
- 异步能力复用统一 Background Task，不另起状态表。
- 业务状态变化发布 Domain Event。
- 文档解析结果必须可追溯：LLM 只输出行号/元数据，内容由代码从 L1 原文切片。
- 文档解析的 LLM 行号必须经过代码锚点校正，并保存 `llm_anchor/corrected_anchor/anchor_status`。
- 配图必须携带 `page_no/bbox/placement/source`，无位置不自动关联。
- 元数据来源优先级明确：文件名/上传表单优先，LLM 只填空或高置信度覆盖。
- 表结构变更必须同步 Alembic migration。
- live LLM/OCR 测试必须与常规 pytest 隔离。
- 新字段、新功能、新状态枚举同步维护到 `DICTIONARY.md`。
- 修改生产代码后更新对应测试。
- 重要变更按记录规范在 `LOG.md` 文末追加完整时间戳记录。
- 项目状态更新到 `PROJECT_STATUS.md`，并在文末“更新记录”追加完整时间戳。

---

## 4. 禁止事项

- 不绕过 Application Service / Domain Service。
- Agent 不得绕过 MCP Tool 直接调用业务能力。
- 不直接调用 LLM SDK。
- 不直接在 API 层访问数据库。
- 不为同类后台任务重复建立不同 status 表。
- 不把 prompt 或 CoT 写入数据库。
- 文档解析不允许把 LLM 抄写的题干/选项/答案/解析 JSON 作为正式内容源。
- 不允许把未经锚点校正的 LLM 行号直接作为最终切片边界。
- 不允许无 page/bbox 时猜图关联或使用整页兜底。
- 不允许绕过 Alembic 直接改表结构。
- 不允许常规 pytest 默认套件真实调用外部 LLM/OCR。
- 不在项目文件夹外创建文件。
- 不把 API Key 硬编码到代码或文档。
- 不在 `test/` 外存放测试数据、测试脚本和测试结果。

---

## 5. 测试目录约定

- 所有测试相关数据和测试资产统一放在根目录 `test/`，禁止放在代码、文档或其他目录。
- 原始样本按类型分目录，例如 `test/pdf/`、`test/docx/`、`test/jpg/`。
- 测试脚本、配置和结果报告放入 `test/scripts/` 等 `test/` 下子目录。
- 后端单元测试继续使用 `backend/tests/`；真实文档样本、准确率统计和解析验证测试归 `test/`。

---

## 6. V1 教训强制约束

详见 `Docs/05_Development/V1_LESSONS.md`。核心红线：

1. Annotation Paradigm：LLM 输出行号范围，代码切原文。
2. LLM 行号是粗定位；代码必须做锚点校正，不能直接切片。
3. L1 双源证据路由：PyMuPDF native 与 PP-StructureV3 并存，canonical L1 按行选择。
4. 图片去重文档级，bbox 使用 IoU/中心距离，不做精确匹配。
5. 教师版答案/详解优先，LLM 生成只兜底且必须标记来源。
6. 知识树为空时不得静默跳过映射。
7. Schema 变更必须有 migration。
8. 验证前清理旧进程，不使用 `--reload`。
9. live 测试单独运行，不污染默认 pytest。
10. 复合题必须 section 级切分；quality gate 失败部分保存并标记低置信度。

### 2026-08-11 23:49:10

- 更新 L1 来源约束：PyMuPDF 不再作为整份正文 L1 基座。
