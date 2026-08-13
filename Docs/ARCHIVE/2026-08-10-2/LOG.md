# AI Tutor Personal Edition — 变更日志

---

## 变更记录

### 2026-08-10 21:20:30

#### 文档基线重写

- 新增 `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`，记录真实需求问答结果。
- 重写 `Docs/01_Product/PRD.md`，从旧规划改为当前开发指引基线。
- 重写 `Docs/02_Architecture/SAD.md`、`ACS.md`、`MIS.md`、`PIPELINE.md`。
- 重写 `Docs/03_Data/DSD.md`。
- 新增 `Docs/02_Architecture/UI.md`，将 `Docs/Design.md` 映射到前端页面规范。
- 新增 `Docs/01_Product/TASK.md` 和 `PROJECT_STATUS.md`。
- 旧版核心文档备份到 `Docs/ARCHIVE/2026-08-10/`。

### 2026-08-10 21:56:55

#### 新增记录规范与重启恢复文档

- 在 `rules.md` 增加“记录规范”：`LOG.md` 和 `PROJECT_STATUS.md` 的新增内容必须包含完整时间戳，按时间顺序追加到文件末尾，禁止在文件头部随意新增。
- 调整 `LOG.md` 为文末时间戳追加格式。
- 调整 `PROJECT_STATUS.md` 为当前快照 + 文末时间戳更新记录格式。
- 新增 `RESTART_PROMPT.md`，用于 Codex/Claude 重启后恢复项目目标、系统现状和待办任务。

