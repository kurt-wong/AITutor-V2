# AI Tutor 项目级规则

> **本文件只承载规则与约束，不承载任何项目状态。**
> 进度、已知问题、完成度、工具清单、配置现值等一律写入对应权威文档（见下方导航表）。
>
> 冲突优先级：** REQUIREMENTS_AND_SOLUTION.md > MIS.md > ACS.md > SAD.md > PRD.md > DSD.md > 本文件 > 全局规则**


---

## 查什么去哪（导航）

| 要查的内容 | 权威文档 |
|---|---|
| 真实需求 / 方案基线 | `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md` |
| 字段 / 功能 / 状态字典 | `Docs/00_Requirements/DICTIONARY.md` |
| 项目定位 / 技术栈 / 当前状态 / 完成度 | `PROJECT_STATUS.md` |
| 已知问题 / Bug 跟踪 | `bugs.md` |
| 变更历史 | `LOG.md` |
| 文档解析管线（PP-StructureV3 API、阶段定义、回退链） | `Docs/02_Architecture/PIPELINE.md` |
| V1 经验教训 / 强制约束 | `Docs/05_Development/V1_LESSONS.md` |
| 开发任务计划（严格执行基线） | `Docs/01_Product/ROADMAP.md` |
| PaddleOCR-VL / PP-StructureV3 API 资料 | `Docs/02_Architecture/PADDLEOCR_API.md` |
| MCP Server 与工具权威表 | `Docs/02_Architecture/MIS.md` §3 |
| API 合约 | `Docs/02_Architecture/ACS.md` |
| 系统架构 / DDD 限界上下文 / 模型路由 | `Docs/02_Architecture/SAD.md` |
| 数据库结构 | `Docs/03_Data/DSD.md` |
| 产品需求 | `Docs/01_Product/PRD.md` |
| 任务执行规则 | `Docs/01_Product/TASK.md` |
| 前端页面规范 | `Docs/02_Architecture/UI.md` |
| 前端视觉风格 | `Docs/Design.md` |
| 重启恢复 / 项目目标 / 系统现状 / 待办任务 | `RESTART_PROMPT.md` |

---

## 架构核心规则（不可违反）

```
UI → API → Application Service → Domain Service → Repository → DB
AI Gateway → LLM Provider
Agent → MCP Tool → Application Service
```

1. **唯一调用链**: API → Application Service → Domain Service → Repository → Database
2. **Agent 只能通过 MCP Tool 调用 Application Service**（MCP 是 Agent Interface Layer，不是业务主链路；工具清单以 MIS.md §3 为准）
3. **前端不可直接访问数据库**
4. **数据库不存储 COT（思维链）**（只存最终答案、教学步骤、元数据）
5. **知识树不可自动扩展**（人工维护；映射失败回退 `{SUBJ}-UNKNOWN` 父节点）

**禁止路径**：UI→DB ❌ · API→DB ❌ · Agent→DB ❌ · Agent→LLM ❌ · Service→LLM SDK ❌ · MCP 绕过 Application Service 直连 SQL ❌

**MCP 治理**：
- MCP 只用于 Agent 接口层，不强制用于正常业务主链路
- 工具必须无状态、单一职责，命名以 MIS.md §3 为准
- 同一 Server 内工具不得互调；跨 Server 组合只能由 Application Service 编排
- Agent 能力开发次序：Application Service → API → 可选 MCP Tool

### 设计原则：LLM 能力最大化（不可违反）

**每个环节都必须尽可能充分发挥 LLM 的最大能力。**
本项目以题目（question）为驱动核心，LLM 是唯一具备语义理解能力的环节。
凡是 LLM 能做的事，不应交由正则、关键词匹配或人工规则代劳。

具体而言：
- **让 LLM 输出完整语义，而非只输出坐标**：LLM 理解试卷结构后，应同时输出每个
  section 的元数据（题型、题号范围、是否综合题、材料是否共享等），下游代码直接
  消费元数据，零猜测、零规则。
- **LLM 负责判断，代码负责执行**：判断"这些题是否依附同一篇材料"是 LLM 的事，
  按判断结果合并是代码的事。不要反过来——不要代码猜完再让 LLM 补救。
- **正则仅用于机械操作**：切分行号、提取纯数字 QNO 等纯文本操作可以用正则。
  判断语义（"这是完形填空吗？""这道题属于哪个 section？"）必须交给 LLM。
- **Prompt 能解决的不写代码规则**：遇到 corner case，优先增强 prompt 而非添加
  if/else。规则是死的，prompt 是活的。

---

## V1 教训固化（不可违反）

本规则来源见 `Docs/05_Development/V1_LESSONS.md`。以下约束在 V2 中直接生效：

1. **文档解析的 LLM 只输出标注/行号/元数据，不输出题干原文**。内容由代码从原始 Markdown 或 Native 文本切片。
2. **PDF 采用 Native/PP 双源 L1 证据路由**；PyMuPDF 只做页面/图片/答案表/上下标辅助，PP-StructureV3 负责公式与复杂版面，canonical L1 按行选择并保留 provenance。
3. **配图必须携带 page/bbox/placement/source**；禁止无位置猜图、整页兜底、跨题广播。
4. **教师版答案/详解优先**，LLM 推理只做缺失项兜底，并保留来源标记。
5. **元数据以上传/文件名解析来源优先**，LLM 只填空或高置信度覆盖，禁止 `None` 写成字符串。
6. **启用知识点映射前必须初始化知识树**；知识树为空时不得静默跳过映射。
7. **任何表结构变更必须有 Alembic migration**，禁止只改模型或只改数据库。
8. **常规 pytest 必须 mock**，live LLM/OCR 验证单独隔离，禁止混入默认套件。
9. **解析/worker 验证前必须清理旧进程和 `__pycache__`**，禁止用 `--reload` 做验证。
10. **错误不能静默吞掉**；失败、低置信度、来源缺失必须记录结构化原因并进入可审计状态。
11. **OCR 识别链（用户决策 2026-08-25，见 `OCR_PROVIDER_POLICY.md`）**：
    - L1 识别仅使用 paddle 系（PP-StructureV3 / PaddleOCR-VL，学科路由）；
      native-markdown 只做同页同行证据 + PP 空行兜底。
    - **LLM VL（mimo-vl / deepseek-vl）禁止作为 L1 识别工具或入库驱动**；
      仅保留为可选交叉验证入口（默认关闭）。
    - paddle 不可用（401/10010/网络错误）：重试/熔断耗尽后任务失败并标记
      `ocr_unavailable`，等待 paddle 恢复后重跑；**禁止自动降级 LLM VL 驱动入库**。
    - 动 OCR 链前必读 `OCR_PROVIDER_POLICY.md` 与 `ocr/paddle_client.py`。

---

## 关键约定

### 代码风格

- Python: snake_case，类型注解，async/await
- 测试: `test_<module>.py`，`TestXxx` 类，`test_<行为>` 方法
- 日志: `from app.core.logging import get_logger` → `logger.info()`

### 测试数据与脚本

- 所有测试相关数据（PDF/DOCX/JPG、样本、标注结果等）统一放在根目录 `test/` 下，禁止散落在代码、文档或其他目录。
- 原始测试样本按类型放入子目录，例如 `test/pdf/`、`test/docx/`、`test/jpg/`。
- 测试脚本、配置和结果报告统一放入 `test/` 下对应子目录，例如 `test/scripts/`。
- 后端单元测试仍按 pytest 惯例放在 `backend/tests/`；涉及真实文档样本、准确率统计和解析验证的测试资产归 `test/`。

### LLM Gateway

- 模式: `live`（生产）/ `mock`（测试）
- Provider 链: primary → cloud → Ollama（三级回退）
- 模型路由表以 SAD.md §5 为准；所有 AI 功能必须可经 Gateway 路由，禁止绕过

### .env 约定

- 密钥/Token 一律走 `.env`，禁止硬编码（含 docker-compose 的 `${VAR:-默认值}` 形式）
- 生产模式硬性要求：`LLM_GATEWAY_MODE=live`、`OCR_MOCK_MODE=false`、`EMBEDDING_MOCK_MODE=false`；`PADDLEOCR_VL_TOKEN` 与 `ADMIN_API_KEY` 必须设置（缺失时服务拒绝启动）
- 可调策略键（`VL_PRIMARY`、`PADDLEOCR_VL_LAYOUT_MODE` 等）的当前值查 `backend/.env`，不要抄写进任何文档
- 新增配置键必须同步维护 `backend/.env.example`

### 错误处理与日志红线

- MCP 失败：最多重试 2 次 → LLM 场景回退次级 Provider → 返回 ACS 结构化错误（`error.code` + `error.message`）
- 每个请求必须携带 request_id，记录延迟与所用 MCP 工具/LLM 成本
- 日志禁止记录：prompt 全文、原始 LLM 输出、用户完整文档文本

### 依赖约束

- 存储栈仅允许：PostgreSQL + pgvector + Redis + MinIO（Qdrant 永久禁用）
- 禁止绕过 Gateway 直连模型 SDK（OpenAI / DeepSeek / MIMO SDK 直调 ❌）

---

## 开发流程规则

- 单任务制：同一时间只推进一个任务；每任务 ≤ 4h、产出可运行结果；禁止 big-bang 式交付
- **先讲明白再动手（不可违反）**：遇到以下任一情况，必须先停下，用大白话向用户讲清楚「问题根因是什么、我打算怎么改、改动的范围和影响是什么」，**获得用户明确确认后**才能动手写代码：
  1. 同一问题反复修改 2 次及以上仍未解决；
  2. 涉及较大范围的代码级调整（跨模块、改契约、改数据流）；
  3. 涉及架构级调整或技术方案/技术选型变更；
  4. 需要新增或回退较多后端逻辑来"补"某个输入/数据质量问题。
  - 禁止在未确认前连续多轮闷头改代码、逐层加补丁；发现问题根源在**上游输入质量**（如 OCR、源文件）时，优先解决源头或标注隔离，而不是用代码兜底。
- **文档优先（不可违反）**：所有代码修改必须严格遵循项目文档设定，不能擅自越过项目文档。如确有偏离必要，必须先充分沟通、明确告知影响并得到确认后再实施；实施后同步回写权威文档。
- 开发期冲突处理：文档与可运行代码冲突时，先停下核对权威文档；若文档确实过时，先沟通确认，再改代码并回写文档。Phase 冻结后一律以文档为准。
- 拿不准时：选更简单方案、沿用现有架构、优先 Tool 而非 Agent、存事实不存推理、不动架构
- 个人系统优先最简实现：复用现有后端分层与统一 Task 契约；不复制 V1 巨型管线，不做通用 LaTeX 解析器。

---

## 记录规范（不可违反）

适用于 `LOG.md` 和 `PROJECT_STATUS.md`，其他需要持续恢复上下文的文档建议同样遵守。

1. 新增内容必须包含完整时间戳，格式为 `YYYY-MM-DD HH:mm:ss`。
2. 新增内容按时间顺序追加到文件末尾，禁止在文件头部随意新增。
3. 禁止覆盖或删除历史记录；如需修正，追加一条新的修正记录。
4. `LOG.md` 每次重要变更追加一条记录。
5. `PROJECT_STATUS.md`、`RESTART_PROMPT.md`、`bugs.md` 等状态类文档必须按时间戳顺序在文末追加更新记录，禁止直接在文档头更新；如维护头部快照，则头部只保留最新快照，且每次头部变化必须先在文末追加完整时间戳条目。
6. `RESTART_PROMPT.md` 用于 Codex/Claude 重启恢复；项目目标、系统现状、待办任务变化后必须同步更新，并在文末追加时间戳记录。
7. 出现新字段、新功能或新状态枚举时，必须同步维护 `Docs/00_Requirements/DICTIONARY.md`，并在文末“更新记录”追加完整时间戳。

日常更新必须写入对应文档，不得新建替代文档：

| 更新类型 | 对应文档 |
|---|---|
| 日常代码更新、修复、测试、变更历史 | 根目录 `LOG.md` |
| 项目当前状态、阶段、下一步任务 | 根目录 `PROJECT_STATUS.md` |
| Codex/Claude 重启后恢复上下文 | 根目录 `RESTART_PROMPT.md` |
| 开发过程中发现的 Bug / 修复记录 | 根目录 `bugs.md` |
| 规划、设计、需求、架构、API、数据、UI 契约 | `Docs/` 下对应规划类权威文档 |

禁止事项：

- 禁止在 `Docs/` 下创建任何状态类、执行记录类、审查报告类、临时方案类文档。
- 未经用户确认，禁止在 `Docs/` 下新增任何文档。
- 确需新增 `Docs` 文档时，必须先向用户说明用途、目录和对应权威文档，得到用户确认后才能创建。

---

## 工作指令

0. **【死命令】禁止在项目文件夹外创建任何文件** — 所有产出物（代码、文档、测试、临时文件等）必须严格限定在 `D:\Project\AITutors-v2` 根目录范围内。禁止向桌面、用户目录、系统临时目录等任何项目外路径写入文件。违反此规则将污染用户文件系统。
1. **先读代码再回答** — 文档可能过时，代码是唯一事实源
2. **修改前先理解** — 读取目标文件和相关调用方，理解上下文
3. **保持架构合规** — 新代码必须走 Service → Repository → Database 路径
4. **测试同步** — 修改了生产代码就更新对应测试
5. **记录同步** — 重要变更按“记录规范”在 `LOG.md` 文末追加；项目状态变化更新 `PROJECT_STATUS.md` 并在文末追加时间戳，不要写进本文件
6. **不要过度工程** — 只做被要求的事
7. **Windows 环境** — 路径用反斜杠，PowerShell 语法，Python 3.12
8. **动文档解析管线前必读** `PIPELINE.md`、`Docs/05_Development/V1_LESSONS.md` 与 `backend/app/domains/document/ocr/paddle_client.py`
9. **文档优先 / 偏离需沟通** — 代码修改默认严格遵循权威文档；确需偏离时必须先充分沟通、告知影响，得到确认后再改代码

---

## 文档治理

- **`Docs/` 只允许存放项目规划、设计、契约类权威文档。**
- 禁止在 `Docs/` 下随意新增执行记录、审查报告、临时方案、验收报告、修复计划等文档。
- 日常代码更新和修复记录写入 `LOG.md`；当前状态写入 `PROJECT_STATUS.md`；Bug 写入根目录 `bugs.md`；重启恢复上下文写入 `RESTART_PROMPT.md`。
- 若确需在 `Docs/` 新增文档，必须先经用户审核同意，且只能写入对应规划类目录。
- 技术细节（工具名/类名/端点/表结构）写入文档前，先运行 `backend/scripts/validate_docs_vs_code.py` 验证与代码一致（退出码 0）
- 代码变更必须同步对应权威文档；「目标架构」与「已实现」必须显式标注，不得混写
- 版本号规则：工具增删 → MINOR++；架构重大变更 → MAJOR++；错字/格式 → PATCH
- 大规模文档修正前，先备份到 `docs_archive/<YYYY-MM-DD>/`
- 变更完成后更新对应文档 CHANGE LOG 与 `LOG.md`

---

## 本文件维护规则

- 只允许写入：规则、约束、约定、导航指针
- 禁止写入：进度、状态、已知问题、统计数字、配置现值、API/工具/数据表清单
- 发现状态类内容混入本文件时，应将其移至 `PROJECT_STATUS.md` 或对应权威文档，而非就地更新

---

## 文档治理快照模式（v6.21，优先）

以下规则优先于上方「记录规范」中涉及 `PROJECT_STATUS.md` 与
`RESTART_PROMPT.md` 历史堆积的旧条款。

1. `LOG.md` 是唯一完整变更历史；每次重要变更在文末追加一条记录，格式为
   `YYYY-MM-DD HH:mm:ss`，禁止覆盖或删除历史。
2. `PROJECT_STATUS.md` 只保留最新状态；更新时直接在正文维护，不在文末堆积历史。
3. `RESTART_PROMPT.md` 只保留稳定上下文：项目目标、基础架构、强制规则、
   文档地图、恢复流程；不承载状态数字和历史记录。
4. 版本升级或里程碑验收前，先运行
   `python scripts/archive_status_snapshot.py --version <VERSION>`，
   把旧版 `PROJECT_STATUS.md` 和 `RESTART_PROMPT.md` 快照到
   `docs_archive/status/`；同版本小修改不强制快照。
5. `bugs.md` 仍按文末追加维护；覆盖或删除历史前，必须先保留原内容到归档目录。
6. 出现新字段、新功能或新状态枚举时，必须同步维护
   `Docs/00_Requirements/DICTIONARY.md`，并在其更新记录追加完整时间戳。
7. 禁止用新文件替代 `LOG.md`、`PROJECT_STATUS.md`、`RESTART_PROMPT.md`
   的状态职责；`docs_archive/status/` 只做快照，不做工作文件。

| 更新类型 | 对应文档 |
|---|---|
| 代码/修复/测试/变更历史 | `LOG.md` |
| 当前状态与下一步 | `PROJECT_STATUS.md` |
| 重启恢复稳定上下文 | `RESTART_PROMPT.md` |
| Bug / 修复记录 | `bugs.md` |
| 版本化状态快照 | `docs_archive/status/` |
| 规划/设计/API/数据/UI 契约 | `Docs/` 下对应权威文档 |
