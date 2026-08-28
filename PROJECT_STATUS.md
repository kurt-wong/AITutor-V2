# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.44
Status: P4E.1 子题链路修复完成并验证（52 题入库）+ 前端展示重构完成；测试门禁未启动；token 消耗根因=DSH 会话重发上下文
Date: 2026-08-28

---

## 当前阶段

Phase 2A/2B/2C 已验收；OCR Provider 策略落地（PPS/PVL 主识别、LLM VL 移出驱动链）；
Sprint 治理五项完成（content_hash 生命周期 / DSD §8 / AGENTS 薄入口 / Pipeline 方案 A /
fixture 版本化）。

**v6.44（2026-08-28，P4E.1 主体完成）**：
- **子题链路 6 处补齐 + 答案/详解/配图修复已全部落地并经真实文档验证**（P4E.1 任务 1/2/3）：
  3 份验证文档（东城英语/八中数学/丰台物理）重跑完成，52 题入库——父题答案聚合子题、
  配图 page 约束（不再跨页误关联）、详解保留教师版换行、作文英文原文。
- **前端展示重构完成**：`〔N〕` 空位高亮、题干默认展开 + 答案/详解折叠、
  答案格式化（`(1) C (2) D` → `1.C 2.D`）、子题题干去重。
- **空位标记 5/10**（旧正则数据）：正则已修复（允许数字后接字母），要全 10/10 需
  重跑 3 份（约 ¥1-2）——**待用户决策**：重跑 or 推迟到批量导入。
- **token 消耗根因锁定**：11:00 后 103 次 / 7,097 万 token（平均 ~69 万/次）=
  **DSH 会话每轮重发全部历史**（上下文膨胀至 ~70 万 token），非 V1/V2 worker。
  用户已决定开新会话恢复。成本防护：`WORKER_ENABLED=0` 环境变量 gate（API-only）。
- **测试门禁（P4E.1 任务 4）未启动**：golden 子题结构 + run_live_validation 准确率
  FAIL + 选项完整性指标——**新会话首个任务**。

## 关键验收

| 项 | 状态 |
|---|---|
| Phase 2A 总验收 | ✅ |
| Phase 2B 搜索/统计 | ✅ |
| Phase 2C Structure Signature | ✅ |
| OCR Provider 策略（PPS/PVL 主识别、LLM VL 移出驱动链） | ✅ 651 passed |
| paddle 耗尽不降级（OCROutageError + ocr_unavailable） | ✅ |
| 批量恢复脚本（retry_ocr_unavailable.py） | ✅ |
| worker 超时兜底（P7/P10）+ 僵尸恢复（v6.33/6.34） | ✅ |
| DOCX 全管线支持 + 扫描件标注（v6.34） | ✅ |
| 9 科答案 mismatch / 严格通过 | ✅ 0 / 212/215 (99%) |
| 题库管理页（v6.40）+ 图片 URL 落库（v6.41） | ✅ |
| Sprint 治理五项（v6.42） | ✅ 680 passed |
| 入库质量审计（v6.43）：6 类错误量化、根因定位 | ✅ 诊断完成 |
| **P4E.1 任务 1/2/3（子题链路/紧凑选项/父题不拼接）** | ✅ 52 题入库验证 |
| **前端展示重构（空位高亮/折叠/格式化）** | ✅ |
| **P4E.1 任务 4（测试门禁）** | ⏳ 未启动 |
| **P4E.1 任务 5（验证文档空位标记 10/10）** | ⏳ 5/10，待决策重跑 |
| pytest（专用测试库） | ✅ 687 passed / 2 errors（沙箱环境限制） |

## 当前状态（v6.44）

- **入库质量**：子题数据链路修复完成（此前 20.9% 坏的核心根因已消除）；3 份验证
  文档 52 题入库结构完整。空位标记 5/10（旧正则数据，重跑可全）。
- **token 消耗**：根因 = DSH 会话重发上下文（每轮 ~69 万 token）。V1/V2 worker 正常
  量级（今日 V2 仅 ~40 次 flash）。**新会话每轮成本将降到几万 token。**
- **成本防护**：`WORKER_ENABLED=0` → API-only（无 LLM 消费）；走环境变量不写 .env。
- **测试**：687 passed / 2 errors（沙箱 temp ACL，用户本机可过）。
- **服务状态**：8000（uvicorn）与 5173（vite）当前未监听（会话收尾已停）。

## 数据与文档基线

- migration `20260821_0003/0005`、`20260827_0001` 已执行；知识树 333 节点。
- 专用测试库 `aitutors_test`（`AITUTOR_TEST_DB=0` 关闭）。
- 文档治理快照模式：v6.42 已归档 `docs_archive/status/2026-08-27_*_v6.42.md`。
- `D:\Project\Papers` 是批量导入源（maintainess 整理集 + 高一/高一上/高二/高三原始集）。
- V2 `backend\.env`：DEEPSEEK_API_KEY=`sk-06123f…`（新，已验证）；V1（D:\Project\AI
  Tutors）已换 sk-1bd6a1…，遗留 v4-pro 强制 + explain_queue 6 任务待处理。

## 当前焦点（新会话按此顺序）

1. **测试门禁（P4E.1 任务 4）**：golden 补子题结构（子题数 + 每子题 options_line_ids
   精确）；run_live_validation 把 golden 准确率纳入 FAIL（<80%）；选项完整性指标
   （label 数/空选项/内嵌）。回归测试能抓"子题内容丢失/选项拼接/紧凑未拆"。
2. **空位标记决策**（等用户）：重跑 3 份验证文档补全 10/10（约 ¥1-2）或推迟到
   批量导入（P4E.2 时正则已修，直接产出完整标记）。
3. **批量导入（P4E.2）**：全盘 9 万 → 清单（文件名元数据 + 去重 + 文本层检测）→
   30 份 → 100 份 → 全量；DOCX 优先。P4E.1 验收通过后启动。
4. **V1 遗留清理**（可选）：async_pipeline v4-pro 强制改 flash/禁用；Redis
   explain_queue 6 任务清除。
5. **异步补全**：详解空缺 LLM 生成（标记 `llm_fallback`）。
6. **扫描件**（错题拍照场景）：PPS/PVL 路径预留，下一轮。

## 历史与快照

- 完整变更历史：`LOG.md`
- 快照：`docs_archive/status/2026-08-27_PROJECT_STATUS_v6.42.md`
- 快照：`docs_archive/status/2026-08-27_RESTART_PROMPT_v6.42.md`
- 快照：`docs_archive/status/2026-08-27_PROJECT_STATUS_v6.41.md`
