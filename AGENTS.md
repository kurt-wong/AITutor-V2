# AI Tutor Personal Edition — Agent 薄入口

本文件是 Codex/Claude/opencode 等代理的**薄入口**，只负责指向权威文档，
不承载项目细节（2026-08-27，P0 治理：原 agent 路由指南不携带项目上下文，
改为入口，避免代理只读本文件而缺失项目上下文）。

## 必读文件（按顺序）

1. `RESTART_PROMPT.md` — 项目目标、基础架构、强制规则、文档地图、恢复流程
2. `rules.md` — 项目级规则与约束（调用链、V1 教训、记录规范、工作指令）
3. `PROJECT_STATUS.md` — 当前状态与下一步（只取最新状态，不读历史堆积）

## 强制红线（摘要，详见 rules.md）

- 唯一调用链：UI → API → Application Service → Domain Service → Repository → DB
- AI 必须经 Gateway；Agent 只能通过 MCP/Application Service
- 文档优先：代码修改严格遵循权威文档，偏离必须先沟通确认
- 记录规范：重要变更在 `LOG.md` 文末追加；状态变化更新 `PROJECT_STATUS.md`

## 文档地图

完整文档地图见 `RESTART_PROMPT.md` §4；按任务读取对应权威文档
（需求 `Docs/00_Requirements/`、架构 `Docs/02_Architecture/`、数据 `Docs/03_Data/DSD.md` 等）。
