# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.27
Status: 9 科答案基线 225/231 (97%)；物理/历史 PPS 重跑 + 地理/生物缺库修复
Date: 2026-08-25

---

## 当前阶段

Phase 2A/2B/2C 已验收；P0 入库管线修复完成；OCR Provider 策略落地（PPS/PVL
主识别、LLM VL 移出驱动链、`ocr_unavailable` 等待恢复）；9 科基线 **225/231
(97%)**。本轮完成：物理/历史 PPS 数据补丁（Q4/Q7/Q20/Q37）、地理缺库修复
（发现并删除 L2 幻选题）、生物 Q1/Q2 回填、verifier 希腊字母/单位归一改进。

## 关键验收

| 项 | 状态 |
|---|---|
| Phase 2A 总验收 | ✅ |
| Phase 2B 搜索/统计 | ✅ |
| Phase 2C Structure Signature | ✅ |
| P0 入库管线修复 | ✅ |
| OCR Provider 策略（PPS/PVL 主识别、LLM VL 移出驱动链） | ✅ 651 passed |
| paddle 耗尽不降级（OCROutageError + ocr_unavailable） | ✅ |
| 批量恢复脚本（retry_ocr_unavailable.py） | ✅ |
| provider_used 落盘 | ✅ |
| 英语 | ✅ 11/11 |
| 语文 | ✅ 24/24 |
| 数学 | ✅ 22/23（Q15 负号证据缺失） |
| 历史 | ✅ 43/43（PPS 版 100%） |
| 物理 | ✅ 19/20（PPS 版，Q18 答案依赖图） |
| 化学 | ✅ 26/26 |
| 生物 | ✅ 26/26 |
| 9 科答案 mismatch | ✅ 0 |
| 9 科严格通过 | ✅ 225/231 (97%) |
| pytest（专用测试库） | ✅ 651 passed |
| Phase 2D | ⏸ 前置条件未满足 |

## 最近版本摘要

| 版本 | 关键内容 |
|---|---|
| 6.27 | PPS 数据补丁（物理 Q4/Q7/Q20、历史 Q37）+ 地理/生物缺库修复，基线 225/231 |
| 6.26 | OCR Provider 策略代码改造（VL 移出驱动链、ocr_unavailable、批量恢复）、PPS 重跑物理/历史 |
| 6.25 | 6 项遗留修复：Q4/Q7 回填、结构化答案、Q24 作文、Q26 选项 D、膨胀边界、Q46 essay |
| 6.24 | 语文 Q17 审核修复（串题截断 + 假冲突 BUG-026）、9 科基线 215/231 |
| 6.23 | 物理答案证据 5 题修复（BUG-025）、9 科基线 214/231 |
| 6.22 | 历史重跑 Q37 修复、9 科最终基线 209/231、快照模式落地 |
| 6.20 | 语文位置 23/24、膨胀检测材料题识别、物理 mimo-vl 重跑、pytest 648 passed |
| 6.17 | 数学 LaTeX 归一化、严格 16/23 → 22/23、9 科 204/231 |

## 当前状态

- 9 科答案基线：mismatch=0，严格通过 **225/231 (97%)**；答U 5、答M 0。
  **注意**：物理/历史/数学为 PPS（PP-StructureV3）重跑版本（2026-08-25 策略），
  其余科为 mimo 版本；两 provider 互补，PPS 版本需数据补丁兜底。
- 各科严格：语文 24/24、历史 43/43、化学 26/26、英语 11/11、生物 26/26、
  政治 28/28、数学 22/23、物理 19/20、地理 26/30。
- OCR Provider 策略（用户决策 2026-08-25）：L1 识别仅 paddle 系；LLM VL
  （mimo-vl/deepseek-vl）移出驱动链（仅可选交叉验证）；paddle 不可用时任务
  标记 `ocr_unavailable` 等恢复重跑，不降级。token 已更新（401 消除），
  paddle 10010 队列满为服务端瞬时状态（夜间批量更优）。
- 本轮修复：物理 Q4/Q7/Q20 补丁（回填+截断+section 修正）、历史 Q37 回填、
  地理 Q21/Q30 回填 + L2 幻选题（23/24/25）删除、生物 Q1/Q2 回填、
  verifier 希腊字母/单位归一（PPS 纯文本答案适配）。
- 剩余缺口（诚实口径）：物理 Q18 答案 (1) 依赖受力分析图（无文本答案）、
  数学 Q15 负号证据三源损坏（DB 答案数学正确）、地理 Q30 长解答题图表
  位置口径 N + 报告含管线幻选题号（DB 27 正确）。
- pytest：专用测试库 aitutors_test 下 **651 passed**；2 failed + 2 errors 沙箱 ACL。
- T0-2 key 轮换：用户决定暂缓，泄漏原 key 未轮换；步骤见 `bugs.md`。

## 数据与文档基线

- migration `20260821_0003`、`20260821_0005` 已执行。
- 知识树 333 节点、292 父子关系已入库。
- 专用测试库 `aitutors_test`（alembic head + 知识树种子），pytest 默认重定向
  （`AITUTOR_TEST_DB=0` 关闭），初始化脚本 `backend/scripts/setup_test_db.py`。
- OCR 策略与实施：`Docs/02_Architecture/OCR_PROVIDER_POLICY.md`；
  批量恢复：`backend/scripts/retry_ocr_unavailable.py`；
  数据回填脚本：`backfill_physics_q4_q7.py`、`backfill_history_q37.py`、
  `backfill_geo_missing.py`、`backfill_bio_q1q2.py`、`backfill_pps_missing_options.py`。
- 文档治理 v6.21+：`PROJECT_STATUS.md` 与 `RESTART_PROMPT.md` 只保留最新/稳定内容，
  历史统一归档到 `docs_archive/status/` 与 `LOG.md`。

## 当前焦点

1. 数学 Q15：PPS 重跑验证负号（进行中）；物理 Q18 答案依赖图、地理 Q30
   长解答题图表口径——诚实登记，人工核对可选。
2. 其余科（语文/化学/政治/英语/生物）是否 PPS 重跑统一数据源（待用户决策）。
3. T0-2 泄漏 API key 轮换（用户决定暂缓）。
4. 扩充样本 + 补齐 9 科 Structure Signature，条件满足后启动 Phase 2D。

## 历史与快照

- 完整变更历史：`LOG.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_PROJECT_STATUS_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_RESTART_PROMPT_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_PROJECT_STATUS_v6.21.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_RESTART_PROMPT_v6.21.md`
