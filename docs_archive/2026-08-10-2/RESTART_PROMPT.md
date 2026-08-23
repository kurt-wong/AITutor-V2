# AI Tutor Personal Edition — RESTART_PROMPT

Version: 0.1
Status: 重启恢复指引
Date: 2026-08-10 21:56:55

---

## 1. 用途

本文件用于 Codex/Claude 在重启后快速恢复工作状态。

任何 Agent 进入项目后，应先读本文件，再按需读取 `rules.md`、`PROJECT_STATUS.md`、`LOG.md` 和相关权威文档。

---

## 2. 项目目标

项目是一个家庭自用、面向高中学生的题库管理与智能辅导平台。

核心目标：

1. 管理员批量上传教师版 PDF/DOCX，系统自动提取题目、配图、答案、详解和元数据。
2. 题库支持题型频次、年份趋势、知识点占比、难度分布等统计分析。
3. AI 根据历史趋势、频率和占比生成新题，经管理员审核后入库，并支持导出学生版和答案详解版。
4. 学生上传 JPG 错题，系统自动切分、识别、匹配或新建，形成错题本。
5. 系统根据错题和知识点掌握度生成针对性练习，自动判分并记录学习过程。

---

## 3. 系统现状

当前阶段：规划/文档基线阶段。

- 已有完整需求基线，但尚无可运行代码。
- 核心文档已按新需求重写，旧文档已备份到 `Docs/ARCHIVE/2026-08-10/`。
- 已确认使用 Docker 部署在 NAS，NAS 只有 CPU。
- 已确认 embedding 使用本地轻量模型，文档解析、题目生成等重任务使用云 API。
- 已有 DeepSeek、MIMO、PaddleOCR-VL、PP-StructureV3 API Key。
- 尚未建立真实文档解析准确率测试集。
- 尚未创建后端、前端、数据库迁移。

---

## 4. 文档地图

| 文档 | 用途 |
|---|---|
| `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md` | 真实需求与方案基线 |
| `Docs/01_Product/PRD.md` | 产品需求 |
| `Docs/01_Product/TASK.md` | 任务执行规范 |
| `Docs/02_Architecture/SAD.md` | 系统架构 |
| `Docs/02_Architecture/MIS.md` | MCP 工具规范 |
| `Docs/02_Architecture/ACS.md` | API 合约 |
| `Docs/02_Architecture/PIPELINE.md` | 文档入库管线 |
| `Docs/02_Architecture/UI.md` | 前端页面规范 |
| `Docs/03_Data/DSD.md` | 数据库结构 |
| `Docs/Design.md` | 前端视觉设计风格 |
| `PROJECT_STATUS.md` | 当前状态和下一步 |
| `LOG.md` | 变更历史 |
| `rules.md` | 项目规则和约束 |

---

## 5. 待办任务

### T1. 建立真实文档测试集

- 收集代表性教师版 PDF/DOCX。
- 覆盖数学、物理、化学、英语、语文、生物、政治。
- 覆盖文末答案和题后答案。
- 覆盖配图题、公式题、表格题、复合题。
- 建立字段级准确率统计。

### T2. 搭建后端骨架

- FastAPI 项目结构。
- Service 层、Repository 层、MCP Tool 层骨架。
- PostgreSQL、MinIO、Redis 本地可运行。
- LLM Gateway 基础路由。

### T3. 实现文档解析管线

- 按 `Docs/02_Architecture/PIPELINE.md` 实现。
- 优先验证 PDF/DOCX 到题目、配图、答案、详解的结构化提取。
- 输出置信度并支持低置信度审核。

### T4. 实现题库与审核

- 题目 CRUD。
- 低置信度审核队列。
- 重复题合并。
- 题目内容与元数据分开维护。

### T5. 实现统计与分析

- 题型频次和年份趋势。
- 知识点频次和占比。
- 难度分布。
- 错题统计。
- 学生学习趋势。

### T6. 实现 AI 组题与导出

- 根据历史趋势、频率和占比自动生成新题。
- 支持手动比例覆盖。
- 生成题审核后入库，标记为生成题。
- 导出学生版，以及答案和详解独立版。

### T7. 实现学生错题

- JPG 多题自动切分。
- 识别、匹配题库或新建。
- 管理员确认后进入错题本。
- 错题本列表、详情、重练、标记已掌握。

### T8. 实现练习与掌握度

- 自动判分。
- 保存题目快照、答案、对错、用时、知识点。
- 答错自动进入错题本。
- 根据掌握度调整出题。

### T9. 实现前端

- 管理员后台和学生端。
- 按 `Docs/02_Architecture/UI.md` 和 `Docs/Design.md` 实现。
- 先支持电脑浏览器。

### T10. Docker/NAS 部署

- Docker Compose 编排。
- PostgreSQL、MinIO、Redis、backend、worker、frontend。
- API Key 通过 `.env` 管理。

---

## 6. 恢复流程

Codex/Claude 启动后建议按以下顺序恢复：

1. 读 `RESTART_PROMPT.md`。
2. 读 `rules.md`，确认不可违反规则。
3. 读 `PROJECT_STATUS.md` 和 `LOG.md`，确认当前状态。
4. 根据任务类型读对应权威文档。
5. 修改前确认当前任务和完成标准，不擅自扩大范围。

---

## 7. 更新记录

### 2026-08-10 21:56:55

- 创建本文件，作为 Codex/Claude 重启恢复入口。

