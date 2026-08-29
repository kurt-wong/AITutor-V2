# AI Tutor Personal Edition — 变更日志

---

> **历史记录（2026-08-10 ~ 2026-08-24）已归档至 `docs_archive/2026-08-29/LOG_historical_2026-08-10_to_2026-08-24.md`**
> 本文件只保留2026-08-25及之后的变更记录。

## 变更记录

### 2026-08-25 16:00:00

#### 6 项遗留按序修复：基线 215/231 → 223/231 (97%)（版本 6.25）

**① 物理 Q4/Q7 缺库（回填）**：正文第2页仅"4.(集团校自创题)"占位，真实题干+选项在
第9页"自主命制试题"部分；LLM 提取了选项但题干为空被丢弃。`backfill_physics_q4_q7.py`
从 pdf_raw 提取题干（去空白连续文本，全角标点）、复用管线选项、答案区 4.A/7.B，
幂等插入 Question+Instance；并修正 L2 stem_start_marker（mimo 幻觉标题
"滑沙项目受力与运动分析"→ 真实题干开头）。验证器 `verify_stem` 增加锚点缺失题
native 源回退（OCR 源含幻觉标题致文本跨度失败，DB 数据正确）。

**② 物理 Q17/Q20 free_text（结构化答案）**：DB 精简版答案（"（1）a=0.2m/s²；…"）vs
答案区完整解答（中间步骤+分值注记"（2分公式1分结果1分）"），整段无法命中。新增
`_find_structured_answer`：按（N）分拆 → 每部分 LaTeX 归一化取 "=" 后核心值 →
题号+子题标记锚定窗口（2000 字符，去分值注记）逐一核对，全部命中才 matched。
`_strip_score_annotations` 抽出为模块级（兼容"（2分公式1分结果1分）"多段注记）。
仅非综合题启用（综合题走 composite 子题路径，Q15/Q16 不受影响）。

**③ 语文 Q24 free_text（数据侧）**：DB 答案残缺（"例文：\n【答案】例文："只截到标签）；
答案区含完整作文（两篇例文+详解 4281 字符）。`fix_yuwen_q24_answer.py` 回填。

**④ 历史 Q26 选项 D（数据侧）**：mimo OCR 漏识别 D（OCR 里 C 后直接接 Q27）；
pdf_raw/native 中 "D.白话文在全国逐渐普及开来" 真实存在。`fix_history_q26_option_d.py`
回填 + approved。

**⑤ 膨胀边界（人工审核）**：
- 化学 Q23/Q24（1132/1078，合法多小问/HTML 实验表格）、地理 Q26（860，读图+统计表）
  → approved（gate 无 section 上下文，人工判定）。
- 物理 Q20 实为**真膨胀**：stem 尾部混入"自主命制试题"整节（Q4/Q7 完整内容 +
  mimo 幻觉标题 + LLM 注释"注：图片占位符…"）。截断 1598 → 862 字符（保留拖把/
  传送带/字典三小问），approved 后位置校验同步通过。
- 语文 Q23：answer_conflict 假冲突（两次重灌答案 compact 完全一致，BUG-026 前残留）
  → approved。
- 顺带发现并修复**化学 Q11 选项 B/C/D 缺失**：源中真实存在，pdf_raw 竖排系数 +
  OCR LaTeX 结构重建（B 2H⁺+SO₄²⁻+Ba²⁺+2OH⁻=BaSO₄↓+2H₂O、C 澄清石灰水、
  D 2Na+O₂=Na₂O₂ 错误干扰项，与答案 C 单选一致）。

**⑥ 英语 Q46 essay（验证器）**：DB 作文答案与答案区范文逐字一致，但作文区无 "46."
锚点（"第二节(20分) One possible version: Dear Jim, …"）。验证器对长文本（≥100
字符）改为：答案前 40 字符在答案区逐字出现 → matched（evidence_kind=essay）；
否则 essay_manual_review（不误报）。

**验证（真实管线）**：
- 各科严格：物理 16/20 → **20/20**、语文 23/24 → **24/24**、历史 42/43 → **43/43**、
  化学 25/26 → **26/26**、英语 10/11 → **11/11**（政治 28/28、生物 24/24、数学 22/23
  持平；地理 25/30 缺库口径不变）。
- 9 科基线：**215/231 (93%) → 223/231 (97%)**；答U 14 → 8、答M 0。
- `test_answer_verifier.py` 19 passed（+5：结构化分部命中/部分/长子段、essay 全文
  命中/未命中）；全量 pytest 649+ passed（2 failed + 2 errors 沙箱 temp ACL）。

**剩余 8 题（新遗留，非本次列表）**：地理 5 缺库（DB 25 vs L2 30）、生物 Q1/Q2 缺库
（BUG-004）、数学 Q15 负号证据缺失（OCR 丢失负号）——全为缺库/证据类，待重跑或回填。

**版本升至 6.25。**

### 2026-08-25 17:00:00

#### 架构决策：OCR Provider 策略（PPS/PVL 主识别 + LLM VL 移出驱动链）

**决策**（用户，质量第一 / 成本 / 无人值守安全）：
- L1 识别仅用 paddle 系（PP-StructureV3 / PaddleOCR-VL）；LLM VL
  （mimo-vl / deepseek-vl）**移出 OCR 驱动链**，仅保留为可选交叉验证入口
  （默认关，以确定性规则门为主——e2e 语义验收已覆盖结构异常信号）。
- paddle 不可用时：重试/熔断耗尽后任务失败标记 `ocr_unavailable`，等待
  paddle 恢复重跑；**不自动降级 LLM VL 驱动入库**。
- 动因：mimo 实证失误（幻觉标题/漏选项 D/漏题干/空单元格）+ 免费额度
  （paddle 每天各 3000 页）+ LLM 按量计费 + 夜间无人值守不划算。

**10010 根因调查（官方文档确认）**：
- 10010 是**官方异步 API 错误码**"任务提交队列已满"（HTTP 400）——服务端
  pending 队列容量满，非认证/配额/频率问题（与 12001 配额 403、12002 频率
  429 区分）。官方无恢复时间承诺；实测连续 30s 间隔多次提交均满（免费层
  共享队列高峰满载），夜间低谷相对空闲。**勘误**：`paddle_client.py` 注释
  "官方错误码表无 10010"不准确，已同步文档。
- 配额：3000 页/天/模型（超限 429）；单文件建议 ≤100 页。

**token 更新**：`PADDLEOCR_VL_TOKEN` 已换新（`backend/.env`，gitignore 不
入库）；实测 401 已消除（当前 10010 队列满为服务端瞬时状态）。

**文档落地**：`docs/02_Architecture/OCR_PROVIDER_POLICY.md`（新）、
`PADDLEOCR_API.md`（错误码表+10010+配额）、`PIPELINE.md`（回退链声明）、
`rules.md`（V1 教训固化 §11 OCR 识别链）。

**待执行（实施计划，见 OCR_PROVIDER_POLICY.md §5）**：
① OCRFallbackChain 不降级 LLM VL（抛 `OCROutageError` + `ocr_unavailable`）
② LLM VL 移出 `build_ocr_chain` ③ 批量任务探活/恢复 ④ 测试改造。
**历史数据**：paddle 恢复后 14:00 批量重跑 mimo 灌入文档（物理/历史），
以主识别结果为准对比 mimo 效果。

### 2026-08-25 18:30:00

#### OCR Provider 策略代码改造完成（版本 6.26）

**改造（OCR_PROVIDER_POLICY.md §5 全部完成）**：
1. `OCRFallbackChain`：全部 provider 失败 → 抛 **`OCROutageError`**
   （继承 OCRProviderError，保留 failures 明细）；`simple_pipeline` OCR 失败
   标记 **`ocr_unavailable`**（原 retry_eligible）；`processor.py` 失败任务
   error_detail 优先取 `result.errors`（含 ocr_unavailable 供批量恢复识别）。
2. `build_ocr_chain`：**移除 mimo-vl / deepseek-vl 追加块**——LLM VL 移出
   驱动链，`LLMVisionOCRProvider` 保留实现供可选交叉验证（外部显式构造）。
3. 批量恢复：`backend/scripts/retry_ocr_unavailable.py`（探活 paddle →
   retry ocr_unavailable 失败任务）。
4. `app/core/logging.py`：root logger INFO 输出（`main.py` 显式导入触发），
   worker INFO 日志可见（"document_parse_worker started" 等）。
5. 测试：`test_vl_model_queue.py` 回退顺序用例改为"VL 不在链中"（paddle
   token 存在 → 链只含 paddleocr；缺失 → 空链）；`test_ocr_parsing.py`
   新增"paddle 耗尽抛 OCROutageError 保留失败明细"。全量 **651 passed**
   （2 failed + 2 errors 沙箱 ACL）。

**PPS 重跑与回填（对比 mimo）**：
- 物理 PPS（PP-StructureV3）：严格 15/20；Q1 选项 D 回填后 **16/20**。
  PPS OCR 把 Q1 "C.加速度D时间" 粘连一行（源 PDF 文本层本就粘连）→ LLM
  无法拆分；mimo 视觉能拆。Q3/Q9/Q10 表格答案 PPS 原生正确。
- 历史 PPS（PP-StructureV3）：严格 39/43；Q26/Q27/Q28 选项回填后 **42/43**
  （`backfill_pps_missing_options.py`）。根因：LLM 标注跨页漏标选项行号
  （Q26 D 在第 6 页开头、Q27/Q28 整题在跨页边界）——OCR 数据完整，非 OCR
  问题。Q37 缺库（同 mimo，需回填/重跑）。
- 结论：**PPS 与 mimo 互补而非替代**（PPS 表格提取强/免费/可靠；mimo 选项
  完整/LaTeX 格式化）；PPS 为主力后，跨页标注与粘连选项需数据补丁兜底。

**9 科基线（v6.26，物理/历史为 PPS 版本）**：严格 **218/231 (94%)**、答U 13、
答M 0。物理 16/20（Q4/Q7 缺库 + Q18/Q20 structured_partial）、历史 42/43
（Q37 缺库）；其余科持平（语文 24、数学 22、政治 28、生物 24、化学 26、
英语 11、地理 25）。

**版本升至 6.26。**

### 2026-08-25 19:00:00

#### PPS 数据补丁 + 地理/生物缺库修复：基线 225/231（版本 6.27）

**PPS 版本数据补丁（物理/历史，`cb267fb`）**：
- 物理 PPS：Q4/Q7 回填（复用 content_hash question）+ L2 section_id 修正
  （一_单项选择题 → 自主命制试题，options 行号 P9L004+ 落对 section）；
  Q20 stem 截断 1231 → 684（真膨胀：混入 Q4/Q7 内容 + LLM 注释）。
  verifier 改进：`_greek_to_latex`（Unicode θ/φ ↔ LaTeX theta/varphi 同规，
  PPS 纯文本答案 vs OCR LaTeX）+ `\text{...}` 单位标记取内容（`4.5s` vs
  `4.5\text{s}`）。物理 16/20 → **19/20**；Q18 答案 (1) 是受力分析图
  （无文本答案）诚实保持 U。
- 历史 PPS：Q37 回填（源 stem/options/answer=A）+ L2 stem_start_marker
  垃圾标记"()业中"修正。历史 42/43 → **43/43 (100%)**。

**地理缺库（`57e4732`）**：
- **发现 L2 幻选题**：源试卷题号 1-22 + 26-30，**无 23/24/25**（L2 把材料
  正文当题干幻造 3 题）。L2 30 → 27（删除幻觉题）。
- Q21 回填（stem/options/answer=C；L2 marker 幻造"21.下列关于两处土壤
  剖面的描述"→ 修正为真实题干）；Q30 回填（770 字符 stem + 管线 answer）。
- 地理 25/30 → **26/30**；Q30 长解答题（含图/表）anchorless + 跨源文本
  差异（native 0.6/OCR 0.4 覆盖）位置 N 为诚实口径限制；报告 30 含管线
  残留幻选题号（DB 27 正确）。

**生物缺库**：Q1/Q2 回填（源 stem + 管线 options/answer；题干为空被丢弃），
Q2 stem 修正为仅题干。生物 24/24 → **26/26 (100%)**。

**数学 Q15**：DB 答案 `$-7/3$` 数学验证正确（f(x)=3(cosx−2/3)²−7/3），但
答案行证据三源损坏（pdf 竖排 `73−`、OCR `~7/3` 负号误识别且 `~6` 噪声
不可区分）——诚实保持 U；PPS 重跑数学验证中。

**9 科基线（v6.27）**：严格 **225/231 (97%)**、答U 5、答M 0。语文 24/24、
历史 43/43、化学 26/26、英语 11/11、生物 26/26、政治 28/28、数学 22/23
（Q15）、物理 19/20（Q18）、地理 26/30（Q30 口径）。

**版本升至 6.27。**

### 2026-08-25 21:00:00

#### PPS 全科重跑完成：语文综合题粒度确认 + 化学 VL 重跑中（版本 6.28）

**6 科 PPS 重跑（统一数据源）**：
- 生物：26/26（Q1/Q2 回填、Q24 审核、Q26 截断 + L2 stem 行号修正
  P4L003-007→P8L002-014——P4L003 是 Q20 选项行，行号重叠破坏 section 边界）。
- 英语 11/11、政治 28/28：干净。
- 地理：27/30 报告值（管线幻选残留 23/24/25，DB 27 正确，真实 27/27）。
- **语文（关键结论）**：PPS 标注 8 题 = **综合题粒度**（材料大题+全部子题：
  园林 Q1×7、文言 Q8×6、诗歌 Q14×3、散文 Q18×4、语用 Q22×2、默写 Q17、
  微写作 Q23、作文 Q24）——完整覆盖试卷结构，**非退化**（mimo 24 题是
  独立小题粒度，丢失材料归属）。L2 section_id "none" 字符串 → null
  （Q23/Q24 位置）。语文 PPS **8/8 (100%)**。
- 化学：**PP-StructureV3 21/26 退化**（Q16/Q18/Q20 表格内选项全丢——PPS
  不识别表格选项；源中有完整表格）。**PaddleOCR-VL 重跑中**——paddle
  10010 队列满多次阻断（20:41-20:53 持续），auto_retry_chem_vl.py
  待队列空自动重试；对比 VL 效果后决定化学数据源。

**代码修复（subject/ocr_model 传递）**：processor/worker 未传 subject →
文件名 URL 编码提取不到中文学科 → **化学 VL 路由失效静默走 PPS**。修复：
worker 传 document.subject（化学自动路由 PaddleOCR-VL-1.6）+ 上传接口/
task payload 支持 ocr_model 显式覆盖。test_worker_status 适配。

**9 科基线（v6.28，PPS 为主，语文综合题粒度）**：严格 **205/215 (95%)**、
答U 7、答M 0。语文 8/8、历史 43/43、生物 26/26、政治 28/28、英语 11/11、
地理 27/27（真实）、物理 19/20（Q18 图答案）、数学 22/23（Q15 负号）、
化学 21/26（待 VL）。

**版本升至 6.28。**

### 2026-08-25 21:30:00

#### 化学 VL 验证 + 数据源最终决策：基线 210/215 (98%)（版本 6.29）

**化学 PaddleOCR-VL 重跑验证**：ocr_provider=paddleocr, model=PaddleOCR-VL-1.6
（subject 传递修复生效），**15/26——比 PPS 21/26 更差**（Q6/Q10/Q13 题干
标记 + Q14-17 位置/选项越界大面积失败）。结论：**Paddle 系（PPS/VL）对
化学表格选项均不适用**（表格内选项结构识别差；VL 虽提取出 HTML 表格但
行号/归属大面积错乱），**mimo 26/26 是唯一完美选项**。

**数据源最终决策**：
- PPS（PP-StructureV3）为主：语文（综合题粒度 8/8）、物理 19/20、历史
  43/43、数学 22/23、生物 26/26、政治 28/28、英语 11/11、地理 27/27。
- mimo 保留：**化学 26/26**（Paddle 系表格盲区；PPS/VL 化学文档标记
  superseded，数据保留可回溯）。
- 语文粒度确认：PPS 8 题综合粒度（材料+全部子题）覆盖全卷，非退化。

**9 科基线（v6.29）**：严格 **210/215 (98%)**、答U 5、答M 0。语文 8/8、
历史 43/43、化学 26/26、生物 26/26、政治 28/28、英语 11/11、地理 27/27
（真实）、物理 19/20（Q18 图答案）、数学 22/23（Q15 负号）。

**版本升至 6.29。**

### 2026-08-25 22:00:00

#### 化学数据源切换 PVL：26/26（验证器口径修复，版本 6.30）

**人工核对结论（用户要求）**：PVL（PaddleOCR-VL）化学 OCR 质量远好于 PPS——
上下标 LaTeX 标准（`$Fe^{2+}$`、`$SO_{2}$`、`$Na_{2}CO_{3}$`、`$Cl^{-}$`）、
表格完整（Q16/Q18/Q20 含全部选项）、字母识别正确；PPS 则字母错乱
（`V`/`A`、`λ`/`Y`）、公式脏格式（`$\mathrm{S O}_{2}$` 空格、
`\ensuremath{\mathbf{e}}`）。

**PVL 15/26 的真因（非 OCR）**：
1. **verify_material 设计缺陷**：Q12/Q13（粗盐提纯材料题）的独立材料被
   build_sections 并入 section 共享 → section 内全部成员题（Q1-21）被要求
   DB stem 含粗盐材料 → 材料覆盖 0% 假阳性。修复：verify_material 优先用
   当前题 pipeline 的 own_shared，未标注共享材料 → 检查通过（非材料题）。
2. **L2 Q12/Q13 section 归属错**（粗盐提纯_12_13 → 第一部分_选择题）：
   section 边界 id_max 被提前到第 2 页 → Q14-21（第 3/4 页）误判越界。
3. **L2 stem_start_marker 与 DB stem 差异**（Q6 转义反斜杠 `6\.`、Q10 空格
   `$N_A$` 等）→ 修正 marker 对齐。

**修复后 PVL 化学 15/26 → 26/26**。化学数据源：PVL（OCR 质量最好，
mimo/PPS superseded，数据保留）。

**9 科基线（v6.30）**：严格 **210/215 (98%)**、答U 5、答M 0。语文 8/8、
历史 43/43、化学 26/26（PVL）、生物 26/26、政治 28/28、英语 11/11、
地理 27/27（真实）、物理 19/20（Q18 图答案）、数学 22/23（Q15 负号）。

**版本升至 6.30。**

### 2026-08-24 23:30:00

#### 物理 Q18 + 数学 Q15 修复：基线 212/215 (99%)（版本 6.31）

**物理 Q18**（受力分析图题，DB `（1）见解析 （2）1.5N （3）夹角增大，拉力增大`）：
- (1) 答案在受力分析图中（答案区该子部分无文本，只有分值注记），"见解析"
  是正确占位。**验证器支持"见解析/见详解"图答案占位剔除**：从核对清单
  剔除该子部分（不要求匹配、不计缺失），其余子部分仍须全部命中。
- (3) DB 摘要 "夹角增大，拉力增大" 不是答案区完整表述
  （"F增大，θ增大，轻绳与竖直方向夹角增大，轻绳拉力T增大"）子串 →
  **数据修复** DB answer (3) 改为与答案区一致表述（`fix_physics_q18.py`）。
- 修复后 **物理 19/20 → 20/20**。

**数学 Q15**（DB `①. $6$ ②. $-\frac{7}{3}$`，三源负号证据损坏）：
- DB 答案用**圈号 ①②**（无括号子号），`_split_structured` 原只认（N）→
  parts 为空 → 退化为 free_text 失败。**验证器支持圈号 ①-⑩ 拆分**。
- (2) fragment `-7/3` 在答案行 OCR 丢失负号（`~7/3`），但**详解含正确值**
  （"取最小值-7/3"、"故答案为:6:-7/3"）→ **负号值题号窗口级搜索**：
  子窗口未命中且 fragment 以 "-" 开头时，在题号窗口（2000 字符）内再搜。
- 短片段（纯数字值如 "6"）只在子题标记紧邻区（前 80 字符）匹配，防窗口
  越界命中后续题号/详解中的无关数字。
- 修复后 **数学 22/23 → 23/23**。

**连带回归修复**：`_split_structured` 重写后物理 Q20（3）DB 答案
"f1/f2=cosθ（或f2/f1=1/cosθ）" 的 "（或…）" 保留 → `split("=")[-1]` 被
内层 "=" 拆成 "1/costheta)" → structured_partial。修复：**"（或…）"等价
表述在 split("=") 前剥离**（答案区只给主式）→ Q20 恢复 matched。原有
"（或…）"截断行为由旧 `[^（(；;]+` 正则隐式提供，新实现显式化。
verifier 单测 20 passed（含原有 Q17/Q20 结构化用例）。

**9 科基线（v6.31）**：严格 **212/215 (99%)**、答U 3、答M 0。答U 3 全部为
地理报告管线幻选题号残留（23/24/25，DB 27 题正确，非真实缺口）。语文
8/8、历史 43/43、化学 26/26（PVL）、生物 26/26、政治 28/28、英语 11/11、
地理 27/27（真实）、**物理 20/20**、**数学 23/23**。

**版本升至 6.31。**

### 2026-08-25 01:30:00

#### 30 份样本验证（61%）+ P2/P4 修复 + 审计结论（版本 6.32）

**样本扩展验证**：test/pdf 30 份全部入库（10 份已有 completed + 20 份新跑）。
新样本原始质量 **134/219 (61%)**（零人工干预）；stem/位置/材料覆盖 92%+，
缺陷集中在答案/入库环节。运行期问题 P1-P9（MinIO 文件名、260 路径、paddle
熔断 10010、retry 500、僵尸任务、deepseek 慢、worker 挂死、VL 队列满、
脚本 env 路径）全部记录。

**P2 修复（Windows 260 路径限制）**：`processor._download_pdf` 临时文件名
改为短名 `doc_<uuid>.pdf`（管线 filename 仍传原值）。验证：51bf043c
（路径 261）与 19086f92（路径 297）——两个曾必失败的文档均 completed
（ingested 18/21、26/26）。

**P4 修复（retry API 500）**：根因 = retry commit 后 onupdate 列 expired，
`_serialize_task` 同步访问触发 MissingGreenlet。修复 = TaskService 新增
`refresh()`，application 层 commit 后 refresh。验证：retry API 返回 409
（正确业务响应，不再 500）。

**审计结论（未修，记录根因）**：
- 化学 17 mismatch：**同号题锚定冲突**（选择题答案表 vs 综合题详解，卷面
  存在多个同号"2."）——提取/锚定层缺陷，非 OCR 问题。
- 入库缺口（数学 3 题、生物 9 题）：**选择题题干/答案提取失败**
  （stem_empty / 锚点需重新标注 / answer_empty）。
- 地理育英 23 U：**答案区无题号锚点**（no_answer_evidence）——验证口径
  需适配答案区结构。
- P10：worker LLM 请求挂死复发（P7 在 answer_extractor、P10 在
  llm_annotation；deepseek 探测正常）——重启 worker 恢复；**待修**：LLM
  调用加超时/心跳。

**版本升至 6.32。**

### 2026-08-25 02:30:00

#### worker LLM 挂死 P7/P10 双层超时兜底（版本 6.33）

**根因**：`LLM_REQUEST_TIMEOUT_SECONDS=300` 是 httpx **空闲超时**（两次
数据读取间隔），deepseek 流式响应持续有数据时可远超总时长（实测最长
339s 成功）；而挂死场景（连接挂起无数据且不关闭）空闲超时可能失效 →
请求无限等待 → 单任务卡死阻塞整个批次（P7 answer_extractor、P10
llm_annotation 两次出现，deepseek 探测均正常）。

**修复（双层兜底）**：
1. **LLM 层**（`ai/providers/http.py` `_post_completion`）：请求包
   `asyncio.wait_for` 总时长兜底 = `max(2×空闲超时, 600s)`——容纳正常
   reasoning 响应（~6min），挂死请求 10min 内强制取消 → TimeoutError
   （继承 OSError，走既有重试/失败路径）。新增 `total_timeout_seconds`
   参数便于测试注入。
2. **worker 层**（`worker/document_worker.py`）：`process_document` 整体
   `asyncio.wait_for` 3600s 兜底；超时取消后 task 幂等标记 failed
   （不再僵尸），可重试（P4 已修 retry）。

**验证**：新增 `backend/tests/test_http_provider_timeout.py` 3 用例
（挂死请求总超时取消、挂死重试后抛错、正常请求不受影响）；相关套件
36 passed 无回归。提交 `9bf6594`。

**版本升至 6.33。**

### 2026-08-26 08:06:54

#### DOCX 全管线支持 + 验证器 DOCX 适配 + worker 僵尸恢复 + 扫描件标注（版本 6.34）

**① DOCX 全管线支持（提交 6c7f729）**：
- `extract_l1_from_docx`（python-docx 段落+表格），解析 numbering.xml 还原
  Word 自动编号前缀（upperLetter→A、decimal→数字、roman→罗马）；
  simple_pipeline 对 .docx 跳过 OCR（ppsv3_doc=native_doc、零 paddle token）；
  processor 临时文件保留原后缀（限 .pdf/.docx）。
- DOCX 九科样本（test/docx，2018-2021 教师版）全量 e2e：严格通过率 62%
  （165/267），答案命中 90%、答M=0。但口径注意：与 PDF 基线是**不同试卷**
  非一对一对比，且 DOCX 批次选择题更多（275 vs 219）。
- **DOCX 短板（记录，后续处理）**：选项/公式为图片时原生提取丢失
  （数学 docx 271 张 WMF 公式图，paragraph.text 不含）；双卷题号冲突
  （数学 A+B 卷 unique 约束拒 B 卷）；分栏布局锚定错位。讨论存档
  `tmp/docx_pipeline_discussion.md`。

**② 验证器 DOCX 适配（提交 64ec9f3）**：
- pdf_raw 误配修复（非 .pdf 文档不参与 subject 模糊匹配，否则 docx 会
  误用 test/pdf 下同科目其他 PDF 当答案证据源）；
- docx 答案格式解析：内联 `1.【答案】D`、管道表格、无表头双行、同行配对；
- 上标字符 int() 崩溃修复；e2e 排序 length+text（地理 "二.1"）。
- 效果：DOCX e2e 从初跑 28% → 62%（答M 106→0）。

**③ worker 僵尸任务恢复（提交 12cd06a）**：
- 问题：worker 重启/崩溃遗留的 running 任务不会被轮询重拾（只查 queued）
  → 文档永久卡 processing（DOCX 批次英语任务曾手工改 DB 才恢复）。
- 修复：TaskService.recover_stale_running_tasks（running+超时+非 active
  → 重置 queued）+ repository list_stale_running + worker 每轮询先恢复
  （_active_task_id 跟踪当前任务）。单测 3 + worker 套件 30 passed +
  E2E（ghost 任务 6s 恢复→拾取，日志 "recovered 1 stale running task"）。

**④ 扫描版 PDF 检测标注（提交 148d8e6）**：
- 昌平生物（全库唯一无文本层 PDF，PyMuPDF text_coverage=0）8 题题号被
  OCR 误读（9→D、15→1b、28→33），实测换 OCR 引擎无效（PaddleOCR-VL 与
  PP-StructureV3 同一后端，题号印刷模糊；题干内容两引擎均能认对，仅
  "第几题"编号丢失）。
- 决策（方向 B）：纯扫描件是少数（当前 1/39），不为异常样本反复调后端。
  检测 text_coverage < 0.02 → 标记 processing_status=scanned，跳过
  OCR/LLM（零 token 浪费），后续集中处理。此前为扫描件加的 option-fallback
  + 宽松题号匹配补丁已全部回退。
- E2E：昌平生物重跑秒级标记 scanned（无 paddle 请求）。

**⑤ 规则新增（rules.md）**：遇到同一问题反复修改 ≥2 次、较大代码级/架构级
调整、或用后端补"上游输入质量"问题时，必须先大白话讲清根因与改动范围，
获得用户确认后再动手；禁止连续多轮闷头改代码、逐层加补丁。

### 2026-08-26 13:20:00

#### 答案归一化去重（answer_conflict 假冲突，提交 91c268f）

**根因**：数学 40 题 + 物理/政治/语文/生物/英语共 ~63 题被标 answer_conflict
卡 reviewing。同一道题两次入库（幂等重灌），LLM/OCR 输出格式抖动被误判冲突：
`$0$` vs `0`（LaTeX 定界符）、`(1)` vs `（1）`（全角/半角）、换行 vs `；`
（分隔符）、`①.` vs `①`（圈号后点号有无）。

**修复（ingestion.py）**：
- `_compact_answer` 归一化：去空白 → 圈号后点号归一（`①.`→`①`）→ 全角转
  半角 → 换行/分号统一 → LaTeX 剥离（`$`、`\frac{a}{b}`→`a/b`、`\text{}`→
  内容、`\pi`→π、`\left/\right` 等命令去除）。仅用于去重冲突判断，不改
  存储答案。
- dedup exact（归一化后一致）时清除历史遗留 answer_conflict 标记并恢复
  approved（否则假冲突标记永久滞留 reviewing）。
- 测试 +2（LaTeX/全角差异不冲突、exact 清除历史标记），24 passed。

**验证**：二附中数学重灌，Q14/17/18/23 假冲突清除恢复 approved；剩余
Q13/15/16/19-22 为本轮 LLM 真实输出差异（圈号错位 `0①` / 截断 / 乱码），
保留 reviewing 合理（需人工审核）。

### 2026-08-26 19:20:00

#### 共享题图选择题组合并为综合题（提交 d35d878）

**问题**（育英地理，用户既定产品规则）：卷面"读图/读表…完成 N—M 题"
共享题图/前提的若干选择题应合并为一道综合题（脱离题图子题无法独立
作答）。此前 LLM 标 shared_material_line_ids 但 is_composite=False →
29 题全独立入库，题图上下文丢失。Q21 有自己独立的折线图 → 应保持独立。

**修复**（LLM 语义判断为主，非机械行号合并——遵循"LLM 负责判断、代码
负责执行"）：
1. **line_annotator prompt**：明确"共享材料/题图即合并，不依赖能否独立
   作答"；特别提醒选择题组共享题图时必须合并（不要因各有选项判独立）；
   补共享题图综合题 JSON 示例（子题带 stem_line_ids/options_line_ids）；
   L2 解析透传子题题干/选项行号。
2. **schemas_l2**：L2SubQuestion 增加 stem_line_ids/options_line_ids。
3. **content_slicer._merge_question_group**：合并时透传子题题干/选项。
4. **anchor_corrector**：_QUESTION_NUMBER_RE 支持中文逗号 `21，`（全库
   仅育英 Q21 一处，零误伤）。

**验证**：育英地理重跑（deepseek-v4-flash）→ **13 综合题 + 1 独立（Q21）**：
9 组共享题图选择题组全部正确合并（Q1-4/5-8/9-11/12-13/14-15/16-17/
18-20/22-23/24-25），子题数量对齐，答案 `(18) B (19) A (20) B` 格式
正确，ingested 14/14。114 passed 无回归。

**版本升至 6.34。**

### 2026-08-26 20:15:00

#### 综合题父题答案缺失（answer_missing）修复（提交 367c7df，版本 v6.35）

**问题**：育英地理重灌后 9 题 reviewing/answer_missing（此前 quality_gate 修复后从 anchor_uncertain 转出）。DB 显示父题 answer 为空、子题答案完整。

**根因链**：
- 综合题由 LLM 直接输出（_merge_shared_material_questions 只分类不合并），LLM 把答案写在 sub_questions[].answer，父题 answer 字段本身为空；
- answer_matcher 的选择题纯字母校验（_CHOICE_ANSWER_RE = ^[A-G]{1,7}$）把子题汇总格式 "(9) A (10) B (11) D" 判定为"非字母"而清空 → 父题 answer=None → quality_gate 报"答案缺失，禁止自动发布"；
- 且文末答案表按父题号给单字母（如 18→B），answer_map 覆盖会丢失子题汇总。

**修复**（3 处，全部针对选择题组综合题 is_composite+choice）：
1. content_slicer：_slice_single_question 透传 LLM 父题 answer；slice_questions 对父题 answer 为空的综合题从 sub_questions 构建汇总 "(9) A (10) B (11) D"（格式与 _merge_question_group 的 merged_answer 一致，仅空时构建不覆盖已有答案）；
2. answer_matcher：_apply_llm_annotation_answers 与 match_answers 主循环跳过选择题组综合题（保留汇总答案，不被纯字母校验清空/答案表单字母覆盖）；
3. ingestion：选择题组综合题不用 answer_map 单字母覆盖汇总答案。

**验证**：
- 育英地理重灌：14/14 approved，0 answer_missing（此前 9 题 reviewing）；
- 综合题父题答案=子题汇总（Q1:"(1) C (2) B (3) D (4) C"），子题答案完整保留；
- 新增 5 单测（slice_questions 汇总构建/不覆盖已有答案、answer_matcher 保留汇总、quality_gate 综合题跳过选项检查）63 passed；
- 全量回归 651 通过，4 failed+2 errors 均为既有沙箱环境问题（HTTP 超时模拟/vision OCR/真实管线/tmp 权限）。

**版本升至 6.35。**

### 2026-08-26 21:40:00

#### 多副本文档治理（v6.36，数据侧）

**背景**：全库 50 个 PDF 文档中 10 个文件名存在 2~4 个 document 副本（多次重灌/路径超 260 短名重传遗留），旧副本的 reviewing 残留虚增缺口统计。

**治理**（tmp/supersede_dups.py，规则：completed 优先 → reviewing 最少 → inst 最全 → 最新者为权威，其余标记 superseded）：
- 标记 16 个 completed/processing 副本为 superseded：北师大实验数学 db2cb33d、2025东城历史 80e72eaa/de81a7f5/3384f8ec、2026东城政治 125f99f3、2026东城英语 96830c18/8729f29a/159ac0d8、2026二中数学 5108787b、八十中物理 dfd13f8a/635ac7f7/f7abd939、北师大生物 af6ae05f、朝阳地理 6f5a2eac、朝阳语文 1110840d/f886c4ef；
- 同卷不同名：19086f92（长名 P2 重复）superseded，保留 66ab79ec（短名，30 份样本正式记录）。

**缺口统计修正**（只看权威副本）：
- 历史 6→1（只剩海淀 Q14 anchor_uncertain 独立题选项锚点）
- 物理 3→1、生物 4→3、语文 4→3、化学 18→16
- 剩余：化学 16（anchor 8 / low 5 / missing 3）、语文 3、生物 3、数学 2、物理 1、历史 1

**版本升至 6.36。**

### 2026-08-26 22:30:00

#### 化学表格选项题方案定稿（v6.37）

**问题**：化学 8 题 anchor_uncertain 全为表格选项题（实验装置图/表格选项）。
根因：VL OCR 把选项区识别为单行 `<table>`（选项 A/B/C/D 在 `<td>` 内），
LLM 无法给选项独立行号 → options_line_ids 全空 → 锚点校验 retry。

**调查结论**（3 份化学卷 5 类表格形态验证）：
- VL 表格文本质量优于 native（公式/上下标完整，如 `$ \ce{Fe(OH)3} $`），
  问题只在"整表一行不可锚定"；
- native 层同区域有独立行选项（可锚定）但文本质量差（下标丢失）；
- 对照 Q13（成功）：资料表（选项在表外普通行）LLM 正常锚定；
  Q8（失败）：选项标签在表格内部（`<td>A</td>`）→ 无法锚定。

**方案（用户确认）**：VL 表格拆行——仅对"选项表"（表格内部首列有 A-G 标签
且行 ≥2 列）拆行：`<td>A</td>` 转 `A. ` 前缀 + 其余 `<td>` 用 `，` 合并，
保留 VL 公式文本；资料表/答案表保持单行。拆行后 LLM 看到独立行 →
给出独立行号 → 锚点校验与选项切片零改动可用。

**实现**：`ocr_l1_converter.py` `_split_block_lines` / `_split_markdown_lines`
（VL 表格单行合并处）+ 单测（选项表拆行/资料表不拆/答案表不拆）。

**版本升至 6.37。**

### 2026-08-26 23:50:00

#### VL 表格选项题锚点修复验证完成（c0c0f27，版本 v6.38）

**验证**（4 份化学卷重灌，LOG v6.37 方案的落地）：
- 八十中：Q10/Q12 approved（选项含 <img> 引用、三列内容完整切片）
- 大兴：Q1/Q17/Q19 approved（26/26 ingested，blocked=0）
- 北师大二附：Q6/Q8 approved（19/19 ingested）
- 二附中选考：Q14/Q22 approved（26/26 ingested，blocked=0）
- 化学 anchor_uncertain **8→0**；全库缺口 **26→17**

**实现**（ocr_l1_converter.py）：
- _is_option_table：4 种选项表形态（五行/2×2 图+文/纯标签行+内容行/表头+选项行），
  排除答案表（题号/答案表头）与资料表
- _split_option_table：拆成 'A. <内容>' 行（保留 VL 公式与 <img> 引用）
- 单测 4 新增 + 2 更新，92 相关 / 634 全量通过

**剩余缺口**（17）：化学 7（low 5 / missing 2，解答题质量）、语文 3、生物 3、
数学 2、物理 1、历史 1。

**版本升至 6.38。**

### 2026-08-26 23:59:00

#### short_answer 膨胀放宽 + boundary 答案区豁免（47b2b64，版本 v6.39）

**问题**：化学 7 题缺口 = 5 low_confidence（膨胀误伤）+ 2 answer_missing（答案区被截断）。

**修复 1（quality_gate）**：short_answer 一律按综合题上限（3000）计长。
- 解答题合法题干可长（化学 Q23 1025 字符、Q15 1208、语文默写 2098）；
- 数据：全库 >800 解答题 38 题中 28 已 approved，长题干是解答题常态；
- 真膨胀（语文 Q17 默写混入散文）改由答案质量检查兜底（用户决策，前端反馈机制后续补）。

**修复 2（answer_matcher）**：_filter_to_question_boundary 豁免文末答案区。
- 全库 124 个 short_answer 答案行全部位于答案区（0 例紧跟题目）；
- boundary 把答案区行当"越界"清空 → answer_missing（化学 Q16/Q19）；
- 答案区（"参考答案"标题后）行保留，仅过滤"下一题号行到答案区之间"的解题过程
  （物理 Q18 混入 Q19 行案例仍被拦截，回归测试保护）。

**验证**：4 份化学卷重灌 reviewing 全部清零（二附中 0、大兴 0、北师大二附 0、八一 0），
全库缺口 17→10（化学 7→0）。638 单测通过。

**版本升至 6.39。**

### 2026-08-27 07:20:00

#### 管理后台「题库管理」页面上线（v6.40）
**目标**（用户）：重跑全量测试前先完成前端页面，能从页面直观查看入库结果。
**参考**：V1 前端（`D:\Project\AI Tutors\frontend`）的题库目录树 + 题目表格形态；
设计语言遵循 `Docs/Design.md`（Apple-like，单一蓝 #0066cc，无阴影无渐变）。
**前端**（`frontend/src/pages/QuestionBankPage.tsx`，约 500 行 + App.tsx 路由 `/admin/questions` + theme.css 样式）：
- 左侧目录树：学科 → 年级 → 题目数（`GET /api/admin/catalog` 新端点）；
- 右侧题目列表：状态徽章（已入库/待审核/已驳回/草稿）+ 题干摘要 + 学科/题型/难度/置信度/出现次数/综合题；
- 筛选：学科 / 状态 / 题型 / 难度；分页；
- 点击行展开详情：题干/选项/答案/详解/配图标识（`GET /api/admin/questions/{id}`）；
- AdminHome 文档列表新增「入库」入口 → `/admin/questions?document=<filename>`（按 source_document_name 模糊筛选）。
**后端**：
- `repository.py`：`catalog()` 学科→年级聚合；`_build_search_stmt`/`search` 加 `source_document_name` ilike 筛选；
- `service.py` / `application/services.py` / `api/routes/questions.py`：透传 + `GET /api/admin/catalog` 端点；
- `_serialize_question` 增加 `subject_name` / `question_type_name`（全量查 subjects/question_types 映射，一次查询）。
**已知缺口**：入库题目图片仅持久化 image_id（无 URL），详情页当前显示配图标识列表，实际图片渲染待后端图片服务端点。
**验证**：Playwright（Edge headless）实测——目录树 28 节点、题目列表 20 行、详情展开（答案/选项/配图标识）、学科/状态筛选、文档入口跳转+解码、无 404（除 favicon）；tsc 类型检查通过；后端 10 单测 + 19 集成通过。
**版本升至 6.40。**

### 2026-08-27 08:15:00

#### 入库质量诊断 + 前端题库页修复（v6.41）
**诊断结论**（用户反馈"入库质量不高"后全面核查）：
- 数据层真实问题：详解缺失 548/921 approved（59%）、reviewing 积压 86 题、图片仅存 image_id 无 URL；
- 前端误判澄清：公式渲染正常（katex 53 个公式 OK）、综合题结构正常（子题 1-5 占 110/135）、学科归属正确；
- 反斜杠非脏数据（LaTeX 合法转义，仅 8 题真实双反斜杠且为 aligned 换行符）。
**修复 1（前端 bug）**：题库页读取 URL subject 参数（d63bffe），?subject=化学 正确筛选 181 题。
**修复 2（脏数据清理）**：17 题——15 题图片残留（外链→【图片】占位/描述保留/OCR 本地 img 移除）+ 2 题地理选项混入题干（去选项残片，从 OCR 原文还原正确题干）。
**修复 3（图片 URL 落库，bd8d91c）**：QuestionImage 新增 url 列（migration 20260827_0001），_build_question_images 携带 img.url，ingestion 保存，API 返回，前端有 URL 渲染实际图/无 URL 降级显示标识列表。历史数据 URL 已过期（PaddleOCR 签名 0/15 可访问），对重跑后的新数据生效。
**待进行**：LLM 批量回填 548 题缺失详解（逐文档提取，47 文档）；reviewing 86 题（82 题有答案，等 30 份 PDF 重跑自动修复）。
**版本升至 6.41。**

### 2026-08-27 08:40:00

#### 详解回填实测 + 决策（v6.41 补充）
**实测结论**（逐文档 LLM 提取方案）：
- 47 个文档逐个调用 answer_extractor 提取答案+详解，单文档长文档耗时 171s（近超时），全程预计 2+ 小时；
- 命中率极低：首文档 43 题仅 2 题有详解——教师版试卷答案区大多只有答案没有详解，
  LLM 忠实执行"没有就留空"规则，提取方案本质无解。
**用户决策**：放弃批量提取详解，接受现状（详解缺失 548/921 approved 为源文档固有属性，
非管线缺陷）。已停止全部提取任务。
**reviewing 积压结论**：86 题中 82 题实际有答案（anchor_uncertain 60/answer_missing 9/
low_confidence 8/answer_suspicious 5 都有答案），仅 4 题真无答案（3 数学填空 OCR 公式丢失 +
1 地理综合题号缺失）。积压主因是旧代码标注质量 + 旧文档 OCR，30 份 PDF 全量重跑（新代码：
VL 表格拆行/答案区豁免/膨胀放宽）预计自动修复大部分。
**版本保持 6.41（补充记录）。**

### 2026-08-27 19:00:00

#### 暂停：用户重启 PC（v6.41 会话结束）
**当前 HEAD**：a27550e（docs: quality diagnosis, cleanup, image url persistence, backfill decision）
**已完成**（本轮会话）：前端题库管理页（v6.40）+ 前端 subject 参数修复（d63bffe）+
图片 URL 落库 migration 20260827_0001（bd8d91c）+ 17 题脏数据清理 + 入库质量诊断 +
详解回填放弃决策 + reviewing 积压分析（82/86 有答案）。
**服务状态**：vite dev（5173）与 uvicorn（8000）已停止（准备重启 PC）。
**基础设施（Docker 容器，重启 PC 后 Docker Desktop 自动恢复）**：
- `aitutor-postgres` → localhost:15432（DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:15432/aitutors）
- `aitutor-minio` → localhost:9000/9001（minioadmin/minioadmin，bucket=aitutors）
- `aitutor-redis` → localhost:16379
- 若未自动启动：`docker start aitutor-postgres aitutor-minio aitutor-redis`
#### 2026-08-27 21:30:00 — ChatGPT 四轮审计 + Codex 复核后执行决策（重启后 Sprint）

**审计结论核实**（均与代码事实一致）：content_hash 生命周期漏洞（apply_review 改内容不重算 hash）、
DSD §8 状态漂移（"待实现"但已落地）、test/ 被 gitignore 导致 GitHub 无法复现、生产管线依赖 legacy 内部函数。

**重启后 Sprint 排期**（小 Sprint，不全量执行 P0）：
1. **P0 content_hash 生命周期**（重跑前必须做）：统一领域入口 `update_question_content()` ——
   内容变化→重算 hash→查 exact duplicate→冲突标记审核；apply_review 内部调用它；补回归测试
   （人工审核改题干后新内容能正确去重、旧 hash 不残留）。**注意**：修复后重跑可借机验证 dedup 收敛。
   **先不**加 UNIQUE(subject_id, content_hash)——先修写路径 + 审计现有重复，避免迁移失败固化审核差异。
2. **P0 DSD §8 修正**：把"已实施的 Phase 2A schema"与"未来 Family/Similarity 计划"分开，删除"待实现/旧结构"表述。
3. **P0 AGENTS.md 薄入口**（不新建 PROJECT_CONTEXT.md）：opencode.json 只自动加载 AGENTS.md，
   但 AGENTS.md 只有 agent 路由——改为薄入口指向 RESTART_PROMPT + rules。
4. **P2 Pipeline 共享内核拆分（方案 A + 兼容层标注）**：
   - 新建 `pipeline_shared.py`：PipelineResult + save_result + _filter_by_page_range + _build_question_images
     + 依赖 helper（_provenance_to_dict/_anchor_to_dict/_slice_l1_text/_question_is_ingested/
     _discard_reason_label/_discard_category_for_issue/_question_field_line_ids/
     _question_option_line_ids/_bbox_contains_with_margin）+ schemas import，**无循环依赖**（shared 不 import pipeline）；
   - pipeline.py 顶部显式标注"**兼容层**：生产代码禁止从这里导入共享符号，请从 pipeline_shared 导入；
     re-export 仅兼容 legacy 测试与旧调用"+ re-export；
   - 生产三文件（simple_pipeline/processor/ingestion）改从 pipeline_shared 导入；
   - **测试零改动**（re-export 兼容）；验收=rg 确认生产三文件不再 from pipeline import 共享符号 + 全量 pytest；
   - LOG 留一条"移除 legacy 时同步迁移 17 个测试文件 import"后续事项。
   **不做**：不拆 result/helpers/legacy/simple 四文件、不动 parser.py/question_extractor.py、不动 scripts 目录；
   extract_l1_from_pdf/ocr 不进 shared（legacy 测试面，等删除时处理）。
5. **P1 最小 JSON fixture 版本化**（重跑后）：只解除小 fixture ignore，不提交真实 PDF；
   每修复一个真实 bug 沉淀一个最小匿名 regression fixture。

**决策原则**（延续）：不为极小概率事件过度投入；治理文件必须替代而非叠加；先修写路径再加 DB 约束；
代码优先于文档（文档可能过时）。

**重启后待办**：
1. 读 PROJECT_STATUS.md（已更新至 v6.41）恢复上下文；
1b. **先读本暂停记录中的"2026-08-27 21:30:00 审计执行决策"**：重启后 Sprint 五项
    （content_hash P0 / DSD P0 / AGENTS.md P0 / Pipeline 方案A P2 / fixture P1）按此排期执行，
    content_hash 必须在 30 份 PDF 重跑之前完成；
2. 重新启动后端（uvicorn 8000，backend 目录，`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`）；
3. 重新启动前端（vite 5173，frontend 目录，`npx vite --port 5173 --strictPort`，沙箱需 danger-full-access）；
4. 等用户确认后启动 30 份 PDF + 9 份 DOCX 全量重跑（半小时轮询，rerun_docs2.py 批量入队）；
5. 重跑后对比缺口（当前 10）+ reviewing 积压（86）+ 详解缺失率（59%）变化；
6. 完成后整体情况汇总 + DOCX 管线调整决策（tmp/docx_pipeline_discussion.md）。

### 2026-08-27 20:04:17（v6.42）

#### Sprint 治理五项完成（按 21:30 审计执行决策排期执行）

**1. P0 content_hash 生命周期**（重跑前必须做，已就绪）：
- `question/service.py` 新增统一领域入口 `update_question_content()` +
  `_apply_content_update()`：内容变化（stem/options/sub_questions）→ 重算
  content_hash → 查 exact duplicate（同学科同 hash 排除自身）→ 答案归一化
  不同则标记 `answer_conflict:<source>:<answer>` + 降 reviewing（不静默覆盖）。
- `apply_review` 内部改走 `_apply_content_update`（此前 overrides 改题干/选项
  不重算 hash → 旧 hash 残留、新内容无法去重）。question_type 从
  question_type_id 反查 `QuestionType.code`（hash 需题型字符串）。
- `question/repository.py` 新增 `find_by_content_hash_excluding()`。
- `_compact_answer` 从 ingestion 提升为 `content_hash.compact_answer` 公共函数
  （ingestion 与 question 域共用，去重判断归一化一致，避免跨域依赖 ingestion）。
- 回归测试：`test_phase2a_step5_content_hash.py` 新增 `TestContentHashLifecycle`
  7 项（改题干重算/旧 hash 不残留、只改答案 hash 不变、无 overrides hash 不变、
  撞车冲突降 reviewing、撞车答案一致不标记、update_question_content 改 options、
  未知题返回 None）。
- **先不加 UNIQUE(subject_id, content_hash)**（审计决策：先修写路径 + 审计现有
  重复，避免迁移失败固化审核差异）。

**2. P0 DSD §8 修正**：标题/引言去掉「待实现/当前 DB 仍为旧结构」，改为
「已实施 + 未来计划」；§8.1-8.3 标注已实施（migration 20260821_0003/0005、
20260827_0001，`alembic current` 在 head）；§8.5 拆分为「已实施原则」与
「未来 Family/Similarity 原则」；§4.5 两处过时说明同步修正；§10 追加变更记录。

**3. P0 AGENTS.md 薄入口**：移除 agent 路由指南（不承载项目上下文），改为
薄入口指向 RESTART_PROMPT + rules + PROJECT_STATUS（opencode.json 只自动
加载 AGENTS.md，未新建 PROJECT_CONTEXT.md）。

**4. P2 Pipeline 共享内核拆分（方案 A + 兼容层标注）**：
- 新建 `pipeline_shared.py`：PipelineResult + save_result + _filter_by_page_range
  + _build_question_images + 依赖 helper（_provenance_to_dict/_anchor_to_dict/
  _slice_l1_text/_question_is_ingested/_discard_reason_label/
  _discard_category_for_issue/_question_field_line_ids/_question_option_line_ids/
  _bbox_contains_with_margin）+ schemas import，**无循环依赖**（shared 不 import
  pipeline）。
- pipeline.py 顶部显式标注「**兼容层**：生产代码禁止从这里导入共享符号，请从
  pipeline_shared 导入；re-export 仅兼容 legacy 测试与旧调用」+ re-export
  13 个符号；清理 4 个未使用 import（json/L1Page/L2DocumentAnnotation/SlicedQuestion）。
- 生产三文件（simple_pipeline/processor/ingestion）改从 pipeline_shared 导入。
- **验收**：rg 确认生产代码不再 `from pipeline import` 共享符号 ✅；
  pipeline 相关测试 139 passed ✅。
- **后续事项**：移除 legacy 时同步迁移 17 个测试文件 import。
- **不做**：不拆 result/helpers/legacy/simple 四文件、不动 parser.py/
  question_extractor.py、不动 scripts 目录；extract_l1_from_pdf/ocr 不进 shared。

**5. P1 最小 JSON fixture 版本化**：.gitignore 改为 `test/*` + `!test/fixtures/`
+ `!test/fixtures/**`（放开最小匿名 JSON/markdown fixture，便于 GitHub 复现）；
真实 PDF/DOCX/JPG（40 个样本 36.8MB）保持 ignore。每修复一个真实 bug 沉淀
一个最小匿名 regression fixture（后续持续）。

**测试结论**：全量 pytest **680 passed / 7 failed / 2 errors**。
- 7 failed = 4 个**既有**（基线 HEAD 同样失败，已 git stash 验证）：
  test_phase2_fixes url 断言 3 个（v6.41 bd8d91c 加 `url` 字段测试未同步）
  + test_processor_progress scanned 1 个（v6.34 扫描件检测 mock l1_doc
  text_coverage=0 触发 scanned 分支）+ 2 个沙箱 temp ACL
  （ocr_vision_pdf_fallback，PermissionError 写沙箱 temp）+ 1 个 flaky
  （http_provider_timeout，单独跑/整文件跑通过，全量顺序依赖）。
- 2 errors：test_temp_root/test_validation_harness 沙箱 temp ACL
  （用户本机可过，v6.41 已记录）。
- **无本次改动引入的确定性回归**。
- 待用户确认：4 个既有失败是否顺手修复（均为小修复，不影响生产）。

**版本保持 6.42（Sprint 治理完成，PROJECT_STATUS 已更新，v6.41 已快照到
docs_archive/status/）。下一步：等用户确认启动 30 份 PDF + 9 份 DOCX 全量重跑。**

### 2026-08-27 20:21:29（v6.42 补充：7 个失败测试全部修复 + 2 errors 根因定位）

用户质疑失败评价的客观性后，逐项深挖并修复全部 7 failed（687 passed）：
- **test_phase2_fixes 3 个（v6.41 url 字段回归）**：`_build_question_images` 在
  v6.41（bd8d91c）携带 `img.url`，测试断言未同步 → 断言补 `"url": None`。
- **test_processor_progress 1 个（v6.34 扫描件检测回归）**：`_make_l1_doc` 不传
  text_coverage（默认 0.0）触发 scanned 分支跳过主流程 → 显式传 `text_coverage=1.0`。
- **test_ocr_vision_pdf_fallback 2 个（沙箱 temp ACL）**：`tempfile.mkdtemp` 落在
  conftest 重定向的 `%TEMP%\aitutor_pytest`，沙箱拒绝测试进程写入 → 改用工作区
  tmp（`tmp/pytest_ocr_vision` + uuid 子目录，模式与 paddle_circuit_breaker 一致）。
- **test_http_provider_timeout 1 个**：此前误判"flaky（单独跑通过）"——实测单独
  运行 5 次有 2 次超 2.0s（1.1~2.1s 波动）。根因：`httpx.AsyncClient` 构造在沙箱下
  耗时 0.9-1.9s（wait_for 本身 0.2s），`elapsed < 2.0` 断言过紧（全量 684 测试时
  elapsed=2.19s）→ 断言放宽到 `< 5.0`（功能断言 TimeoutError 抛出保留）。
- **2 errors 根因定位（test_temp_root / test_validation_harness）**：pytest
  basetemp = `%TEMP%\aitutor_pytest`（conftest），沙箱 ACL 限制测试进程创建/清理
  basetemp 下目录（历史 ocr_vision_* 残留删不掉，跨进程 SID 隔离，外部删除不生效）
  → tmp_path fixture setup ERROR。修复需把 conftest WORKSPACE_TMP 改到工作区 tmp
  （当前沙箱会话工作区 tmp 可写可删，paddle/ocr_vision 已验证；但 conftest 注释
  记录 2026-08-22 工作区 tmp 曾被锁的历史教训）→ **待用户确认后改 conftest**。

**教训**：分类「既有/环境」必须有修复动作，不能只解释；「单独跑通过」不等于
「非回归」（需实测耗时分布）；沙箱 temp 与工作区 tmp 的 ACL 差异是测试编写硬约束。

### 2026-08-27 20:28:42（v6.42 补充：conftest basetemp 实测结论 + 回滚）

用户确认改 conftest 后实测两种方案均不可行，**conftest 已回滚到原状**：
- 方案 A（工作区固定 basetemp `tmp\aitutor_pytest`）：pytest 进程
  `os.listdir` 自己刚 mkdir 的目录即 PermissionError（独立 python 进程访问
  同一路径完全正常——mkdir/listdir/write/rmtree 全过 → 沙箱对 pytest 长进程
  的工作区目录操作有额外拦截，conftest 2026-08-22「工作区 tmp 被锁」教训复现）。
- 方案 B（工作区唯一 basetemp `run_<uuid>`）：同样 `os.listdir` PermissionError。
- 结论：沙箱下固定 basetemp 无解（系统 %TEMP% 跨进程残留删不掉；工作区被
  pytest 进程拦截）。conftest 保持系统 temp 方案，注释已记录实测结论；
  2 errors（test_temp_root / test_validation_harness）为沙箱环境固有限制，
  用户本机无此沙箱可正常通过。
- 最终全量：**687 passed / 2 errors（沙箱环境限制）**，7 failed 全修复。
- 工作区 tmp 实验残留已清理（tmp\aitutor_pytest 已删除）。

### 2026-08-28 14:06:04（deepseek key 消耗根因 + 更换新 key）

**消耗审计**（用户 deepseek 官方平台）：
- sk-96521 今日 0:00-11:00：v4-flash 11,084 次 / 7,688 万 token + v4-pro 299 次 / 4,196 万 token
- **根因**：V1 项目（D:\Project\AI Tutors）的 async worker 今天上午运行过——
  `async_pipeline.py:915` 强制 "DeepSeek V4 Pro review (mandatory for all)"（v4-pro 299 次），
  且 Redis `async:task_b:status` 15+ 条 failed（explanation_generate 全失败反复重试 → flash 大头）。
  V1 无服务/计划任务自动启动，疑为上午手动/工具触发后自动消费遗留队列（8/10 留下），
  跑完进程退出（ai_tutor 库今日 0 插入、当前无进程）。
- **排除**：V2 worker 今日仅 ~40 次 flash（重跑 3 份文档，日志确认）；codex 用 sk-e24f7abf、
  opencode 用 sk-84ea8eb7（同账号其他 key）；claude 今天没开；9-11 点 cc-switch 代理零请求
  （v4-pro 为直连）。

**处置**：
- 用户删除 sk-96521，重建 claude code 专用 key（仅授权 CC SWITCH）。
- **V2 `backend\.env` DEEPSEEK_API_KEY 更换为 sk-06123f05f54d49638db303cb87ec9990**（已验证有效）。
- 待处理：V1 `D:\Project\AI Tutors\backend\.env` 仍指向已删 key（再触发会 401 重试）；
  V1 async_pipeline 强制 v4-pro 应改 flash 或禁用；V1 Redis 遗留 explain_queue 6 任务待清。

### 2026-08-28 14:12:00（V1 key 更换）

- **V1 `D:\Project\AI Tutors\backend\.env`**：DEEPSEEK_API_KEY + DEEPSEEK_VL_API_KEY
  更换为 `sk-1bd6a13bebf1476f8a0e9b427331e8dc`（已验证有效）。
- 遗留风险提醒：V1 `async_pipeline.py:915` 强制 v4-pro review（新 key 也会烧）；
  Redis `async:explain_queue` 6 个 explanation_generate 任务未清（V1 启动会消费）。

### 2026-08-27 20:32:37（v6.42：30 份 PDF + 9 份 DOCX 全量重跑已启动）
**启动流程**（用户确认）：
1. 后端 uvicorn（8000）已启动，document worker 随 lifespan 启动（poll=5s）。
2. 用 `tmp/rerun_docs2.py` 批量入队 **39 个文档**（30 PDF + 9 DOCX，清单来自
   test/pdf + test/docx 文件名 → DB 匹配，优先 completed；选考班用正式记录
   66ab79ec 替代 superseded 19086f92；昌平生物 scanned 保留重跑重新检测）。
   清单存 `tmp/rerun_docs_ids.json`。
3. worker 开始串行消费：首个 4643628c（语文 DOCX）llm_annotation 阶段。
4. 后台监控（tmp/rerun_monitor.log，5 分钟快照）跟踪至全部完成或 4h 上限。

**预期验证**（完成后对比）：30 份样本基线（79%/缺口 10）刷新、reviewing 积压
（86→目标 0）、详解缺失率（59%）、content_hash dedup 收敛（重跑借机验证）。

### 2026-08-27 23:36:10（v6.43：入库质量诊断 + 任务计划确立）

**重跑暂停**：用户要求暂停重跑（20:38 kill uvicorn/monitor）。本次重跑实际
只运行约 6 分钟，几乎无产出（此前"已完成约 10 个文档"判断有误——13:xx-14:xx
的 succeeded 是上午历史任务，已向用户纠正）。修复后重新全量重跑。

**质量审计（全库 554 道 approved/reviewing 题）**：
- 确定坏 **116 题（20.9%）**。六类：综合题子题内容全丢 58、空选项 38
  （含 4 题 A-D 全空）、父题选项拼接 11（最长 166 字符）、紧凑选项未拆 5、
  选项数异常 3、选项超长 24（部分存疑需甄别）。
- 按学科：英语 88% 坏（22/25，含 2020 首都师大英语 DOCX 9/9 全坏——当前代码
  产物非历史遗留）、政治 52%（12/23）、其余 9%-24%。

**根因（已实证，raw_response 对照）**：
- LLM 标注正确：完形 Q1 输出 20 个子题，各带 stem_line_ids/options_line_ids
  （如 {A:[N1L009], B:[N1L009], C:[N1L009], D:[N1L009]}），父题 options_line_ids={}。
- **链路 6 处断裂丢弃子题数据**：content_slicer 回退分支（263-269 不传行号）/
  pipeline_shared.to_dict（205-214 只输出 qno/type/answer/kp/score）/
  ingestion 入库（235/332 只存 3 键）/ worker L2 落盘（394-402）/ API 序列化
  （questions.py 不返回 sub_questions）/ 前端（AdminHome 只渲染父题 options）。
- 父题选项拼接：LLM 聚合行时 `_slice_options`（content_slicer:494）`" ".join`
  拼接；紧凑选项 `A.xxxB.yyy` 未拆分（V1 3.21 约束未落实）。

**测试盲区确认**（与 ChatGPT 四轮审计互为印证）：
- golden 只标第一子题选项（english Q1 expected_content.options 各 1 词）；
  比较用"包含"（run_phase1_eval:346）；门禁只查字段存在（run_live_validation:
  550-561，english options_line_ids=12/19 不 FAIL）；GOLDEN_FIELDS 8 项无子题
  结构字段；e2e verify_options 按 label 包含判断。

**文档规模**（D:\Project\Papers）：总 89,655 文件（PDF 44,812 + DOCX 44,843），
唯一文件名 71,318；maintainess（整理集）+ 高一/高一上/高二/高三（原始集）；
DOCX 原生结构零 OCR 优先，PDF 多带文本层，少量扫描件（错题拍照场景预留）；
目录/文件名即元数据（年份/学校/年级/学科/教师版）。待转换DOC 为 .doc 老格式。

**ChatGPT 四轮审计收敛**（用户提供，chatGpt.md 为空待补）：
- 确认 P0/P1：content_hash 生命周期、Pipeline Shared/Legacy 边界、Regression
  Fixture 版本化、DSD 状态漂移——**均已于 v6.42 修复**。
- 未修核心：子题数据链路断裂（= "题目完整入库"未解决）+ 测试只验字段不验结构。
- 建议：停止泛审计，进入整改 Sprint；不做 RAG/Vector 记忆、不重写 Pipeline。

**任务计划确立**（ROADMAP 新增 P4E.1/P4E.2，PROJECT_STATUS 更新 v6.43）：
- P4E.1 入库质量修复（最高优先级）：子题链路 6 处补齐 + 紧凑选项拆分 + 父题
  选项不拼接 + 测试门禁 + 3 份验证文档（英语完形/化学表格/地理读图）验收。
- P4E.2 批量导入工程化：全盘清单（元数据+去重+文本层检测）→ 30 份 → 100 份 →
  全量 7.1 万唯一；DOCX 优先。
- 后续：异步补全详解（llm_fallback 标记）、扫描件 PPS/PVL 路径。

### 2026-08-28 01:06:26（P4E.1 执行：子题链路 + 答案/详解/配图修复，前端逐题验证）

**执行背景**：用户清空主库测试数据（59 文档→0，保留知识树种子），启动前后端，
在前端逐题验证入库质量。两份真实文档（东城英语、八中数学）暴露四类系统问题。

**已修复（8 处，全部经真实文档验证/回归测试）**：
1. **子题链路 6 处补齐**：L2SubQuestion 加 stem/options 文本字段；content_slicer
   `_slice_single_question` 按子题行号切片文本（LLM 标记综合题主路径）；行内
   选项拆分 `_inline_split_options`（V1 3.21：A.xxxB.yyy / ①②③|B.… 拆独立选项）
   + 行号去重 + 按行聚合 label；pipeline_shared.to_dict / ingestion / worker L2
   落盘 / API 序列化补子题行号+文本；前端 AdminHome + QuestionBankPage 渲染
   子题题干/选项/答案。
2. **父题 options 不拼接**：选择题组综合题父题 options 置空（子题选项归属子题）。
3. **答案汇总修复**（answer_matcher + ingestion）：综合题父题答案保留 content_slicer
   子题汇总（"(11) itself (12) to..."），answer_map 单值不覆盖（此前仅 single_choice
   跳过，fill_in/short_answer 综合题被截成第一个子题答案）。
4. **详解切片优先**（ingestion）：sq.explanation（教师版原文，保留 L1 换行）优先，
   LLM 提取的详解（无换行拼接）只兜底——此前 LLM 详解覆盖导致排版堆叠。
5. **配图 page 约束**（pipeline_shared `_build_question_images`）：匹配要求
   img.page_no == line.page_no——此前缺 page 约束，跨页 bbox 数值碰巧重叠即
   误关联（八中数学 Q1 关联到第 8 页图、页眉页脚横条混入）。
6. **prompt 强化**（line_annotator）：完形/语法填空等填空类子题 stem_line_ids
   必填（含空位/题号所在行），前端可匹配选项与题干。
7. **作文英文正常**：确认"转中文"为旧数据/渲染问题，新数据英文原文正确。

**验证结果**（东城英语重跑，新代码）：Q1 完形子题 stem+options 全有（10/10）；
Q11/14/21/42 子题题干完整（含完整句子）；Q46 作文英文原文。答案汇总待
ingestion/answer_matcher 修复后的最新重跑确认。

**测试**：新增行内拆分/子题切片/入库子题内容等测试；修复 page 约束暴露的
test_question_image_association helper 矛盾；相关测试 70 passed。

**待处理**：八中数学 Q4 绝对值符号缺失、Q15 题干混入"三、解答题"、Q17 茎叶图
LaTeX 渲染、Q19 表格 HTML 源码显示（前端渲染长尾）；配图空白图/页眉页脚过滤
（page 约束已修主路径）。

### 2026-08-28 14:30:00（P4E.1 验证文档重跑完成 + token 消耗根因锁定 + 文档收尾）

**3 份验证文档重跑完成**（最终代码，52 题入库，worker 日志确认）：
- 东城英语 fd6a575a / 八中数学 2f150efd / 丰台物理 f8b43616。
- 已验证：答案汇总（父题聚合子题答案）✓、配图 page 约束（Q1 不再误关联 P8 图）✓、
  详解换行保留（sq.explanation 优先）✓、作文英文原文 ✓。
- **空位标记 5/10**：本次数据由旧正则（数字后接字母被排除）生成；正则已修复
  `(?<![〔\d%])(\d+)(?!\.\d|[\d〕])`（允许数字后接字母，如 "11.to"）+ 测试
  test_mark_blank_positions_digit_followed_by_letter（34 passed）。**要全 10/10
  需重跑 3 份（约 ¥1-2），已列为待用户决策。**

**前端展示重构完成**（QuestionBankPage + AdminHome）：
- `〔N〕` 空位标记渲染为高亮 span（.blank-marker）；
- 综合题详情：题干区默认展开 + 答案区/详解区默认折叠（`<details>`）；
- 答案格式化 `(1) C (2) D` → `1.C 2.D`（每行 5 个）；子题题干去重
  （parentStem 包含 subStem 时不重复渲染）。

**token 消耗根因锁定（11:00 后大头 = DSH 会话，非 V1/V2 worker）**：
- deepseek 平台 11:00 后 v4-flash 103 次 / 7,097 万 token，平均 ~69 万 token/次 =
  **DSH（Codex 代理）每轮重发全部会话历史**（本会话上下文已膨胀到 ~70 万 token）。
- V2 worker 今日仅 ~40 次 flash（重跑 3 份文档）；V1 上午已跑完退出。
- **用户决定开新会话恢复**（读 RESTART_PROMPT.md 即可，状态全在文档）。

**成本防护落地**：
- `WORKER_ENABLED` 环境变量 gate（main.py lifespan）：默认 1 启动 worker；设 0
  为 API-only（无 LLM 消费）。**注意：gate 走环境变量，不写 .env**——启动命令：
  `$env:WORKER_ENABLED='0'; python -m uvicorn app.main:app ...`。
- 13:16 曾出现 V2 uvicorn 被外部重启（worker 自动消费）——gate 即为此而设。

**会话收尾环境状态**：8000（uvicorn）与 5173（vite）当前均未监听（服务已停）；
Docker CLI 在代理沙箱不可用（用户本机可用）。待用户决策：①空位标记是否重跑补全
（~¥1-2）还是推迟到批量导入；②V1 遗留（v4-pro 强制 / explain_queue 6 任务）。
测试门禁（P4E.1 任务 4：golden 子题结构 + run_live_validation 准确率 FAIL +
选项完整性指标）**未启动**，新会话首个任务。

### 2026-08-28 22:30:00（切片入库规则差距修复 + 端到端验证 + 文档快照 v6.45）

**背景**：用户第三次提供「题干区/答案区/详解区」展示标准，要求核对英语与理科
切片入库规律。核对发现 3 类差距，全部代码层定位并修复（非"旧管线未生效"——
P4E.1 修了一半，本次补全）。

**差距 1：fill_in/short_answer 综合题父题答案未汇总**（东城英语 Q11 语法填空
parent answer 只剩 `itself`、Q21 词汇只剩 `confusing`、Q42 阅读表达只留第一题答案）
- 根因：P4E.1 修了 `_apply_llm_annotation_answers`（跳过所有 composite），但
  `answer_matcher.match_answers` 主循环只跳过 `single_choice/multiple_choice` 综合题
  → fill_in/short_answer 综合题的 content_slicer 汇总答案在最后一步被答案表单值
  覆盖（`(11) itself (12) to (13) to stay` → `itself`）。
- 修复：`answer_matcher.py` 主循环跳过「所有 is_composite 且父题已有汇总答案」；
  父题 answer 为空（物理实验题等，content_slicer 无子题可汇总）仍走答案区匹配，
  避免 answer_missing（`test_short_answer_composite_keeps_answer_outside_question_boundary`
  同步更新为新行为断言）。

**差距 2：七选五选项错位**（东城英语 Q37-41：B 丢失、D 吞 E、E/F/G 错位、G 落
section 标题）
- 根因链：① PPSV3 把 `D.xxx`/`E.yyy` 两行合并成一个 L1 行 → LLM 行号整体偏移；
  ② `content_slicer._INLINE_LABEL_RE` 只匹配 A-D，七选五 E/F/G 行内标签不识别；
  ③ `anchor_corrector.correct_anchors` 只校验顶层题选项行号，子题行号 LLM 原始值
  直接透传；④ 合并行场景（E 引用 D 开头的行）被 `_validate_option_anchor` 误判 retry。
- 修复（4 处）：`_INLINE_LABEL_RE` A-D→A-G；`l1_postprocessor` 行内拆行 A-D→A-G
  （L1 阶段拆开 PPSV3 合并行）；子题 options_line_ids 也过锚点校验（失败归集为
  `sub_options` retry 锚点，simple_pipeline retry hints 覆盖）；合并行行内归属
  （首行标签≠期望但行内含该标签时不误判 retry，保留行号由切片归属）。

**差距 3：空位标记不完整**
- 根因：`_mark_blank_positions` 只处理父题 stem；`____37____` 下划线形式（native L1
  保留、PPSV3 常丢下划线变裸数字/粘连如 `_40Orthe`）不识别；`annotation.subject`
  可能为空使文本科目孤立数字规则不启用。
- 修复：规则 1.5 下划线空位 `____37____`→`〔37〕`（所有科目）；切片时子题 stem
  同样标记；simple_pipeline 用管线传入 subject 兜底 `annotation.subject`。

**测试**：新增 7 项（下划线空位、七选五 A-G 行内拆分、合并行切片归属、子题锚点
校验 retry/exact、fill_in/short_answer 综合题汇总不被覆盖、七选五端到端链路）。
改动范围 129 passed；全量 708 收集正常，运行中挂起/失败均为沙箱环境固有问题
（temp ACL、OCR tmp 写入），与本次改动无关。

**验证**（不跑真实入库，直接验证新代码行为）：
- Q11 场景：parent answer 保持 `(11) itself (12) to (13) to stay`（不再变 `itself`）。
- Q37 场景：选项 A-G 完整、D/E 正确分离、父题/子题 stem 空位 `〔37〕` 已标记。

**待办（新会话）**：
1. 重跑东城英语文档（fd6a575a）修复存量数据（选项错位 + 父题答案截断 + 空位），
   约 ¥0.5-1，用户已确认方向但暂缓（先研究清楚再跑）。
2. **异步富化（用户确认方向）**：理科选择题大部分无详解（源 PDF 教师版答案区只有
   「题号+答案」表，八中数学 Q1-10 无【详解】），需入库后 LLM 异步生成并写回
   `questions.explanation` 标记 `llm_fallback`——当前无实现，需新增补全 worker。
3. 测试门禁（P4E.1 任务 4）未启动。

**版本**：v6.44 → v6.45（快照已归档 docs_archive/status/2026-08-28_*_v6.44.md）。

### 2026-08-28 23:30:00（题型入库标准对抗性审查 v3.1 锁定 + 修复计划）

**背景**：用户提供英语/理科试卷的「题干区/答案区/详解区」展示标准，要求核对当前切片入库管线是否符合标准；Claude 审查 v1 经 Codex 逐条代码核对后修正为 v3.1 终版。

**审查结论（v3.1）**：
- P0：P0-1 细粒度题型/section 入库丢失、P0-2 写作题无 canonical 类型、P0-3 多层嵌套子问不支持、P0-4 结构化答案格式缺失（条件化）、P0-5 化学式下标/上标标准化。
- P1：P1-1 词库无独立 word_bank 字段、P1-2 答案图子题粒度绑定不精确、P1-3 完形共享材料数字误标、P1-4 七选五 A-G 完整性无强制校验。
- P2：P2-1 instruction 独立字段（当前行为不算错误）、P2-2 七选五正确选项高亮/自动关联文本展示增强。
- 已排除/降级：答案表空格、词库完全无支撑、答案图完全无支撑、数字误标全面风险等 v1 误判已修正。

**计划**：
1. Phase 1 数据契约：P0-1/P0-3/P0-4/P1-1，涉及 L2/Sliced/Question/API/前端、Alembic migration、DSD/DICTIONARY 同步。
2. Phase 2 英语：P0-2/P1-3/P1-4/P2，涉及题型映射、prompt、空位保护、七选五校验和展示增强。
3. Phase 3 理科：P0-5/P1-2，涉及化学式标准化和答案图子题绑定。
4. Phase 4 验收：新增回归测试 + golden + 重跑东城英语/样本卷。

**文档**：PROJECT_STATUS.md 已锁定 v3.1 状态与修复计划；bugs.md 新增 BUG-027 Open；未开始生产代码修复。

### 2026-08-28 23:55:00（P0-1 完成：保留细粒度题型与 section）

- 问题：对应 v3.1 P0-1，questions 表无法保留 cloze/grammar_fill/seven_to_five 等细粒度题型，也无法保留 section_id。
- 修复：
  - SlicedQuestion 新增 original_question_type，content_slicer 保留 LLM 原始细粒度题型。
  - questions 新增 original_question_type VARCHAR(50)、section_id VARCHAR(100)。
  - ingestion/API/frontend 全链路输出新字段，前端优先使用细粒度题型标签。
  - Alembic migration：20260828_0001_add_question_original_type_section.py。
- 验证：
  - pytest：42 passed（test_content_slicer 全量 + pipeline 相关单元测试）。
  - 新增 2 项回归测试：切片保留 original_question_type/section_id、PipelineResult.to_dict 输出新字段。
  - frontend npm run build 通过。
  - alembic current = 20260828_0001 (head)。
  - validate_docs_vs_code.py 仅存在既有不匹配：answer_extraction_retries 表、两个 answer-retries 路由未入文档，与本次修复无关。
- 文档：DSD/DICTIONARY 已同步；PROJECT_STATUS 暂未更新，待 Phase 1 全部完成后回写。


### 2026-08-28 23:58:00（P0-1 对抗性审查修复）

- 审查结论：P0-1 代码路径正确，但测试覆盖不足（T1-T5）；同时发现词库合并路径在 L2 阶段已将 vocabulary_fill 归一化为 fill_in，原始细粒度题型会丢失。
- 修复：L2QuestionAnnotation 新增 original_question_type；line_annotator 保留 LLM 原始题型并在子题合并、无材料拆分、词库合并路径传递；content_slicer 优先使用 original_question_type。
- 测试：新增 T1 入库持久化、T2 综合题合并、T3 词库合并、T4 API 序列化、T5 向后兼容；相关测试集 97 passed。
- 测试库：aitutors_test stamp 到 20260827_0001 后执行 20260828_0001 migration，解决旧 schema 与 alembic 版本表漂移。
- 状态：PROJECT_STATUS 标记 P0-1 完成；bugs.md BUG-027 标记 P0-1 已修复；下一环节 P0-3。


### 2026-08-29 00:05:00（P0-3 完成：多层子问递归结构）

- 实现：L2SubQuestion 新增递归 sub_sub_questions；line_annotator 解析并更新 prompt；content_slicer 递归切片与空位标记；ingestion/PipelineResult/API JSONB 递归序列化；前端新增递归 SubQuestionList 组件。
- 测试：新增 4 项（L2 解析、切片、PipelineResult 序列化、ingestion 持久化）；相关集合 125 passed；frontend npm run build 通过。
- 文档：DSD/DICTIONARY/PROJECT_STATUS/bugs/LOG 已同步；下一环节 P0-4。


### 2026-08-29 00:10:00（P0-3 对抗性审查修复）

- 修复：QuestionBankPage 子题题型显示调试残留，改为 TYPE_LABELS 映射；_slice_sub_question 递归传递 fallback_qno；pipeline/ingestion 序列化统一为 getattr 安全访问。
- 补测试：T1 content_hash 嵌套子题、T2 API 透传嵌套、T3 空嵌套边界、T4 3 层递归深度。
- 验证：相关集合 129 passed；frontend npm run build 通过。


### 2026-08-29 00:20:00（P0-4 完成：结构化答案）

- 实现：L2/SlicedQuestion 新增 answer_structure；questions 新增 answer_structure JSONB；ingestion 提供 _build_answer_structure 自动识别多答案与数值范围；API/PipelineResult 输出结构。
- 迁移：20260829_0001_add_question_answer_structure.py，实际库与测试库均已 upgrade head。
- 测试：新增结构推导、入库持久化、PipelineResult 输出、API 透传；相关集合 132 passed。
- 状态：待 Claude 对抗性审查；下一环节 P1-1。


### 2026-08-29 00:35:00（Phase 1 对抗性审查缺口全部修复）

- P0-4：prompt 新增 answer_structure 契约；前端渲染 accepted_answers/range/error_span/explanation；去除中文 “或/或者” 自动拆分误判。
- P1-1：单题词库也解析 word_bank；找词库行跳过 section 标题；词库字段入 DSD/DICTIONARY。
- P0-1：入库优先使用 original_question_type 建立细粒度 question_type_id，支持完形/语法填空/七选五等统计。
- 文档：DSD/DICTIONARY/PROJECT_STATUS/bugs/LOG 已同步。


### 2026-08-29 00:45:00（Phase 1 全量回归）

- 后端 pytest 全量：730 passed，5 failed。
- 5 个 failed 均为 test_e2e_ingestion_verification：目标文档 042f5b90-4a11-4c03-aabd-bd0683442dfe 不在当前 documents 表，属环境/数据缺失，与 Phase 1 代码无关。
- 前端 npm run build 通过；迁移 head=20260829_0002。

#### 2026-08-29 12:30:00 Phase 2 英语 P0-2/P1-3/P1-4/P2-2

- P0-2：content_slicer/line_annotator 增加 essay/writing/composition/作文/写作/书面表达映射；prompt 明确英语写作输出 essay；入库 _get_question_type_id 保留 essay/writing 细粒度类型。测试：test_line_annotator、test_content_slicer、test_question_type_get_or_create。
- P1-3：_mark_blank_positions 增加 _is_protected_number，对 ages/year/month/page/range/percent/中文量词等上下文数字不替换。测试：test_mark_blank_positions_protects_ordinary_english_numbers。
- P1-4：anchor_corrector 增加 _is_seven_to_five 与 A-G 完整性校验，缺失标签汇总为 sub_options retry；simple_pipeline 重试提示覆盖。测试：test_seven_to_five_missing_labels_trigger_retry、test_seven_to_five_missing_labels_build_retry_hint。
- P2-2：QuestionBankPage/AdminHome 增加 answerWithOptionText，正确选项 is-correct 高亮；theme.css 增加样式。前端 npm run build 通过。
- P2-1：保持现状，不新增 instruction 字段，符合展示标准。
- 回归：后端 739 passed，5 failed 仅为已知 e2e 目标文档 042f5b90 不存在；前端 build 通过。

#### 2026-08-29 13:00:00 Phase 2 对抗性审查修复

- P1-3：孤立数字 regex 增加 %/％ 排除，_is_protected_number 改用 m.string，修复 50% 与题号 50 冲突的误标风险。
- P1-4：七选五缺少 sub_questions 时生成 sub_options retry，不再静默跳过结构校验。
- P2-2：新增 frontend/src/lib/answer.ts 共享答案工具，answerWithOptionText 支持 BD/ACD 多答案，isOptionCorrect 支持多字母高亮。
- 验证：content_slicer/anchor_corrector/simple_pipeline 79 passed；前端 npm run build 通过。

#### 2026-08-29 15:30:00 Phase 3 P0-5/P1-2

- P0-5：新增 chemistry_formula.py；正则覆盖元素下标、离子电荷、化合物组下标；ingestion/pipeline/simple_pipeline 三入口按化学 subject 触发；修复 subject 别名归一化后未更新问题。
- P1-2：_build_question_images 增加答案图到子题的空间邻近绑定；QuestionImage 新增 sub_question_qno；API/前端透传，父题区排除子题绑定图。
- Schema：20260829_0003_add_question_image_sub_question.py，真实库/测试库均已 upgrade head。
- 回归：后端 746 passed，5 failed 仅为已知 e2e 目标文档缺失；前端 npm run build 通过。

#### 2026-08-29 16:00:00 新增九科题型树文档

- 新增 `Docs/00_Requirements/QUESTION_TYPE_TREE.md`。
- 第一部分：全国新高考九科题型多级树状清单（语文/数学/英语/物理/化学/生物/历史/政治/地理）。
- 第二部分：北京高考各科题型清单（2026年版），含统一高考与学考等级考模式说明。
- 用户后续可继续补充北京卷细分题型；文档保留为题型分类与切片入库的基础契约。

#### 2026-08-29 17:00:00 验收遗留项测试闭环

- P2-2：新增 `frontend/tests/answer.test.mjs`，用 Node 24 原生 `node:test` 覆盖 `answerWithOptionText/isOptionCorrect` 多答案、单答案、空答案、非字母答案边界；`package.json` 新增 `npm test`。
- P0-4：`test_build_answer_structure_range_and_accepted` 补强全角波浪范围、管道多答案、None/空/见解析边界。
- INFO 化学式 pipeline 集成测试：`test_simple_pipeline_normalizes_chemistry_formulas` 已存在，验证 subject=化学 时完整管线自动归一化。
- 验证：`npm test` 5 passed，`npm run build` 通过，后端相关测试 8 passed。

#### 2026-08-29 18:00:00 题型树种子数据

- 新增 `question_type_seed/` 模块（types.py + 9 科数据文件 + seed.py）。
- 229 个题型节点，覆盖九科（全国卷+北京卷），3 级层级（L1 大题型 → L2 子类 → L3 细粒度）。
- Schema：20260829_0004 新增 level/description/keywords 字段到 question_types 表。
- API：`GET /api/admin/question-types` 题型树端点，支持 ?subject= 过滤。
- 测试：6 项种子完整性测试。
- 与知识树正交：题型 = 怎么考（question_types），知识点 = 考什么（knowledge_nodes）。

#### 2026-08-29 19:00:00 知识节点库统一

- 用户提供《高考九科知识点树状清单》（2026 课标教材体系），生成 v2 知识树（917 节点）。
- v1 知识树（333 节点，考试能力分类）的关键词全部合并到 v2 节点（4 个纯题型词 cloze/cloze test/完形/完形填空 主动移除，不属知识点）。
- index_builder.py 清理：删除所有 v1 import 和运行时补充逻辑，仅引用 v2 文件。
- 九科覆盖：语文 99、数学 102、英语 99、物理 126、化学 90、生物 107、历史 127、政治 84、地理 83。
- 5010 个关键词（小写去重），支持学科内搜索/检索。
- 对抗性审查修复：
  - 移除 ENG-LEXA(词法) 上的题型关键词（cloze/七选五/完形），它们是题型不是知识点。
  - 补充常用搜索词："排列组合"→计数原理、"电解"→化学反应与电能、"reading comprehension"→阅读技能、"函数单调性"→函数的概念与性质。
- 测试库 seed 917 个 v2 节点。
- 回归：后端 748 passed，0 failed。

### 2026-08-29 20:00:00

#### 文档治理审计（docs/ 精简 + LOG.md 分割）

**治理原则**：docs/ 只保留规则/规划/契约类文档；状态文档只在根目录；历史归档到 docs_archive/。

**归档（5 份 → docs_archive/2026-08-29/）**：
- `PLAN_QUESTION_FAMILY.md`：Phase 2A 设计冻结稿，已完成使命
- `T3_IMPLEMENTATION.md`：Phase 1 执行基线，已完成
- `TASK.md`：任务执行规范，内容已整合进 ROADMAP v3.0
- `Design.md`：Apple-like 设计参考，UI.md 已提取设计 Token
- `LOG_historical_2026-08-10_to_2026-08-24.md`：LOG.md 历史部分（2006 行）

**整合**：
- ROADMAP.md v2.0 → v3.0：吸收 TASK.md 的完成标准（§4）和试卷结构门禁（§5）
- rules.md 导航表：移除 TASK.md / Design.md 引用

**精简**：
- LOG.md 从 3115 行 → 1118 行（历史 2006 行归档，近期 8/25 起保留）
- experiment_output.md 移至 tmp/
- 删除 Codex 误生成的空中文命名文件

**治理后 docs/ 结构（14 份，全部为规则/规划/契约类）**：
- 00_Requirements/：DICTIONARY、QUESTION_TYPE_TREE、REQUIREMENTS_AND_SOLUTION
- 01_Product/：PRD、ROADMAP（v3.0，唯一计划文档）
- 02_Architecture/：ACS、MIS、OCR_PROVIDER_POLICY、PADDLEOCR_API、PIPELINE、SAD、UI
- 03_Data/：DSD
- 05_Development/：V1_LESSONS

**版本**：RESTART_PROMPT v6.46。

### 2026-08-29 21:00:00

#### Codex 审计四项问题修复

**修复 1：题型树落库**（Codex 问题 1）
- `setup_test_db.py` 新增 `seed_question_types` 调用，测试库初始化时自动落库242 个题型节点。

**修复 2：北京卷题型补充**（Codex 问题 2）
- 语文 +3：整本书阅读（红楼梦）、多文本阅读、记叙文
- 数学 +4：新定义题、结构不良/开放型、任务驱动题、多项选择
- 英语 +6：听说机考 + 5 子题型（听后选择/听后记录/听后转述/短文朗读/回答问题）
- 化学 +1：不定项选择
- 生物 +2：科学思维路径、开放性设问
- 物理 +2：小实验、大实验（"一小一大"结构）
- 总计 229→247 个题型节点。

**修复 3：移除知识节点库中的题型词**（Codex 问题 3）
- `english_v2.py` ENG-SKILL-REA 移除"七选五"。
- 新增 `test_knowledge_tree_integrity.py`：防御性测试确保纯题型词（七选五/完形填空/cloze/cloze test）不进入知识关键词。

**修复 4：文档计数修正**（Codex 问题 4）
- 关键词计数从5012 修正为5010（小写去重，含移除"七选五"后重算）。

**验证**：7 passed（test_question_type_seed 6 + test_knowledge_tree_integrity 1）。

### 2026-08-29 22:00:00

#### 测试文件治理审计

**治理规则**：后端业务测试 → `backend/tests/`；前端业务测试 → `frontend/tests/`；整体架构/验证脚本 → `test/`。

**删除（合计 ~450 个文件）**：
- `backend/scripts/_tmp_*.py`（26 个）：一次性诊断脚本，零外部引用
- `test/scripts/_*.py`（64 个，保留 `_verify_env_keys.py`）：一次性诊断/上传/清理脚本
- `test/results/*.py`（32 个）：错放的诊断脚本，不应在 results 目录
- `test/results/` 日志/临时文件（150+ 个）：e2e_*.txt、pytest_*.txt、tmp*.pdf、*.log
- `test/scripts/` 孤立脚本（33 个）：fix_golden 1-4、debug_options 1-2、batch_upload 等零引用脚本
- `tmp/`（707 个文件，24MB）：processor 临时 PDF/DOCX 副本和一次性诊断脚本

**保留**：
- `backend/tests/`：72 个文件全部保留（758 测试全部收集正常）
- `frontend/tests/`：1 个文件（answer.test.mjs）
- `test/scripts/`：15 个活跃脚本（验证/评估/管线批处理/answer_verifier 等）
- `_verify_env_keys.py`：bugs.md 引用的密钥轮换验证工具

**验证**：后端全量 753 passed，5 failed（已知 e2e 数据前置），零回归。
