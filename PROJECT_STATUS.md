# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.45
Status: v6.45 Phase 2/3 修复完成；P0-2/P1-3/P1-4/P2-2/P0-5/P1-2 已回归通过；P2-1 保持题干区现状；下一步 Phase 4 验收。
Date: 2026-08-29

---

## 当前阶段

Phase 2A/2B/2C 已验收；OCR Provider 策略落地；Sprint 治理五项完成。

**v6.45（2026-08-28，切片入库规则差距修复，用户第三次提供展示标准）**：
- **差距 1 修复**：fill_in/short_answer 综合题父题答案未汇总（Q11=`itself`、Q21=`confusing`、
  Q42 只留第一题答案）→ 根因是 `answer_matcher.match_answers` 主循环只跳过
  choice 类综合题，P4E.1 只修了 `_apply_llm_annotation_answers`。已修：所有
  is_composite 且父题已有汇总答案的一律跳过单题匹配。验证：`(11) itself (12) to
  (13) to stay` 保留。
- **差距 2 修复**：七选五选项错位（B 丢/D 吞 E/E/F/G 错位/G 落 section 标题）→
  4 处修复：`_INLINE_LABEL_RE` A-G、l1_postprocessor 拆行 A-G、子题 options 锚点
  校验、合并行行内归属不误判 retry。验证：Q37 选项 A-G 完整、D/E 正确分离。
- **差距 3 修复**：空位标记 → 规则 1.5 下划线空位 `____37____`→`〔37〕`、子题 stem
  也标记、subject 兜底。验证：`〔37〕` 父题/子题均高亮。
- **异步富化（新方向，用户确认）**：理科选择题大部分无详解（源 PDF 教师版答案区
  只有「题号+答案」表，八中数学 Q1-10 无【详解】），需入库后 LLM 异步生成详解并
  写回 `questions.explanation` 标记 `llm_fallback`——**当前无实现，待新会话设计**。
- **测试**：改动范围 129 passed；新增 7 项回归测试（含七选五端到端链路）。
- **存量数据未重跑**：东城英语（fd6a575a）Q11/21/42 父题答案截断、Q37-41 选项
  错位、空位缺失——代码已修，重跑约 ¥0.5-1，用户暂缓。

## 关键验收

| 项 | 状态 |
|---|---|
| Phase 2A 总验收 | ✅ |
| Phase 2B 搜索/统计 | ✅ |
| Phase 2C Structure Signature | ✅ |
| OCR Provider 策略（PPS/PVL 主识别、LLM VL 移出驱动链） | ✅ 651 passed |
| P4E.1 任务 1/2/3（子题链路/紧凑选项/父题不拼接） | ✅ 52 题入库验证 |
| 前端展示重构（空位高亮/折叠/格式化） | ✅ |
| **v6.45：fill_in/short_answer 综合题父题答案汇总** | ✅ 端到端验证 |
| **v6.45：七选五 A-G 选项完整性（含合并行）** | ✅ 端到端验证 |
| **v6.45：空位标记（下划线/子题/裸数字）** | ✅ 端到端验证 |
| **异步富化（理科选择题详解）** | ⏳ 未实现，待设计 |
| **P4E.1 任务 4（测试门禁）** | ⏳ 未启动 |
| pytest（专用测试库） | ✅ 改动范围 129 passed（全量挂起/失败均为沙箱 ACL） |

## 当前状态（v6.45）

- **代码修复完成**（5 个文件）：`answer_matcher.py`（主循环跳过所有有汇总答案的
  composite）、`anchor_corrector.py`（子题选项锚点校验 + 合并行行内归属）、
  `content_slicer.py`（A-G 行内拆分、下划线空位规则 1.5、子题 stem 标记）、
  `l1_postprocessor.py`（行内拆行 A-G）、`simple_pipeline.py`（subject 兜底 +
  retry hints 覆盖子题选项）。
- **存量数据待重跑**：东城英语文档（Q11/21/42 父题答案、Q37-41 选项、空位标记）。
- **异步富化待实现**：理科选择题详解（用户确认方向：入库后 LLM 异步生成）。
- **服务状态**：8000（uvicorn）与 5173（vite）当前未监听（会话收尾已停）。

## 数据与文档基线

- migration `20260821_0003/0005`、`20260827_0001` 已执行；知识树 333 节点。
- 专用测试库 `aitutors_test`（`AITUTOR_TEST_DB=0` 关闭）。
- 文档治理快照模式：v6.44 已归档 `docs_archive/status/2026-08-28_*_v6.44.md`。
- `D:\Project\Papers` 是批量导入源（maintainess 整理集 + 高一/高一上/高二/高三原始集）。
- V2 `backend\.env`：DEEPSEEK_API_KEY 已换新（已验证）；V1 遗留 v4-pro 强制 +
  explain_queue 6 任务待处理。

## 当前焦点

1. **Phase 1 数据契约**：已完成（P0-1/P0-3/P0-4/P1-1），下一步进入 Phase 2。
2. **Phase 2 英语**：已完成（P0-2/P1-3/P1-4/P2-2；P2-1 保持题干区现状），下一步 Phase 3 理科。
3. **Phase 3 理科**：已完成（P0-5 化学式标准化、P1-2 答案图子题绑定）。
4. **Phase 4 验收**：新增回归测试 + golden + 重跑东城英语/样本卷。
5. **异步富化**（暂缓）：待题型/答案结构修复稳定后重新设计。
6. **批量导入（P4E.2）**：修复验收后按 清单 → 30 份 → 100 份 → 全量推进。

## 审核锁定（v3.1，2026-08-28）

对用户提供的英语/理科切片入库展示标准完成对抗性审查并锁定结论：

- P0：P0-1 细粒度题型/section 入库丢失、P0-2 写作题无 canonical 类型、P0-3 多层嵌套子问不支持、P0-4 结构化答案格式缺失（条件化）、P0-5 化学式下标/上标标准化。
- P1：P1-1 词库无独立 word_bank 字段、P1-2 答案图子题粒度绑定不精确、P1-3 完形共享材料数字误标、P1-4 七选五 A-G 完整性无强制校验。
- P2：P2-1 instruction 独立字段（当前行为不算错误）、P2-2 七选五正确选项高亮/自动关联文本展示增强。
- 已排除/降级：答案表空格、词库完全无支撑、答案图完全无支撑、数字误标全面风险等 v1 误判已修正。

## 修复计划（v3.1）

Phase 1 数据契约：全部完成（P0-1/P0-3/P0-4/P1-1），含细粒度题型、section、递归子问、answer_structure、word_bank。
Phase 2 英语：已完成（P0-2/P1-3/P1-4/P2-2；P2-1 保持题干区现状）。
Phase 3 理科：已完成（P0-5 化学式标准化、P1-2 答案图子题绑定）。
Phase 4 验收：新增回归测试 + golden + 重跑东城英语/样本卷。

## 历史与快照

- 完整变更历史：`LOG.md`
- 快照：`docs_archive/status/2026-08-28_PROJECT_STATUS_v6.44.md`
- 快照：`docs_archive/status/2026-08-28_RESTART_PROMPT_v6.44.md`
- 快照：`docs_archive/status/2026-08-27_PROJECT_STATUS_v6.42.md`

## Phase 2 状态（2026-08-29）

- P0-2：essay/writing 题型映射、prompt、入库 get-or-create 与测试完成。
- P1-3：普通数字上下文保护完成，ages/year/date/page/range/percent 不误标。
- P1-4：七选五 A-G 缺失生成 sub_options retry，质量门阻断并生成重试提示。
- P2-2：前端正确选项高亮，答案区自动关联选项文本。
- 对抗性审查修复：P1-3 百分号误标封堵、P1-4 缺 sub_questions retry、P2-2 多答案高亮与共享工具。
- P2-1：指令文本仍保留在题干区，符合当前展示标准，暂不新增 instruction 字段。
- 验证：后端 739 passed（5 failed 仅为已知 e2e 目标文档缺失），前端 npm run build 通过。
- 下一步：Phase 4 验收（golden + 重跑东城英语/样本卷）。

## Phase 3 状态（2026-08-29）

- P0-5：化学式标准化已接入 ingestion/pipeline/simple_pipeline；支持 Cl₂、OH⁻、Fe₂O₃、Fe³⁺、Mg(OH)₂ 等常见 OCR 形态。
- P1-2：question_images.sub_question_qno 已落库，答案图按空间邻近绑定到子题，API/前端按子题过滤展示。
- 验证：后端 746 passed（5 failed 仅为已知 e2e 目标文档缺失）；前端 npm run build 通过；真实库与测试库均升级到 20260829_0003。

## 题型树文档（2026-08-29）

- 新增 `Docs/00_Requirements/QUESTION_TYPE_TREE.md`：记录全国新高考九科题型树与北京高考 2026 题型清单。
- 待补充：北京卷后续细分题型；该文档将作为题型分类与题库展示的基础。

