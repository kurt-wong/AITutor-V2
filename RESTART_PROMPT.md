# AI Tutor Personal Edition — RESTART_PROMPT

Version: 6.25
Status: 文档治理已切换为精简快照模式；功能状态见 PROJECT_STATUS.md
Date: 2026-08-25

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

## 6. 验证清单

```powershell
python test/scripts/llm_smoke_test.py --live
python test/scripts/ocr_smoke.py --provider all
python test/scripts/run_live_validation.py --with-ocr --runs 2
```

---

## 7. 历史与快照

- 当前状态：`PROJECT_STATUS.md`
- 变更历史：`LOG.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_RESTART_PROMPT_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_PROJECT_STATUS_v6.20.md`
