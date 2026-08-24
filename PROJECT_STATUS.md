# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.24
Status: 9 科答案基线 mismatch=0、严格 215/231 (93%)；物理答案缺口 5 题修复 + 语文 Q17 审核修复
Date: 2026-08-25

---

## 当前阶段

Phase 2A/2B/2C 已验收；P0 入库管线修复完成；OCR 链加固完成；provider_used 落盘；
9 科答案基线已提升至 mismatch=0、严格通过 **215/231 (93%)**。本轮完成：数学 LaTeX
答案归一化、语文位置行号区间校验、膨胀检测材料题识别、历史重跑修复 Q37、专用测试库、
物理答案证据 5 题验证器修复、语文 Q17 串题人工审核修复 + 答案假冲突改进（BUG-026）。

## 关键验收

| 项 | 状态 |
|---|---|
| Phase 2A 总验收 | ✅ |
| Phase 2B 搜索/统计 | ✅ |
| Phase 2C Structure Signature | ✅ |
| P0 入库管线修复 | ✅ |
| OCR 链加固（paddle 401 → mimo 回退） | ✅ |
| provider_used 落盘 | ✅ |
| 英语 stem/选项 | ✅ 11/11 |
| 语文位置 | ✅ 24/24 |
| 数学 LaTeX 答案归一化 | ✅ 22/23 |
| 历史 Q37 缺库修复 | ✅ 42/43 |
| 物理答案证据缺口（BUG-025） | ✅ 11/20 → 16/20 |
| 语文 Q17 串题（人工审核 A 方案） | ✅ 22/24 → 23/24 |
| 9 科答案 mismatch | ✅ 0 |
| 9 科严格通过 | ✅ 215/231 (93%) |
| pytest（专用测试库） | ✅ 648+ passed |
| Phase 2D | ⏸ 前置条件未满足 |

## 最近版本摘要

| 版本 | 关键内容 |
|---|---|
| 6.24 | 语文 Q17 审核修复（串题截断 + 假冲突 BUG-026）、9 科基线 215/231 |
| 6.23 | 物理答案证据 5 题修复（BUG-025）、9 科基线 214/231 |
| 6.22 | 历史重跑 Q37 修复、9 科最终基线 209/231、快照模式落地 |
| 6.20 | 语文位置 23/24、膨胀检测材料题识别、物理 mimo-vl 重跑、pytest 648 passed |
| 6.17 | 数学 LaTeX 归一化、严格 16/23 → 22/23、9 科 204/231 |
| 6.14 | 语文重跑 19/24、独立题共享材料合并、9 科 187/213 |
| 6.12 | provider_used 落盘、Phase 2D 前置评估 |
| 6.11 | 英语 stem/选项 11/11、Q46 作文入库 |

## 当前状态

- 9 科答案基线：mismatch=0，严格通过 **215/231 (93%)**；答U 14、答M 0。
- 各科严格：语文 23/24、数学 22/23、历史 42/43、政治 28/28、生物 24/24、化学 25/26、
  英语 10/11、地理 25/30、物理 16/20（剩余缺口：缺库 2 + free_text 2）。
- 物理答案证据 5 题修复（BUG-025）：空单元格答案表按行重排（Q3/Q9/Q10）、综合题子题
  内联搜索（Q15/Q16）、自共享材料跳过（Q16 材料误报）——均为验证器漏检，DB 数据正确。
- 语文 Q17（人工审核 A 方案）：stem 截断 1840 → 228（去除《到泗洪去》串题材料）、
  转 approved；answer_conflict 确认为假冲突（仅空格差异）已清标记；ingestion 答案
  比较改为去空白后比对（BUG-026），防复发。
- 历史 Q37 已修复（重跑 LLM 重标注）；遗留 Q26 选项 D 缺失。
- 物理 mimo-vl 重跑：严格 11/20 → 16/20，材料 20/20；paddle 401 已由 mimo 兜底。
- pytest：专用测试库 aitutors_test 下 648+ passed；剩余 2 failed + 2 errors 为沙箱 temp。
- T0-2 key 轮换：用户决定暂缓，泄漏原 key 未轮换；步骤见 `bugs.md`。

## 数据与文档基线

- migration `20260821_0003`、`20260821_0005` 已执行。
- 知识树 333 节点、292 父子关系已入库。
- 专用测试库 `aitutors_test`（alembic head + 知识树种子），pytest 默认重定向
  （`AITUTOR_TEST_DB=0` 关闭），初始化脚本 `backend/scripts/setup_test_db.py`。
- 语文 Q17 数据修复脚本：`backend/scripts/fix_yuwen_q17_stem.py`（幂等）。
- 文档治理 v6.21+：`PROJECT_STATUS.md` 与 `RESTART_PROMPT.md` 只保留最新/稳定内容，
  历史统一归档到 `docs_archive/status/` 与 `LOG.md`。

## 当前焦点

1. 物理剩余缺口（16/20）：Q4/Q7 缺库（mimo OCR 题干为空）、Q17/Q20 free_text_answer
   （DB 精简答案 vs 答案区完整解答，证据表示不可自动对齐）——需人工核对或 OCR 重识别。
2. 语文 Q24 答案 free_text_answer（精简版 vs 完整解答）。
3. 历史 Q26 选项 D 缺失。
4. 膨胀边界遗留：化学 Q23/Q24、地理 Q26 长解答题 reviewing（保守标记）。
5. 英语 Q46 `essay_manual_review` 验证改进。
6. T0-2 泄漏 API key 轮换（用户决定暂缓）。
7. 扩充样本 + 补齐 9 科 Structure Signature，条件满足后启动 Phase 2D。

## 历史与快照

- 完整变更历史：`LOG.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_PROJECT_STATUS_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_RESTART_PROMPT_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_PROJECT_STATUS_v6.21.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_RESTART_PROMPT_v6.21.md`
