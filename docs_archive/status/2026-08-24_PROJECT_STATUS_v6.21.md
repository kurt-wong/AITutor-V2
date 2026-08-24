# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.21
Status: 9 科答案基线 mismatch=0、严格 204/231 (88%)；历史重跑进行中；文档治理精简快照模式
Date: 2026-08-25

---

## 当前阶段

Phase 2A/2B/2C 已验收；P0 入库管线修复完成；OCR 链加固完成；provider_used 落盘；
9 科答案基线已提升至 mismatch=0、严格通过 204/231 (88%)。当前进行历史重跑与最终基线汇总。

## 关键验收

| 项 | 状态 |
|---|---|
| Phase 2A 总验收 | ✅ |
| Phase 2B 搜索/统计 | ✅ |
| Phase 2C Structure Signature | ✅ |
| P0 入库管线修复 | ✅ |
| OCR 链加固 | ✅ |
| provider_used 落盘 | ✅ |
| 英语 stem/选项 | ✅ 11/11 |
| 语文位置 | ✅ 23/24 |
| 数学 LaTeX 答案归一化 | ✅ 22/23 |
| 9 科答案 mismatch | ✅ 0 |
| 9 科严格通过 | ✅ 204/231 (88%) |
| Phase 2D | ⏸ 前置条件未满足 |

## 最近版本摘要

| 版本 | 关键内容 |
|---|---|
| 6.20 | 语文位置 23/24、膨胀检测材料题识别、物理 mimo-vl 重跑、pytest 648 passed |
| 6.17 | 数学 LaTeX 归一化、严格 16/23 → 22/23、9 科 204/231 |
| 6.14 | 语文重跑 19/24、独立题共享材料合并、9 科 187/213 |
| 6.12 | provider_used 落盘、Phase 2D 前置评估 |
| 6.11 | 英语 stem/选项 11/11、Q46 作文入库 |

## 当前状态

- 9 科答案基线：mismatch=0，严格通过 204/231 (88%)。
- 历史重跑进行中（东城，试修 Q37 缺库），完成后复算最终 9 科基线。
- 物理已用 mimo-vl 重跑：严格 11/20，选项 18/20，stem 18/20；paddle 401 已由 mimo 兜底。
- pytest：专用测试库 aitutors_test 下 648 passed；剩余 2 failed + 2 errors 为沙箱 temp。
- T0-2 key 轮换：用户决定暂缓，泄漏原 key 未轮换；步骤见 `bugs.md`。

## 数据与文档基线

- migration `20260821_0003`、`20260821_0005` 已执行。
- 知识树 333 节点、292 父子关系已入库。
- 文档治理 v6.21：`PROJECT_STATUS.md` 与 `RESTART_PROMPT.md` 只保留最新/稳定内容，
  历史统一归档到 `docs_archive/status/` 与 `LOG.md`。

## 当前焦点

1. 历史重跑验收（东城，试修 Q37）。
2. 9 科最终答案基线汇总。
3. 英语 Q46 `essay_manual_review` 验证改进。
4. T0-2 泄漏 API key 轮换（用户决定暂缓）。
5. 扩充样本 + 补齐 9 科 Structure Signature，条件满足后启动 Phase 2D。

## 历史与快照

- 完整变更历史：`LOG.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_PROJECT_STATUS_v6.20.md`
- 旧版完整快照：`docs_archive/status/2026-08-25_RESTART_PROMPT_v6.20.md`
