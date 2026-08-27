# AI Tutor Personal Edition — PROJECT_STATUS

Version: 6.34
Status: DOCX 全管线支持 + 验证器 DOCX 适配 + worker 僵尸恢复 + 扫描件标注
Date: 2026-08-26

---

## 当前阶段

Phase 2A/2B/2C 已验收；P0 入库管线修复完成；OCR Provider 策略落地（PPS/PVL
主识别、LLM VL 移出驱动链）；**数据源决策完成**：PPS 为主（语文综合粒度
8/8、物理/历史/数学/生物/政治/英语/地理）+ **化学用 PaddleOCR-VL 26/26**。
基线 **212/215 (99%)**；30 份样本原始质量 **61%**（P2/P4/P7/P10 已修复，
逐科调优至 **79%**）。

**v6.34（2026-08-26）新增**：
- **DOCX 全管线支持**：python-docx 原生提取（段落+表格+Word 自动编号
  还原），.docx 跳过 OCR（零 paddle token）。9 科 DOCX 样本 e2e 62%
  （答案命中 90%、答M=0）。
- **验证器 DOCX 适配**：pdf_raw 误配修复、docx 答案格式解析（内联/管道
  表格/无表头双行/同行配对）、上标崩溃修复。
- **worker 僵尸任务自动恢复**：running 超时任务重置 queued。
- **扫描版 PDF 检测标注**：text_coverage < 0.02 → 标记 `scanned`，跳过
  OCR/LLM 后续集中处理（昌平生物隔离）。

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
| pytest（专用测试库） | ✅ 651+ passed |

## 最近版本摘要

| 版本 | 关键内容 |
|---|---|
| 6.34 | DOCX 全管线 + 验证器 DOCX 适配 + worker 僵尸恢复 + 扫描件标注 + 「先讲明白再动手」规则 |
| 6.33 | worker LLM 挂死 P7/P10 双层超时兜底（LLM 层 wait_for 600s + worker 任务级 3600s） |
| 6.32 | 30 份样本验证（原始质量 61%）、P2 路径260 + P4 retry500 修复、审计根因定位 |
| 6.31 | 物理 Q18 + 数学 Q15 修复，基线 212/215 (99%) |
| 6.30 | 化学换 PaddleOCR-VL 26/26，基线 210/215 |
| 6.29 | 化学 VL 验证 → 数据源决策完成，基线 210/215 |
| 6.28 | PPS 全科重跑、subject 传递修复 |
| 6.27 | PPS 数据补丁，基线 225/231 |
| 6.26 | OCR Provider 策略代码改造 |

## 当前状态

- **9 科精选基线**：mismatch=0，严格通过 **212/215 (99%)**；答U 3、答M 0
  （答U 3 全为地理报告管线幻选题号残留 23/24/25，DB 正确）。
- **30 份样本口径**：原始 61% → 逐科调优 **79% (173/219)**。剩余缺口：
  数学 6、化学 8、生物 4、物理 3、语文 5、地理 3、历史 1（政治 0）。
- **扫描件隔离**：昌平生物（全库唯一无文本层 PDF）标记 `scanned`，跳过
  OCR/LLM，后续集中处理（拿源文件/换识别引擎/按文档顺序锚定）。
- **DOCX 方向（讨论中，见 tmp/docx_pipeline_discussion.md）**：DOCX 是
  源格式，文本/表格/OMML 可零 OCR 结构化提取；WMF 公式图（数学 docx
  271 张）须无损渲染后识别；当前 LLM VL 通道不可用（deepseek 不支持
  图片、mimo 无图片端点）。待后续定方案。
- **数据源决策**：PPS 为主 + 化学用 PaddleOCR-VL（上下标/表格质量最优）。
- **OCR Provider 策略**：L1 识别仅 paddle 系；LLM VL 移出驱动链；paddle
  不可用标记 `ocr_unavailable` 等恢复重跑；扫描件（text_coverage<0.02）
  标记 `scanned` 不跑 OCR。
- pytest：专用测试库 aitutors_test 下 651+ passed；剩余 2 failed + 2
  errors 为沙箱 temp ACL（用户本机可过）。

## 数据与文档基线

- migration `20260821_0003`、`20260821_0005` 已执行。
- 知识树 333 节点、292 父子关系已入库。
- 专用测试库 `aitutors_test`（alembic head + 知识树种子），pytest 默认
  重定向（`AITUTOR_TEST_DB=0` 关闭），初始化 `backend/scripts/setup_test_db.py`。
- OCR 策略：`Docs/02_Architecture/OCR_PROVIDER_POLICY.md`；
  批量恢复：`backend/scripts/retry_ocr_unavailable.py`。
- 文档治理 v6.21+：`PROJECT_STATUS.md` 与 `RESTART_PROMPT.md` 只保留
  最新/稳定内容，历史归档到 `docs_archive/status/` 与 `LOG.md`。

## 当前焦点

1. **PDF 基线剩余缺口（79% → 目标）**：化学同号题锚定冲突（最独立）、
   数学 Q19 膨胀+双卷、地理缺库 5 题、各科 free_text/证据类缺口。
2. **扫描件后续**：昌平生物拿源文件或更好 OCR 方案后重新处理。
3. **DOCX 方向**：公式/图片识别方案待定（WMF 渲染可行、VL 通道待解决）。
4. **报告管线**：地理报告幻选题号残留（23/24/25）过滤。
5. **Phase 2D**：9 科 Structure Signature 补齐后启动（前置未满足，暂停）。

## 历史与快照

- 完整变更历史：`LOG.md`
- 快照：`docs_archive/status/2026-08-26_PROJECT_STATUS_v6.33.md`
- 快照：`docs_archive/status/2026-08-26_RESTART_PROMPT_v6.33.md`

## 历史与快照

- 完整变更历史：`LOG.md`
- 快照：`docs_archive/status/2026-08-26_PROJECT_STATUS_v6.33.md`
- 快照：`docs_archive/status/2026-08-26_RESTART_PROMPT_v6.33.md`

### 2026-08-26 20:16:00（v6.35）

- **综合题父题答案缺失修复（367c7df）**：育英地理重灌 14/14 approved，
  0 answer_missing。根因：LLM 把答案写在 sub_questions 而父题 answer 为空，
  answer_matcher 纯字母校验清空汇总答案 → 误报 answer_missing。
  修复：content_slicer 从子题汇总构建父题答案、answer_matcher/ingestion
  跳过选择题组综合题单题覆盖。新增 5 单测，全量回归 651 通过。
- **地理基线缺口收窄**：地理（育英）9 题 anchor_uncertain + 7 题 answer_missing
  全部清零 → 地理基线缺口从 3 降至 0（30 份样本口径地理 3 缺口已消）。

### 2026-08-26 23:52:00（v6.38）

- **VL 表格选项拆行（c0c0f27）**：化学 4 份卷重灌，表格选项题 anchor_uncertain
  8→0，全库缺口 26→17。剩余：化学 7（解答题 low_confidence/missing）、
  语文 3、生物 3、数学 2、物理 1、历史 1。
- **缺口性质变化**：anchor_uncertain 类缺口基本清零（只剩语文 2/数学 2/物理 1/
  生物 1/历史 1 零星），主体转为解答题质量类（low_confidence 8 / answer_missing 3）。

### 2026-08-27 00:01:00（v6.39）

- **化学缺口清零（47b2b64）**：short_answer 膨胀放宽 3000 + boundary 答案区豁免，
  4 份化学卷重灌 reviewing 全 0，全库缺口 17→10。
- **剩余缺口**（10）：语文 3（anchor 2 / low 1）、生物 3（low 2 / anchor 1）、
  数学 2（anchor）、物理 1（anchor）、历史 1（anchor）。
- **待决**：30 份 PDF + 9 份 DOCX 全量重跑（用户确认中）——本轮 3 项全局管线
  改动（表格拆行/膨胀放宽/答案区豁免）已逐份验证，全量重跑可刷新 30 份样本基线
  并观察 DOCX 管线实际执行。

### 2026-08-27 07:20:00（v6.40）
- **管理后台「题库管理」页面上线**：`/admin/questions` 目录树（学科→年级→题目数）+
  题目列表（状态/学科/题型/难度/置信度）+ 点击展开详情 + 文档「入库」入口；
  后端新增 `GET /api/admin/catalog`、`source_document_name` 筛选、序列化补学科/题型名称。
- **前端运行方式**：vite dev server（`localhost:5173`，proxy /api → 8000）；沙箱内需
  danger-full-access 启动（esbuild 子进程 spawn 限制）。
- **已知缺口**：入库图片仅存 image_id 无 URL，详情页暂显配图标识，实际渲染待后端图片服务。

### 2026-08-27 08:15:00（v6.41）
- **入库质量诊断**：详解缺失 59%（548/921）、reviewing 86 题（82 题有答案，锚点/置信度问题为主）、
  图片无 URL（历史 URL 过期，增量落库已加 url 列）。
- **已完成**：前端 subject 参数 bug 修复；17 题脏数据清理（图片残留/选项混入）；
  图片 URL 落库（migration 20260827_0001）+ 前端渲染。
- **进行中**：LLM 批量回填 548 题详解（47 文档逐文档提取）；reviewing 积压等 30 份 PDF 重跑自动修复。

### 2026-08-27 08:40:00（v6.41 补充）
- **详解回填已放弃**：实测 47 文档逐文档提取需 2+ 小时且命中率极低（43 题仅 2 题有详解）——
  教师版试卷答案区大多只有答案无详解，属源文档固有属性。用户决策接受现状。
- **reviewing 86 题**：82 题实际有答案，主因旧代码标注 + 旧文档 OCR；等 30 份 PDF 全量重跑自动修复。
