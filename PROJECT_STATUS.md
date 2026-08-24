# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.29
Status: 数据源决策完成（PPS 为主、化学 mimo）；基线 210/215 (98%)
Date: 2026-08-25

---

## 当前阶段

Phase 2A/2B/2C 已验收；P0 入库管线修复完成；OCR Provider 策略落地（PPS/PVL
主识别、LLM VL 移出驱动链）；**数据源决策完成**：PPS（PP-StructureV3）为主
（语文综合题粒度 8/8 确认非退化）、**化学保留 mimo**（Paddle 系对化学表格
选项不适用——PPS 21/26、VL 15/26，mimo 26/26）。基线 **210/215 (98%)**。

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
| subject/ocr_model 传递修复（化学 VL 路由失效） | ✅ |
| 数据源决策（PPS 为主、化学 mimo） | ✅ |
| 英语 | ✅ 11/11 |
| 语文（PPS 综合题粒度） | ✅ 8/8 |
| 数学 | ✅ 22/23（Q15 负号证据缺失） |
| 历史 | ✅ 43/43（PPS 版 100%） |
| 物理 | ✅ 19/20（PPS 版，Q18 答案依赖图） |
| 化学 | ✅ 26/26（mimo 保留——Paddle 系表格盲区） |
| 生物 | ✅ 26/26 |
| 9 科答案 mismatch | ✅ 0 |
| 9 科严格通过（PPS 为主，语文综合粒度） | ✅ 210/215 (98%) |
| pytest（专用测试库） | ✅ 651+ passed |
| Phase 2D | ⏸ 前置条件未满足 |

## 最近版本摘要

| 版本 | 关键内容 |
|---|---|
| 6.29 | 化学 VL 验证（15/26 比 PPS 更差）→ 化学保留 mimo；数据源决策完成，基线 210/215 |
| 6.28 | PPS 全科重跑（语文综合粒度 8/8、生物/英语/政治/地理干净）、化学 VL 重跑中、subject 传递修复 |
| 6.27 | PPS 数据补丁（物理 Q4/Q7/Q20、历史 Q37）+ 地理/生物缺库修复，基线 225/231 |
| 6.26 | OCR Provider 策略代码改造（VL 移出驱动链、ocr_unavailable、批量恢复）、PPS 重跑物理/历史 |
| 6.25 | 6 项遗留修复：Q4/Q7 回填、结构化答案、Q24 作文、Q26 选项 D、膨胀边界、Q46 essay |
| 6.24 | 语文 Q17 审核修复（串题截断 + 假冲突 BUG-026）、9 科基线 215/231 |
| 6.23 | 物理答案证据 5 题修复（BUG-025）、9 科基线 214/231 |
| 6.22 | 历史重跑 Q37 修复、9 科最终基线 209/231、快照模式落地 |
| 6.20 | 语文位置 23/24、膨胀检测材料题识别、物理 mimo-vl 重跑、pytest 648 passed |
| 6.17 | 数学 LaTeX 归一化、严格 16/23 → 22/23、9 科 204/231 |

## 当前状态

- 9 科基线：mismatch=0，严格通过 **210/215 (98%)**；答U 5、答M 0。
  **注意**：语文为 PPS 综合题粒度（8 题覆盖全卷，total 口径 231→215）。
- 各科严格：语文 8/8、历史 43/43、化学 26/26、生物 26/26、政治 28/28、
  英语 11/11、地理 27/27（真实）、物理 19/20、数学 22/23。
- **数据源决策（2026-08-25）**：PPS（PP-StructureV3）为主——语文
  （综合粒度 8/8 非退化）、物理、历史、数学、生物、政治、英语、地理；
  **化学保留 mimo 26/26**——Paddle 系（PPS 21/26、VL 15/26）对化学表格
  选项均不适用（表格内选项结构识别差；VL 提取出 HTML 表格但行号/归属
  大面积错乱）。PPS/VL 化学文档标记 superseded（数据保留）。
- OCR Provider 策略：L1 识别仅 paddle 系；LLM VL 移出驱动链；paddle
  不可用时任务标记 `ocr_unavailable` 等恢复重跑。10010 队列满为服务端
  瞬时状态（夜间批量更优）。subject/ocr_model 传递已修复（上传接口支持
  ocr_model 显式覆盖）。
- 剩余缺口（诚实口径）：物理 Q18 答案依赖受力分析图、数学 Q15 负号证据
  三源损坏（DB 答案数学正确）、地理报告含管线幻选题号残留（DB 27 正确）。
- pytest：专用测试库 aitutors_test 下 **651+ passed**；2 failed + 2 errors 沙箱 ACL。
- T0-2 key 轮换：用户决定暂缓，泄漏原 key 未轮换；步骤见 `bugs.md`。

## 数据与文档基线

- migration `20260821_0003`、`20260821_0005` 已执行。
- 知识树 333 节点、292 父子关系已入库。
- 专用测试库 `aitutors_test`（alembic head + 知识树种子），pytest 默认重定向
  （`AITUTOR_TEST_DB=0` 关闭），初始化脚本 `backend/scripts/setup_test_db.py`。
- OCR 策略与实施：`Docs/02_Architecture/OCR_PROVIDER_POLICY.md`；
  批量恢复：`backend/scripts/retry_ocr_unavailable.py`；
  subject/ocr_model 传递：上传接口支持 ocr_model 显式覆盖（如
  "PaddleOCR-VL-1.6"）。
- 文档治理 v6.21+：`PROJECT_STATUS.md` 与 `RESTART_PROMPT.md` 只保留最新/稳定内容，
  历史统一归档到 `docs_archive/status/` 与 `LOG.md`。

## 当前焦点

1. 物理 Q18 答案依赖图、数学 Q15 负号证据——诚实登记，人工核对可选。
2. T0-2 泄漏 API key 轮换（用户决定暂缓）。
3. 扩充样本 + 补齐 9 科 Structure Signature，条件满足后启动 Phase 2D。

## 历史与快照

- 完整变更历史：`LOG.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_PROJECT_STATUS_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_RESTART_PROMPT_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_PROJECT_STATUS_v6.21.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_RESTART_PROMPT_v6.21.md`
