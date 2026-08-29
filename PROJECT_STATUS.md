# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.46
Status: v6.46 题型树+知识节点库完成；Phase 1-3 全量修复；752 passed（8 skipped）。
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

## 题型树（2026-08-29）

- `question_types` 表新增 `level`/`description`/`keywords` 字段（migration 20260829_0004）。
- 种子数据 229 个节点，覆盖九科（全国卷+北京卷统一池），3 级层级（L1 大题型 → L2 子类 → L3 细粒度）。
- Seed 脚本 `question_type_seed/seed.py`（idempotent），写入 level/description/keywords。
- API 端点 `GET /api/admin/question-types`，返回树形 JSON。
- 测试：6 项种子完整性测试（parent_code 有效、无重复 code、层级正确）。

## 知识节点库（2026-08-29）

- **统一为 v2 课标教材体系**：917 个节点，九科全覆盖，L2(课程模块)→L3(章)→L4(知识点)。
- v1 知识树（333 节点，考试能力分类）的关键词已全部合并到 v2 节点，index_builder 仅引用 v2。
- `index_builder.py` 清理完毕：零 v1 引用，5010 个关键词（小写去重）。
- 对抗性审查修复：移除 ENG-LEXA 上的题型关键词（cloze/七选五/完形）；补充"排列组合""电解""reading comprehension""函数单调性"等常用搜索词。
- 数据来源：用户提供《高考九科知识点树状清单》（2026 课标教材体系）。
- 与题型树正交：题型 = 怎么考，知识点 = 考什么，每道题同时标注两者。

## 题型树文档（2026-08-29）

- 新增 `Docs/00_Requirements/QUESTION_TYPE_TREE.md`：记录全国新高考九科题型树与北京高考 2026 题型清单。
- 待补充：北京卷后续细分题型；该文档将作为题型分类与题库展示的基础。

## 验收遗留项（2026-08-29）

- P2-2 前端纯函数已补 Node 原生测试，`npm test` 5 passed。
- P0-4 `_build_answer_structure` 独立测试已补强边界。
- 化学式完整 pipeline 集成测试已存在并通过。

## 文档治理审计（2026-08-29）

- **归档 5 份**：PLAN_QUESTION_FAMILY、T3_IMPLEMENTATION、TASK、Design → docs_archive/2026-08-29/；LOG.md 历史部分（2006 行）同目录归档。
- **整合**：TASK.md 内容并入 ROADMAP v3.0（完成标准 §4 + 试卷结构门禁 §5）。
- **精简**：LOG.md 3115→1118 行；docs/ 从 18 份→14 份（全部为规则/规划/契约类）。
- **清理**：experiment_output.md → tmp/；删除 Codex 误生成空文件。
- **更新**：rules.md 导航表、RESTART_PROMPT.md v6.46。
- 详见 LOG.md `2026-08-29 20:00:00` 条目。

## Codex 审计修复（2026-08-29）

- **问题 1 修复**：`setup_test_db.py` 接入 `seed_question_types`，测试库初始化自动落库题型树。
- **问题 2 修复**：补充北京卷特有题型 18 个（语文 3 + 数学 4 + 英语 6 + 化学 1 + 生物 2 + 物理 2），总计 229→247。
- **问题 3 修复**：`english_v2.py` 移除"七选五"；新增 `test_knowledge_tree_integrity.py` 防御性测试。
- **问题 4 修复**：关键词计数从5012 修正为5010（小写去重）。
- 详见 LOG.md `2026-08-29 21:00:00` 条目。

## 测试文件治理审计（2026-08-29）

- **删除 ~450 个文件**：backend/scripts/_tmp_*（26）、test/scripts/_*（64）、test/results/*.py（32）、test/results 日志（150+）、test/scripts 孤立脚本（33）、tmp/（707）。
- **保留**：backend/tests/ 72 个（758 测试）、frontend/tests/ 1 个、test/scripts/ 15 个活跃脚本。
- 753 passed，零回归。详见 LOG.md `2026-08-29 22:00:00`。

## 代码治理审计（2026-08-29）

- **删除 62 个文件（-7234 行）**：v1 tree_seed 7 个（DEAD）、celery_app.py（DEAD）、一次性数据修复脚本 36 个（ONE_SHOT）、阶段验证脚本 18 个（ONE_SHOT）。
- **保留决策**：parser.py/question_extractor.py（DEPRECATED，有回归测试保护）、pipeline.py（兼容层，17+ 测试引用）、占位域骨架（未来功能）、3 个活跃工具脚本。
- **对抗性审查通过**：全部生产模块 import 正常、753 passed 零回归、v1 别名正常工作、已删除脚本无活跃引用。
- **遗留修复**：OCR_PROVIDER_POLICY.md 已更新删除的脚本引用。
- 详见 LOG.md `2026-08-29 23:00:00`。

## 对抗性审查遗留修复（2026-08-29 18:59:31）

- commit 3bcf49d：docker-compose worker 修复、DSD/ACS 文档补齐、pipeline.py 注释 17→16。
- `validate_docs_vs_code.py` 退出码 0。
- 本次仅补录 LOG/PROJECT_STATUS 记录。
- 详见 LOG.md `2026-08-29 18:59:31` 条目。

## 状态同步（2026-08-29 20:31:16）

- HEAD c8d81e2；f4e7ac0 + 7abe2e0 + c8d81e2 已完成对抗性审查后续修复。
- 当前测试：743 passed + 5 failed（e2e 目标文档缺失）+ 8 skipped；validate_docs_vs_code ok。
- 下一主任务：P4E.1 任务 4 测试门禁；前置恢复 test/results/golden 与 e2e 目标文档。
- 待清理：test/results_to_delete/pytest-of-Kurtw（PID 6408 锁定）。

## P4E.1 任务4 测试门禁（2026-08-29 20:59:00）

- 真实库已恢复 `2026北京二中高一（上）期末数学（教师版）.pdf` e2e 文档，23 题入库。
- golden 门禁新增：子题数、子题 `options_line_ids`、选项完整性；golden overall <80% 直接 FAIL。
- 全量 pytest 752 passed + 8 skipped；e2e 9 passed。
- 待办：P4E.1 任务5 三份验证文档重跑；`test/results_to_delete/pytest-of-Kurtw` 锁定残留清理。

## 题目展示与切片契约固化（2026-08-29 21:38:34）

- `Docs/00_Requirements/DISPLAY_CONTRACT.md` v0.4 已固化。
- 当前契约覆盖英语、语文、理科；后续实现将按此契约调整 golden、pipeline、API 与前端。
- 同步更新 `RESTART_PROMPT.md`、`rules.md`、`DICTIONARY.md`。
- 详见 LOG.md `2026-08-29 21:38:34` 条目。
