# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.25
Status: 9 科答案基线 mismatch=0、严格 223/231 (97%)；语文/物理/历史/化学/英语 100%
Date: 2026-08-25

---

## 当前阶段

Phase 2A/2B/2C 已验收；P0 入库管线修复完成；OCR 链加固完成；provider_used 落盘；
9 科答案基线已提升至 mismatch=0、严格通过 **223/231 (97%)**。本轮完成 6 项遗留按序
修复：物理 Q4/Q7 缺库回填、物理 Q17/Q20 结构化答案核对、语文 Q24 作文答案回填、
历史 Q26 选项 D 回填、膨胀边界人工审核（含物理 Q20 真膨胀截断）、英语 Q46 essay
验证器改进。

## 关键验收

| 项 | 状态 |
|---|---|
| Phase 2A 总验收 | ✅ |
| Phase 2B 搜索/统计 | ✅ |
| Phase 2C Structure Signature | ✅ |
| P0 入库管线修复 | ✅ |
| OCR 链加固（paddle 401 → mimo 回退） | ✅ |
| provider_used 落盘 | ✅ |
| 英语 | ✅ 11/11 |
| 语文 | ✅ 24/24 |
| 数学 | ✅ 22/23（Q15 负号证据缺失） |
| 历史 | ✅ 43/43 |
| 物理 | ✅ 20/20 |
| 化学 | ✅ 26/26 |
| 9 科答案 mismatch | ✅ 0 |
| 9 科严格通过 | ✅ 223/231 (97%) |
| pytest（专用测试库） | ✅ 649+ passed |
| Phase 2D | ⏸ 前置条件未满足 |

## 最近版本摘要

| 版本 | 关键内容 |
|---|---|
| 6.25 | 6 项遗留修复：Q4/Q7 回填、结构化答案、Q24 作文、Q26 选项 D、膨胀边界、Q46 essay |
| 6.24 | 语文 Q17 审核修复（串题截断 + 假冲突 BUG-026）、9 科基线 215/231 |
| 6.23 | 物理答案证据 5 题修复（BUG-025）、9 科基线 214/231 |
| 6.22 | 历史重跑 Q37 修复、9 科最终基线 209/231、快照模式落地 |
| 6.20 | 语文位置 23/24、膨胀检测材料题识别、物理 mimo-vl 重跑、pytest 648 passed |
| 6.17 | 数学 LaTeX 归一化、严格 16/23 → 22/23、9 科 204/231 |

## 当前状态

- 9 科答案基线：mismatch=0，严格通过 **223/231 (97%)**；答U 8、答M 0。
- 各科严格：语文 24/24、物理 20/20、历史 43/43、化学 26/26、英语 11/11、政治 28/28、
  生物 24/24、数学 22/23、地理 25/30。
- 本轮 6 项修复：Q4/Q7 缺库回填（自主命制部分）、结构化精简答案分部核对
  （物理 Q17/Q20）、语文 Q24 作文答案回填、历史 Q26 选项 D 回填、膨胀边界人工审核
  （化学 Q23/Q24、地理 Q26 approve；物理 Q20 真膨胀截断 1598→862；语文 Q23 假冲突）、
  英语 Q46 essay 验证器改进（答案区逐字命中 → matched）。
- 历史 Q37/Q26、语文 Q17/Q23/Q24、化学 Q11 等此前遗留全部闭环。
- 剩余 8 题：地理 5 缺库（DB 25 vs L2 30）、生物 Q1/Q2 缺库、数学 Q15 负号证据缺失
  （OCR 丢失负号，free_text_answer）。
- pytest：专用测试库 aitutors_test 下 649+ passed；剩余 2 failed + 2 errors 为沙箱 temp。
- T0-2 key 轮换：用户决定暂缓，泄漏原 key 未轮换；步骤见 `bugs.md`。

## 数据与文档基线

- migration `20260821_0003`、`20260821_0005` 已执行。
- 知识树 333 节点、292 父子关系已入库。
- 专用测试库 `aitutors_test`（alembic head + 知识树种子），pytest 默认重定向
  （`AITUTOR_TEST_DB=0` 关闭），初始化脚本 `backend/scripts/setup_test_db.py`。
- 本轮数据修复脚本：`backfill_physics_q4_q7.py`、`fix_yuwen_q24_answer.py`、
  `fix_history_q26_option_d.py`、`fix_bloat_boundary.py`、`fix_chemistry_q11_options.py`。
- 文档治理 v6.21+：`PROJECT_STATUS.md` 与 `RESTART_PROMPT.md` 只保留最新/稳定内容，
  历史统一归档到 `docs_archive/status/` 与 `LOG.md`。

## 当前焦点

1. 地理 5 题缺库（DB 25 vs L2 30 口径差）+ 生物 Q1/Q2 缺库（BUG-004）——重跑或回填。
2. 数学 Q15 答案证据缺失（OCR 丢失负号，free_text_answer）——人工核对或 OCR 重识别。
3. T0-2 泄漏 API key 轮换（用户决定暂缓）。
4. 扩充样本 + 补齐 9 科 Structure Signature，条件满足后启动 Phase 2D。

## 历史与快照

- 完整变更历史：`LOG.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_PROJECT_STATUS_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_RESTART_PROMPT_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_PROJECT_STATUS_v6.21.md`
- 旧版完整快照：`docs_archive/status/2026-08-24_RESTART_PROMPT_v6.21.md`
