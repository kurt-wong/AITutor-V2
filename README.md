# AI Tutor Personal Edition

家庭自用、面向高中学生的题库管理与智能辅导平台。

## Quick Start

1. 复制环境变量：

```powershell
Copy-Item .env.example .env
```

2. 启动基础服务：

```powershell
docker compose up --build
```

3. 访问：

- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:8080
- MinIO Console: http://localhost:9001

## 文档

- 需求与方案：`Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`
- 项目字典：`Docs/00_Requirements/DICTIONARY.md`
- 项目状态：`PROJECT_STATUS.md`
- 重启恢复：`RESTART_PROMPT.md`

