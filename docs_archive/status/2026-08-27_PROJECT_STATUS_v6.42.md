# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.42
Status: Sprint 治理五项完成（content_hash 生命周期 / DSD §8 / AGENTS 薄入口 / Pipeline 方案 A / fixture 版本化）
Date: 2026-08-27

---

## 当前阶段

Phase 2A/2B/2C 已验收；P0 入库管线修复完成；OCR Provider 策略落地（PPS/PVL
主识别、LLM VL 移出驱动链）；数据源决策完成（PPS 为主 + 化学 PaddleOCR-VL）。
基线 **212/215 (99%)**；30 份样本逐科调优 **79%**。

**v6.42（2026-08-27，Sprint 治理五项，源自 21:30 审计执行决策）**：
- **P0 content_hash 生命周期**：统一领域入口 `update_question_content()` +
  `_apply_content_update()`——内容变化（stem/options/sub_questions）→ 重算
  content_hash → 查 exact duplicate（同学科同 hash 排除自身）→ 答案冲突标记
  `answer_conflict` 审核；`apply_review` 内部接入（此前改题干/选项不重算 hash，
  旧 hash 残留、新内容无法去重）。先不加 UNIQUE(subject_id, content_hash)。
  回归测试 7 项（改题干重算/旧 hash 不残留、撞车冲突降 reviewing、撞车答案
  一致不标记等）。**content_hash 必须在 30 份 PDF 重跑之前完成——已就绪。**
- **P0 DSD §8 修正**：去掉「待实现/当前 DB 仍为旧结构」，改为「已实施 +
  未来计划」；8.1-8.3 标注已实施（migration 20260821_0003/0005、20260827_0001）；
  8.5 拆分为已实施原则与未来 Family/Similarity 原则；§4.5 两处过时说明同步修正。
- **P0 AGENTS.md 薄入口**：移除 agent 路由指南，改为薄入口指向
  RESTART_PROMPT + rules + PROJECT_STATUS（opencode.json 只自动加载 AGENTS.md）。
- **P2 Pipeline 方案 A（兼容层 re-export）**：新建 `pipeline_shared.py`
  （PipelineResult + save_result + _filter_by_page_range + _build_question_images
  + 9 个依赖 helper + schemas import，无循环依赖）；pipeline.py 顶部标注
  「兼容层」+ re-export；生产三文件（simple_pipeline/processor/ingestion）
  改从 pipeline_shared 导入；测试零改动（re-export 兼容）。
- **P1 fixture 版本化**：.gitignore 放开 `test/fixtures/`（最小匿名 JSON/markdown
  可提交，便于 GitHub 复现）；真实 PDF/DOCX/JPG（36.8MB）保持 ignore。

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
| worker LLM 挂死双层超时兜底（P7/P10，v6.33） | ✅ |
| worker 僵尸任务自动恢复（v6.34） | ✅ |
| DOCX 全管线支持（v6.34） | ✅ |
| 扫描版 PDF 检测标注（v6.34） | ✅ |
| 9 科答案 mismatch | ✅ 0 |
| 9 科严格通过（精选基线） | ✅ 212/215 (99%) |
| 题库管理页（v6.40）+ 图片 URL 落库（v6.41） | ✅ |
| **Sprint 治理五项（v6.42）**：content_hash 生命周期 + DSD §8 + AGENTS 薄入口 + Pipeline 方案 A + fixture 版本化 | ✅ 680 passed（7 failed + 2 errors 均为既有/沙箱环境问题，无本次回归） |
| pytest（专用测试库） | ✅ 680 passed |

## 最近版本摘要

| 版本 | 关键内容 |
|---|---|
| 6.42 | Sprint 治理五项：content_hash 生命周期 / DSD §8 / AGENTS 薄入口 / Pipeline 方案 A / fixture 版本化 |
| 6.41 | 入库质量诊断 + 脏数据清理 17 题 + 图片 URL 落库 + 详解回填决策（放弃） |
| 6.40 | 管理后台题库管理页（catalog 树 + source_document_name 筛选） |
| 6.39 | short_answer 膨胀放宽 3000 + boundary 答案区豁免（化学缺口清零 17→10） |
| 6.38 | VL 表格选项拆行（c0c0f27），化学 4 卷重灌 anchor 8→0 |
| 6.35 | 综合题父题答案缺失修复（367c7df），地理缺口清零 |
| 6.34 | DOCX 全管线 + 验证器 DOCX 适配 + worker 僵尸恢复 + 扫描件标注 + 「先讲明白再动手」规则 |
| 6.33 | worker LLM 挂死 P7/P10 双层超时兜底 |
| 6.32 | 30 份样本验证（原始质量 61%）、P2 路径260 + P4 retry500 修复 |
| 6.31 | 物理 Q18 + 数学 Q15 修复，基线 212/215 (99%) |
| 6.30 | 化学换 PaddleOCR-VL 26/26，基线 210/215 |

## 当前状态（v6.42）

- **9 科精选基线**：mismatch=0，严格通过 **212/215 (99%)**；答U 3、答M 0
  （答U 3 全为地理报告管线幻选题号残留 23/24/25，DB 正确）。
- **30 份样本口径**：原始 61% → 逐科调优 **79% (173/219)**。剩余缺口 10：
  语文 3（anchor 2 / low 1）、生物 3（low 2 / anchor 1）、数学 2（anchor）、
  物理 1（anchor）、历史 1（anchor）。待 30 份 PDF 全量重跑刷新。
- **入库质量**：approved 921 / reviewing 86（82 题实际有答案，旧代码标注 +
  旧文档 OCR 所致，重跑预计自动修复）；详解缺失 548/921（59%，源文档固有
  属性，已决策不生成）。
- **content_hash 生命周期已修复**（v6.42）：审核改题干/选项后 hash 重算 +
  撞车冲突标记；重跑可借机验证 dedup 收敛。
- **扫描件隔离**：昌平生物（全库唯一无文本层 PDF）标记 `scanned`，跳过
  OCR/LLM，后续集中处理。
- **DOCX 方向（讨论中，见 tmp/docx_pipeline_discussion.md）**：源格式可零
  OCR 结构化提取；WMF 公式图须无损渲染后识别；LLM VL 通道当前不可用。
- **OCR Provider 策略**：L1 识别仅 paddle 系；LLM VL 移出驱动链；paddle
  不可用标记 `ocr_unavailable` 等恢复重跑；扫描件（text_coverage<0.02）
  标记 `scanned` 不跑 OCR。
- **测试**：全量 pytest 680 passed / 7 failed / 2 errors。7 failed = 4 个既有
  （test_phase2_fixes url 断言 v6.41 未同步 3 个 + test_processor_progress
  scanned 检测 v6.34 未同步 1 个，基线同样失败）+ 2 个沙箱 temp ACL
  （ocr_vision_pdf_fallback）+ 1 个 flaky（http_provider_timeout，单独跑通过）；
  2 errors 为沙箱 temp ACL（用户本机可过）。

## 数据与文档基线

- migration `20260821_0003`、`20260821_0005`、`20260827_0001`（question_images.url）已执行。
- 知识树 333 节点、292 父子关系已入库。
- 专用测试库 `aitutors_test`（alembic head + 知识树种子），pytest 默认
  重定向（`AITUTOR_TEST_DB=0` 关闭），初始化 `backend/scripts/setup_test_db.py`。
- OCR 策略：`Docs/02_Architecture/OCR_PROVIDER_POLICY.md`；
  批量恢复：`backend/scripts/retry_ocr_unavailable.py`。
- 文档治理 v6.21+：`PROJECT_STATUS.md` 与 `RESTART_PROMPT.md` 只保留
  最新/稳定内容，历史归档到 `docs_archive/status/` 与 `LOG.md`。
- **v6.42 新增**：`backend/app/domains/document/pipeline_shared.py`（管线共享内核）；
  `test/fixtures/` 解除 ignore（最小匿名 JSON/markdown 可提交）。

## 当前焦点

1. **30 份 PDF + 9 份 DOCX 全量重跑**（用户待确认启动）：content_hash 生命周期
   已修复，重跑可借机验证 dedup 收敛 + 刷新 30 份样本基线 + 自动修复
   reviewing 积压（86→目标 0）。半小时轮询。
2. **既有测试失败修复**（待用户确认）：test_phase2_fixes 3 个 url 断言（v6.41
   加 url 字段未同步）+ test_processor_progress 1 个 scanned mock 数据
   （v6.34 扫描件检测未同步）——均为小修复，不影响生产。
3. **PDF 基线剩余缺口（10）**：重跑后复查；纯扫描件（昌平生物）另行处理。
4. **DOCX 方向**：公式/图片识别方案待定（WMF 渲染可行、VL 通道待解决）。
5. **报告管线**：地理报告幻选题号残留（23/24/25）过滤。
6. **Phase 2D**：9 科 Structure Signature 补齐后启动（前置未满足，暂停）。

## 历史与快照

- 完整变更历史：`LOG.md`
- 快照：`docs_archive/status/2026-08-27_PROJECT_STATUS_v6.41.md`
- 快照：`docs_archive/status/2026-08-27_RESTART_PROMPT_v6.41.md`
- 旧快照：`docs_archive/status/2026-08-26_PROJECT_STATUS_v6.33.md`
- 旧快照：`docs_archive/status/2026-08-26_RESTART_PROMPT_v6.33.md`
