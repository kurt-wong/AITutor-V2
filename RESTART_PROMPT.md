# AI Tutor Personal Edition — RESTART_PROMPT

Version: 6.46
Status: 文档治理精简完成（v6.46：TASK/PLAN/T3/Design 归档，ROADMAP 吸收任务规范）
Date: 2026-08-29

---

## 1. 用途

Codex/Claude 重启后先读本文件恢复上下文。本文件只承载稳定信息：项目目标、
基础架构、强制规则、文档地图、恢复流程。最新状态不写入本文件。

---

## 2. 项目目标

1. 批量上传教师版 PDF/DOCX，自动提取题目、配图、答案、详解和元数据。
2. 题库支持题型频次、年份趋势、知识点占比、难度分布等统计分析。
3. AI 基于历史趋势生成新题，经审核入库，支持导出学生版与答案详解版。
4. 学生上传 JPG 错题，自动切分、识别、匹配或新建，形成错题本。
5. 根据错题和知识点掌握度生成练习，自动判分并记录学习过程。

---

## 3. 架构与强制规则

- 调用链：UI → API → Application Service → Domain Service → Repository → DB。
- AI 必须经 Gateway，禁止直连模型 SDK；Agent 只能通过 MCP/Application Service。
- LLM 只输出行号/元数据，不输出题目原文；代码锚点校正后切片。
- PDF 采用 Native + PP-StructureV3 双源 L1，canonical 按证据选择。
- 配图必须带 page/bbox/placement/source，禁止猜图。
- 教师版答案/详解优先，LLM 只兜底并标记来源。
- Schema 变更必须 Alembic migration；知识树为空不得静默跳过映射。
- 常规 pytest mock，live LLM/OCR 验证隔离。
- 密钥/Token 只走 backend/.env，禁止硬编码。
- **Token 成本（2026-08-28 实测教训）**：DSH/Codex 会话每轮重发全部历史，上下文
  膨胀到 ~70 万 token 时每轮烧 ~69 万 token（10 次即 ~700 万）。长任务应拆子代理
  或开新会话，不要在一个会话里无限堆积；不跑入库时用 `WORKER_ENABLED=0` API-only。
- 完整规则见 `rules.md`，解析教训见 `Docs/05_Development/V1_LESSONS.md`。

---

## 4. 文档地图

| 文档 | 用途 |
|---|---|
| `rules.md` | 项目规则与约束 |
| `PROJECT_STATUS.md` | 最新项目状态与下一步 |
| `LOG.md` | 完整变更历史 |
| `bugs.md` | 已知问题与修复记录 |
| `docs_archive/status/` | 版本化状态快照 |
| `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md` | 需求与方案基线 |
| `Docs/01_Product/ROADMAP.md` | 阶段任务计划 |
| `Docs/02_Architecture/SAD.md` | 系统架构 |
| `Docs/02_Architecture/MIS.md` | MCP 工具规范 |
| `Docs/02_Architecture/ACS.md` | API 合约 |
| `Docs/02_Architecture/PIPELINE.md` | 文档入库管线 |
| `Docs/03_Data/DSD.md` | 数据库结构 |
| `Docs/05_Development/V1_LESSONS.md` | V1 教训与强制约束 |

---

## 5. 恢复流程

1. 读 `RESTART_PROMPT.md`。
2. 读 `rules.md`。
3. 读 `PROJECT_STATUS.md`，只取最新状态。
4. 按任务读对应权威文档。
5. `LOG.md` 按需读取尾部或搜索，不全文加载。

---

## 6. 服务启动（重启 PC 后）

### 6.1 基础设施（Docker 容器，Docker Desktop 启动后自动恢复）

```powershell
docker ps -a --filter "name=aitutor"
# 若未自动启动：
docker start aitutor-postgres aitutor-minio aitutor-redis
```

| 容器 | 端口 | 凭据 |
|---|---|---|
| aitutor-postgres | localhost:15432 | postgres/postgres，db=aitutors |
| aitutor-minio | localhost:9000 (API) / 9001 (控制台) | minioadmin/minioadmin，bucket=aitutors |
| aitutor-redis | localhost:16379 | — |

> **Docker Compose 方案**（端口/容器名不同）：`docker compose up --build` 使用
> `docker-compose.yml`，postgres 5432 / redis 6379 / minio 9000，前端 8080。
> 两套方案不兼容，不要同时启动。详见 `README.md`。

### 6.2 后端（uvicorn，8000）

```powershell
cd D:\Project\AITutors-v2\backend
# API-only 模式（无 LLM 消费，推荐日常开发/验证用）：
$env:WORKER_ENABLED='0'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level warning
# 需要跑文档入库（worker 消费 LLM）时才去掉 WORKER_ENABLED=0
```
验证：`http://localhost:8000/api/admin/catalog` 返回 JSON（非 index.html）。

> **成本防护（2026-08-28）**：`WORKER_ENABLED` gate 走环境变量，不写 .env；
> 默认 1 启动 worker。13:16 曾出现 uvicorn 被外部重启后 worker 自动消费 LLM——
> 不跑入库任务时务必设 `WORKER_ENABLED='0'`。

### 6.3 前端（vite dev，5173）

```powershell
cd D:\Project\AITutors-v2\frontend
npx vite --port 5173 --strictPort
```
**注意**：沙箱环境需 `danger-full-access`（esbuild 子进程 spawn 限制）。
验证：`http://localhost:5173/admin/questions` 正常渲染。

### 6.4 测试库（pytest 默认走 aitutors_test，自动重定向）

```powershell
$env:AITUTOR_TEST_DB='0'   # 需要连真实库时关闭
cd D:\Project\AITutors-v2\backend
python -m pytest tests -q -p no:cacheprovider
```

---

## 7. 验证清单

```powershell
python test/scripts/llm_smoke_test.py --live
python test/scripts/ocr_smoke.py --provider all
python test/scripts/run_live_validation.py --with-ocr --runs 2
```

---

## 8. 历史与快照

- 当前状态：`PROJECT_STATUS.md`
- 变更历史：`LOG.md`
- 旧版完整快照：`docs_archive/status/2026-08-28_RESTART_PROMPT_v6.44.md`
- 旧版完整快照：`docs_archive/status/2026-08-28_PROJECT_STATUS_v6.44.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_RESTART_PROMPT_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_PROJECT_STATUS_v6.20.md`
