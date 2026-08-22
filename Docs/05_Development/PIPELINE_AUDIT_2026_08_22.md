# 入库管线数据质量审计报告（2026-08-22）

> 背景：30 份教师版 PDF 全流程真实入库验证（23 份完成、444 题入库）后，发现三个数据质量问题：
> 1. 英语综合题切分混乱（共享材料整段并入每题题干、跨题截断）
> 2. 部分题目 LaTeX 公式无 `$...$ 包裹（原样显示）
> 3. 配图覆盖率低（23 卷提取 1426 张图，仅关联 221 张，15.5%）
>
> 本报告对入库管线各阶段做「实现 → 问题 → 证据」逐层审计（4 个并行审计单元 + 真实 DB 数据证据交叉印证）。

## 一、LLM 标注模块（line_annotator.py）审计结论

### Q1：prompt 是否要求行号而非原文
- 规则1（L456）全部字段为行号/元数据；规则10（L485）禁止输出题干原文 —— 方向正确
- **问题**：规则7a（L469）强制 stem_markers 从文档"原样复制"题干首尾子串；规则2a（L462）要求 structure_signature.condition "从题干原文保留文本" —— 两个必填通道强制 LLM 抄写含 LaTeX 原文进 JSON，与模块 docstring（L12）宣称遵守的 V1_LESSONS 3.1/3.16（JSON 不含 LaTeX 命令）自相矛盾，且无来源记录

### Q2：题型规范
- 规则1（L456）给出 canonical 枚举且必填；但综合题格式（L515）又要求"保留原始题型（cloze/reading/grammar_fill/seven_to_five）" —— 两套词汇矛盾
- `_canonical_question_type`（L93）对未命中值原样透传，无白名单校验；缺失默认 "unknown"（L705）

### Q3：难度字段（→ 88% difficulty NULL 根因）
- **规则2（L457）明确标注 difficulty 为"可选字段"**，除 1-5 范围外无任何判断依据
- 代码 L743 原样透传、无默认值无类型强转（对比 question_extractor.py L195 有 _int_or_none）
- 全链路无回填：ingestion.py L262 直写 DB nullable 列；retry hints 不校验难度
- **结论：LLM 大概率省略 → 无默认值 → DB NULL**

### Q4：LaTeX 公式约定（→ 公式不包裹根因）
- **prompt 全文无任何 `$...$` 包裹规则**（grep 仅命中 docstring 与 JSON 示例各一处）
- 规则7a"禁止改写/补全/归一化" + content_slicer._slice_lines（L410-420）verbatim 切片 → L1 无 `$` 公式一路原样入库
- **结论：公式不包裹是 prompt 无规则 + 禁止改写 + verbatim 切片的确定性结果**

### Q5：综合题/共享材料（→ 英语材料并入题干根因）
- 字段 is_composite/sub_questions/shared_material_line_ids 均有定义（L466-467, L488-527）
- **L518 明文要求综合题 stem_line_ids = "材料全文 + 所有子题行号"** —— 材料并入题干是 prompt 设计而非 LLM 违规
- 对独立题无"stem 不得含材料行"约束；_split_no_material_fill_composites（L309）拆分时每个子题复制完整原 stem，材料进一步扩散
- content_slicer 的 Layer-2 合并只按 shared_material_line_ids 触发，LLM 漏标时材料被固化进每题

### Q6：解析逻辑
- _validate_line_ids（L798-810）静默丢弃字段内无效条目（全无效时 stem 空列表仍进入 L2 无标记）
- difficulty/score 无类型校验（可入库 "中等"/3.5）；knowledge_points 为字符串会污染合并路径；sub_questions 元素非 dict 时解析崩溃；answer 非字符串静默置 None；stem_markers 只 strip 不校验原文

### 根因映射总表（line_annotator 层）
| 已观测缺陷 | 根因 | 机制 |
|---|---|---|
| 88% difficulty NULL | prompt L457"可选字段" + 无依据 + 透传无回填 | LLM 省略 → DB NULL |
| 公式无 $ 包裹 | prompt 无规则 + L469 禁止改写 + verbatim 切片 | L1 无 $ 公式原样入库 |
| 材料并入题干 | prompt L518 明文要求 + L309 拆分复制 | 设计使然 + 代码放大 |

## 二、内容切片模块审计结论（content_slicer.py + semantic_anchor.py + anchor_corrector.py）

### A. 材料并入题干 — 三重叠加（切片器主动行为 + Prompt 设计 + 锚点范围）
- 合并路径 L210-218：`all_stem_lines = 材料行 + 各子题 stem 行` → `_slice_lines` 拼接（材料显式并入）
- LLM 标记路径 L350：`stem = _slice_lines(question.stem_line_ids)`，而 Prompt L518 要求 stem_line_ids 含材料全文
- 锚点范围从材料首行起（semantic_anchor L437-440）
- 全程无任何代码把 shared_material_line_ids 从 stem 剔除

### B. 跨题截断（独立代码 bug 路径）
- semantic_anchor L331-336：题型归为 single_choice（cloze/reading→single_choice）且材料后存在首个 `A.` 选项行时，`end_order = first_option - 1`，**无视 LLM 的 end_marker/完整 stem_line_ids**
- 无标记时 resolve_composite_stem_range L456-457 同样以 first_option-1 截断
- anchor_corrector L295-318 覆盖回写 stem_line_ids → 材料 + 首道子题入 stem，后续子题被切（"跨题截断"）
- 若选项与题号同行则 first_option=None 不截断 → 同一题型因排版不同行为分裂

### C. LaTeX 全链路零规范化
- _slice_lines（L410-420）原样取 line.text；native_markdown/ocr_l1_converter/l1_postprocessor 均不触碰公式
- 证据：二十中数学 fixture L32 题干有 `$`、L37-43 选项行无 `$`（OCR 输出即如此）→ 切片原样透传

### D. 选项解析缺陷
- _strip_option_label 只剥行首标签（^A. / ^（A）），单行多选项未切开时（E/F/G 七选五 L1 正则只支持 A-D）label=B 的 text 混入 `A. x B. y` 整行
- 跨行选项以空格 join（L439）无换行分隔
- sorted(labels) 字母序，中文/异常 key 顺序不可控

### E. 合并综合题答案丢失（新发现）
- _slice_single_question 构造 SlicedQuestion（L389-407）**不传 answer/answer_line_ids/explanation_line_ids**（恒 None/[]）
- _merge_question_group L233-237 用 q.answer 拼 merged_answer → 恒 None；all_answer_lines=[]（L259-270）
- answer_matcher by_number（题号→标注）只回填第一道子题 → 其余子题（如 12-20）答案/详解丢失
- 与 schemas_l2.py L5-6 注释"LLM 直接输出 answer_line_ids，代码按行号切片"承诺不符

### F. 其他
- _validate_shared_material_sections（L319-324）是空实现，section 校验完全交给 LLM
- 无标记综合题 stem 边界缺失时（无 end_marker/无 next_q/无选项/无答案区）hard_boundary=文档最后一行（semantic_anchor L310-321）→ stem 吞到文档末尾

## 三、答案匹配与质量门审计结论（answer_matcher.py + quality_gate.py）

### A. 答案匹配
- "matched line question number mismatch" 日志出自 `semantic_anchor.py` L112（**stem marker 解析，非答案表**）：候选行行首题号 ≠ 目标题号 → 候选被拒 → stem 回退 LLM 原始 stem_line_ids，**不直接改答案、不降置信**
- "llm_answer_slice_suspicious" 仅告警，回退 LLM 原文后 provenance 仍为 llm_annotation 0.9

### B. 质量门（为何切分异常仍 0.9 approved）
- **confidence 是纯结构打分**（1.0 起扣），检查项：锚点状态/题干空/选项数量/答案来源/答案可疑/答案缺失
- **从不校验**：答案正确性、公式完整性、stem 长度/材料混入（L143-144 自述"无法可靠判断共享材料，不做此检查"）
- 0.9 = 1.0 - 0.1（详解依赖 LLM 兜底）

### C. 英语综合题材料并入仍 approved 的完整路径
1. prompt L518：综合题 stem_line_ids = 材料全文 + 子题行号（设计如此）
2. `_slice_single_question` 直接拼接 → stem = 整段材料
3. `_validate_stem_anchor` 对 composite **豁免首行题号校验**（L158-168）
4. quality_gate 只查 stem 非空（L82-84），无 stem 长度/材料混入检测
5. 语法填空（fill_in）无选项检查即过；被错拆的阅读单选带选项也过
6. 0.9 >= 0.8 且无"禁止自动发布"且答案非空 → ingestion approved（ingestion.py L169-191）

### D. quality_gate confidence 过度乐观 —— 证据
- **0.9 的来源是"详解缺失"扣分，而非质量证明**：score=1.0 - 0.1（详解依赖 LLM 兜底）= 0.9；英语答案区通常无详解 → 必扣 → 稳定 0.9
- **provenance.confidence 几乎不参与总置信度**（全库仅 quality_gate L110-113 一处使用）；document_answer_table 命中即 0.95，只要无四种字符特征（PUA/替换符/裸 LaTeX/公式符号丢失）就通过，题号映射错也不降级
- 题干维度只查空（L82-84），无长度上限/材料混入检测（L143-144 自述放弃）
- **结论：0.9 approved 是"入库结构合格"信号，不是"内容正确"信号**（设计取向，但题库质量上过度乐观）
- "材料并入+0.9 approved"只发生在：题型为 fill_in（无选项检查）或被错拆成带完整选项的独立单选 —— 两条路径质量门都看不到题干异常

### E. 缺失检测点（quality_gate 中不存在）
1. stem 长度/行数上限或材料占比检查
2. stem 与材料行重叠检测（shared_material ∩ stem）
3. non-composite 题 stem 含共享材料行 → 可疑
4. 答案与题号反查一致性（答案表命中行是否确为本题题号行）
5. provenance.confidence 参与总置信度

## 四、入库模块与配图关联审计结论（ingestion.py + pipeline.py + simple_pipeline.py）

### A. 题型落库（423 题 question_type_id 全 NULL）— 根因链确认
- `_get_question_type_id`（L540-550）精确按 `QuestionType.code` 查表，**查不到返回 None 且不创建**
- **全仓库无任何 question_types 写入路径**：seed_knowledge_tree.py 只种 Subject+KnowledgeNode；alembic 只建表；`KnowledgeService.create_question_type`（service.py L41-57）定义了但**业务流程从不调用**；API 只读
- `sq.question_type` 是合法 canonical 枚举（非解析失败）
- **结论：缺种子数据 + 入库不兜底创建**，非解析问题

### B. 难度落库 ✅
- L262 `difficulty=sq.difficulty` 全程直传无变换，DB 56 == L2 56 吻合

### C. 答案合并 ⚠️
- LLM answer_map 优先于切片答案（L176-183）——**绕过 answer_matcher 对 V1_LESSONS 3.8「教师版答案不被 LLM 覆盖」的保护**（设计张力，非错误）

### D. 配图覆盖率低（数学 80/105、化学 99/115、生物 81/92 无图）— 核心根因

**硬伤①（可证明的代码级 bug）**：`_build_question_images`（pipeline.py L1006-1098）读行号方式与生产数据结构不匹配：
```python
for lid in (getattr(q, "stem_line_ids", None) or []):     # L1051 → SlicedQuestion 无此属性 → []
opts = getattr(q, "options_line_ids", None) or {}          # L1061 → 无此属性 → {}
for lid in (getattr(q, "answer_line_ids", None) or []):    # L1073 → 唯一有效路径
```
- `SlicedQuestion`（schemas_l2.py L142-179）**没有 stem_line_ids/options_line_ids 属性**，行号在 `stem_anchor.corrected_line_ids` 与 `corrected_anchors`
- pipeline.py 自带 `_question_field_line_ids`（L788-799）但 `_build_question_images` 没用它
- 单测全绿因 test_phase2_fixes.py 用 MagicMock 暴露假属性掩盖真实结构

**硬伤②**：图片中心点 ∈ 行 bbox ±20px 的判定（L1038-1098）比 docstring 声称的「bbox 重叠」严格得多，试卷大图中心常落行间空白 → 永不命中

**提取缺图③**：simple_pipeline canonical 文档 `images=list(ppsv3_doc.images)`（L280）——**native 图片（PyMuPDF xref 精确 bbox）被整体丢弃**；PP 图片 bbox 靠文件名正则解析（paddle_client L508-518），命名不符 → bbox=None；PP 默认只恢复公式/表格裁剪图（L436-459）

**根因判定**：关联阶段漏配是主因（硬伤①可证明）+ 提取阶段缺图是次因

### E. 关联元数据丢失
- `_build_question_images` 只输出 3 个 key（question_number/image_id/placement），ingestion 读的 page_no/bbox/source/figure_id（L306-310）全落 None —— 违背 DSD 4.6 与 V1_LESSONS 3.27
- content_hash 去重命中路径（L206-246）不写 QuestionImage —— 二次入库连图都不补
- dedup 的 figure_mapping（removed→kept）从不被消费，被去重图片位置不再参与关联

### F. 修复优先级（审计建议）
1. **P0**：`_build_question_images` 改用 `_question_field_line_ids(q, "stem")` / options 从 `corrected_anchors` 读取；同步改单测 mock
2. **P0**：补 question_types 种子（5 个 canonical code）或 `_get_question_type_id` get-or-create
3. **P1**：关联规则放宽为图片 bbox 与题目区域重叠判定（非中心点在行内）
4. **P1**：`_build_pp_canonical` 补入 native 图片；`_build_question_images` 输出补齐 page_no/bbox/source/figure_id；dedup figure_mapping 透传支持多对多

## 五、三个数据质量问题的根因汇总

| 已观测缺陷 | 根因（跨模块） | 修复方向 |
|---|---|---|
| **英语综合题材料并入题干** | Prompt L518 明文要求 + content_slicer L210 显式并入 + semantic_anchor 锚点范围从材料首行起；跨题截断另有 first_option-1 硬边界（L331-336） | ① 改 Prompt：材料独立于 stem 输出；② content_slicer 剔除材料行；③ semantic_anchor 尊重 LLM 完整范围；④ quality_gate 加 stem 长度/材料混入检测 |
| **LaTeX 公式无 $ 包裹** | Prompt 无公式规则 + L469 禁止改写 + 全链路 verbatim 切片 + OCR 输出本身无 $ | ① Prompt 加公式包裹约定；② 切片层对公式行补 $ 包裹规范化 |
| **配图覆盖率低（15.5%）** | _build_question_images 读 q.stem_line_ids 属性但 SlicedQuestion 无此属性（死分支）+ 中心点判定过严 + native 图片被丢弃 + PP bbox 解析失败 | ① 改用 _question_field_line_ids；② 重叠判定放宽；③ _build_pp_canonical 补 native 图片；④ 补齐元数据输出 |
| **题型 423 题 NULL** | question_types 表无种子数据 + _get_question_type_id 只查不建 | ① 补 5 个 canonical 种子；② get-or-create 兜底 |
| **难度 88% NULL** | Prompt L457"可选字段" + 无判断依据 + 无校验回填 | ① Prompt 改必填+给依据；② 代码校验+retry 补 |
