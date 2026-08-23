# AI Tutor Personal Edition — T3 实施基线

Version: 2.0
Status: 执行基线
Date: 2026-08-11
Source of truth: `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`
约束来源: `Docs/05_Development/V1_LESSONS.md`（29 条 P0/P1/P2 约束）

---

## 1. 第一性原理

V1 的核心教训归结为一句话：**信息在链路中丢失，代码和 LLM 做了对方不该做的事。**

- LLM 做了代码的事（抄写题目原文 → LaTeX 转义静默损坏）
- 代码做了 LLM 的事（正则猜测语义边界 → 55.6% 失败率）
- 信息在转换中丢失（OCR 丢图、归一化丢行号、截断丢答案）

V2 Annotation Paradigm 的本质是**各司其职**：

| 角色 | 职责 | 不做的事 |
|---|---|---|
| LLM | 语义判断：题目边界、题型、section、粗略行号 | 不抄写题目原文、不输出 LaTeX 内容 |
| 代码 | 机械执行：按行号切片、按标记校正边界、答案匹配 | 不猜测语义、不替代 LLM 判断 |
| L1 原文 | 不可变事实源：行编号的原始文档文本 | 不被 LLM 输出覆盖 |
| L2 标注 | 可追溯镜像：LLM 行号 + 校正结果 + 来源标记 | 不存储 LLM 抄写的内容 |

信息零损耗：L1 不可变 → L2 只存标注 → L3 按需渲染。

L1 事实源不依赖单一提取器：PyMuPDF native 文本层、PP-StructureV3 OCR/Layout 输出必须同时保留为 raw L1，再由代码按证据生成 canonical L1。LLM 只做行级仲裁，不生成或改写 L1 原文。

---

## 2. L1 行模型

L1 是文档解析的统一中间表示，Native 和 OCR 输出必须统一为同一个 L1Document，LLM 只面对 L1，不关心来源。

### 2.1 行模型字段

```python
@dataclass
class L1Line:
    line_id: str          # "P1L001"/"N1L001" — PP/Native 按来源区分前缀
    page_no: int          # 1-based 页码
    line_no_in_page: int  # 页内行号（1-based）
    order: int            # 全局排序序号（1-based，跨页连续）
    text: str             # 行文本（不可变）
    block_type: str       # text / formula / table / figure_placeholder
    bbox: dict | None     # {"x1": 0, "y1": 0, "x2": 100, "y2": 20}，可为空
    source: str           # native / paddleocr / mimo / deepseek_vl
    continuation: bool    # 是否跨页续行（默认 false）
```

### 2.2 跨页处理

- 跨页行拆成两行：前页末行（如 `P1L999`/`N1L999`，`continuation=true`）+ 后页首行（如 `P2L001`/`N2L001`，`continuation=true`）
- 不创建跨页逻辑 ID
- LLM 标注时可引用任一侧的 line_id，代码通过 continuation 关联两侧内容

### 2.3 L1Document

```python
@dataclass
class L1Page:
    page_no: int
    lines: list[L1Line]
    images: list[L1Image]

@dataclass
class L1Image:
    image_id: str         # 文档级唯一
    page_no: int
    bbox: dict | None
    xref: int | None      # PyMuPDF xref（Native 路径）
    source: str           # native / paddleocr
    figure_id: str        # 文档级去重标识

@dataclass
class L1Document:
    filename: str
    pages: list[L1Page]
    lines: list[L1Line]   # 按 order 排序的扁平行列表
    images: list[L1Image]
    source: str           # native / ocr / mixed
    total_pages: int
    text_coverage: float  # 文本层覆盖率（Native 路径）
```

### 2.4 L1 后处理

L1 生成后必须执行机械后处理（不依赖 LLM）：

1. **题号前强制换行**：`D. 既不充分也不必要条件5.已知...` → 拆成两行
2. **单行选项行内切分**：`A.选项A B.选项B C.选项C D.选项D` → 4 行
3. **小数/化学式误拆回避**：`3.2x` 不拆为题号 `3.` + `2x`
4. **连续行号校验**：后处理后行号必须连续，不跳号

### 2.5 L1 双源与仲裁

L1 采用“双源 raw + canonical L1”：

- `native raw L1`：PyMuPDF 文本层，用于页面尺寸、图片 xref/bbox、答案表定位、上下标几何信息。
- `ppsv3 raw L1`：PP-StructureV3 视觉识别结果，用于公式符号、复杂版面、扫描页。
- `canonical L1`：代码按每行/每区块证据选择最终 source，并保留 `raw_sources`、`selected_source`、`evidence`、`confidence`。
- LLM 只输出行级仲裁：`line_id`、候选 source、冲突结论、evidence；JSON 中禁止出现题目原文或 LaTeX。
- 上下标/化学式/计量单位默认双源校验；native 与 PP 冲突时进入低置信度，禁止静默采用 PP。

---

## 3. L2 标注契约

L2 是 LLM 标注结果的结构化镜像，只存储行号引用和元数据，不存储题目内容文本。

### 3.1 L2Annotation

```python
@dataclass
class L2QuestionAnnotation:
    question_number: str
    question_type: str         # single_choice / multiple_choice / fill_blank / ...
    section_id: str | None     # 共享材料题的 section 标识（如 "cloze_1"）
    stem_line_ids: list[str]   # ["P1L003", "P1L004", ...]（canonical 保留 PP 行号）
    options_line_ids: dict[str, list[str]]  # {"A": ["P1L008"], "B": ["P1L009"], ...}
    # 注意：B 阶段不输出 answer_lines / explanation_lines
    difficulty: int | None     # 1-5
    score: float | None
    knowledge_points: list[str]
    confidence: float          # 0-1
    source_page: int | None    # 题目所在起始页码

@dataclass
class L2DocumentAnnotation:
    filename: str
    subject: str | None
    grade: str | None
    year: int | None
    school: str | None
    questions: list[L2QuestionAnnotation]
    metadata_confidence: float
    warnings: list[str]
```

### 3.2 约束

- B 阶段（LLM 标注）**不输出** answer_lines / explanation_lines（答案由 C 阶段独立匹配）
- JSON 中**不包含** LaTeX 题干/选项/答案/解析原文（V1_LESSONS 3.1/3.16）
- LLM 输出的行号一律视为 `coarse_line_range`，不是最终切片边界

---

## 4. 锚点校正契约

LLM 输出的行号经过代码校正后才能用于切片。

### 4.1 CorrectedAnchor

```python
@dataclass
class CorrectedAnchor:
    field: str                    # "stem" / "options" / "answer" / "explanation"
    llm_line_ids: list[str]       # LLM 原始输出
    corrected_line_ids: list[str] # 校正后
    anchor_status: str            # exact / nearest / missing / retry
    validation_passed: bool       # nearest 是否通过内容校验
    evidence: str | None          # 校正依据（如 "吸附到题号标记 5."）
```

### 4.2 anchor_status 定义

| 状态 | 含义 | 后续动作 |
|---|---|---|
| `exact` | 锚点与稳定标记精确匹配 | 直接切片 |
| `nearest` | 锚点吸附到最近稳定标记，**通过内容校验** | 切片，标记 `nearest` |
| `missing` | 找不到稳定锚点 | 禁止静默切片，进入低置信度审核 |
| `retry` | 校正后内容校验失败 | 要求 LLM 在局部区域重新标注 |

### 4.3 校正规则

1. **题号起点**：吸附到最近的 `\d+[.、．]` 标记，同时避免把 `3. 2x` 误判为小数
2. **选项边界**：按 `A.`/`B.`/`C.`/`D.` 等标记校正；单行多选项做行内切分
3. **答案边界**：吸附到答案表、`【答案】`、`【详解】`、`【分析】` 等标记
4. **相邻题目边界**：LLM 起点偏前/偏后时，按下一题起点重新截断
5. **`nearest` 必须经过内容校验**：校验不通过 → `retry/missing`，不能"吸到最近就发布"

---

## 5. Source Provenance 契约

每个字段带来源标记，确保可追溯。

```python
@dataclass
class SourceProvenance:
    field: str        # "answer" / "explanation" / "stem" / "options"
    source: str       # 来源类型（见下表）
    confidence: float # 来源置信度
    evidence: str     # 简短描述来源位置
```

### 5.1 来源类型

| source | 含义 |
|---|---|
| `native_extract` | 从 Native PDF 文本层提取 |
| `ocr_extract` | 从 OCR/VL 结果提取 |
| `document_answer_table` | 从文末答案表匹配 |
| `document_inline_answer` | 从题后 `【答案】` 匹配 |
| `document_inline_explanation` | 从题后 `【详解】`/`【分析】` 匹配 |
| `llm_annotation` | LLM 标注的行号切片 |
| `llm_fallback` | LLM 推理兜底（仅用于缺失项） |

---

## 6. 开工前冻结动作

| # | 动作 | 说明 |
|---|---|---|
| F1 | 冻结 `question_extractor.py` | 文件头加 DEPRECATED 标记，禁止正式链路引用 |
| F2 | 冻结 `parser.py` 中 LLM 调用 | 标记为临时验证路径 |
| F3 | 更新 DSD.md | question_images 多对多语义 + L1/L2 中间态说明 |
| F4 | 更新 V1_LESSONS.md 3.4/3.26 | 图片去重改为"物理图存储去重 + 题图关联多对多 + 无证据广播抑制" |
| F5 | 创建 `test/fixtures/l1_snapshot.json` | 手工构造 L1 fixture，供 Golden Set 和 Smoke Test |
| F6 | 新增 Alembic migration | 如有新字段 |

---

## 7. Phase 0：契约 + Golden Set + Smoke Test

**目标**：定义所有数据契约，建立 ground truth，验证 LLM Provider 行为。不做任何解析代码。

### Task 0.1：定义 L1/L2/Anchor/Provenance 数据契约

- 新增 `backend/app/domains/document/schemas_l1.py`：L1Line, L1Page, L1Image, L1Document
- 新增 `backend/app/domains/document/schemas_l2.py`：L2QuestionAnnotation, L2DocumentAnnotation, CorrectedAnchor, SourceProvenance
- 更新 `backend/app/domains/document/schemas.py`：保留现有 OcrDocument/ParsedQuestion 作为 OCR 层契约
- 同步 DSD.md（如有新字段）
- 新增 Alembic migration（如有新表或新字段）
- 运行 `validate_docs_vs_code.py`

**验收**：Schema 通过校验，`compileall` 通过

### Task 0.2：L1 fixture + Golden Set

**L1 fixture**（手工构造，不依赖 PDF 提取）：
- 从 `test/pdf/` 选 1 份数学 PDF，手工提取前 3 页文本
- 构造 `test/fixtures/l1_snapshot.json`：固定行号、固定内容
- 这个 fixture 是 Task 0.2/0.3/1.8 的共享基准

**Golden Set**（两层标注）：

Layer 1 — expected_content（人工标注，不依赖 L1 版本）：
- 题号、题干文本、选项、答案、详解、题型、配图位置
- 答案按"页码 + 文本证据 + bbox"标注

Layer 2 — expected_anchor（基于 L1 fixture 的锚点，可重生成）：
- 每题的 stem_line_ids、options_line_ids、answer_line_ids、explanation_line_ids

标注范围：
- 1 份数学（含公式配图 + 文末答案表）
- 1 份英语（含完形填空共享材料题）
- 放 `test/annotations/golden/`

**验收**：Golden Set 标注完整，Layer 1 和 Layer 2 对应

### Task 0.3：LLM Provider Smoke Test

- 用 L1 fixture 前 3 页文本跑 DeepSeek/MIMO/DeepSeek VL
- 验证：JSON 结构合法、行号在 L1 范围内、MIMO `json_object` 行为、LaTeX 不进入 JSON
- 报告格式：provider、JSON 合法性、行号范围、耗时、token 数、失败原因
- **不记录** prompt 全文、原始 LLM 输出、完整文档文本（rules.md 日志红线）
- live 脚本放 `test/scripts/`，不进默认 pytest

**验收**：三家 Provider 均能返回合法 JSON，行号在合理范围

### Task 0.4：L1 后处理规则

- 新增 `backend/app/domains/document/l1_postprocessor.py`
- 题号前机械换行（V1_LESSONS 3.23）
- 单行 A./B./C./D. 行内切分（V1_LESSONS 3.21）
- 小数/化学式误拆回避
- 纯函数，可用 fixture 验证

**验收**：fixture L1 经后处理后行号连续、题号边界清晰

**Phase 0 交付物**：L1/L2 Schema、Golden Set JSON、Smoke Test 报告、L1 后处理规则 + 测试

---

## 8. Phase 1：单份数学 PDF 最小纵向闭环

**目标**：单份数学 PDF 端到端跑通 Annotation Paradigm。

### Task 1.1：L1 双源生成与 canonical L1

- 新增 `backend/app/domains/document/ppsv3_l1.py`：PP-StructureV3 JSONL → `ppsv3 raw L1`，校验 `extractProgress`，页码使用 JSONL `page` 字段。
- 保留 `backend/app/domains/document/native_markdown.py`：PyMuPDF 只作为辅助源，不再作为整份正文 L1 基座。
- 新增 canonical L1 生成逻辑：按证据选择 native/ppsv3 行，保留 raw source 与 provenance。
- 图片 bbox 通过 `page.get_image_rects(xref)` 获取（V1_LESSONS 3.27）。

**验收**：fixture PDF 能生成双源 raw L1 与 canonical L1，行号稳定，每行可回溯到具体 source。

### Task 1.2：LLM 行号标注器

- 新增 `backend/app/domains/document/line_annotator.py`
- Prompt 只要求输出：题号、题型、section_id、stem_line_ids、options_line_ids、difficulty、score、knowledge_points
- **不输出** answer_lines / explanation_lines
- 输出 L2Annotation

**验收**：用 L1 fixture 跑标注，输出符合 L2 契约

### Task 1.3：锚点校正器

- 新增 `backend/app/domains/document/anchor_corrector.py`
- L2 line_ids → CorrectedAnchor
- 校正规则按第 4.3 节
- `nearest` 必须经过内容校验，校验不过 → `retry/missing`
- `missing`/`retry` 禁止自动发布

**验收**：exact/nearest/missing 三种场景覆盖

### Task 1.4：内容切片器

- 新增 `backend/app/domains/document/content_slicer.py`
- CorrectedAnchor + L1 原文 → stem、options
- 代码切片，不是 LLM 抄写（V1_LESSONS 3.1）

**验收**：切片结果与 Golden Set expected_content 对比

### Task 1.5：答案 + 详解独立匹配器

- 新增 `backend/app/domains/document/answer_matcher.py`
- 统一输出 answer + explanation：
  - `answer_source` + `answer_line_ids`
  - `explanation_source` + `explanation_line_ids`
- 优先级：文末答案表 → 题后 `【答案】`/`【详解】` → LLM 兜底
- LLM 兜底标记 `llm_fallback`，已有教师版时不覆盖（V1_LESSONS 3.8）

**验收**：用 Golden Set 验证答案优先级链正确

### Task 1.6：质量门

- 新增 `backend/app/domains/document/quality_gate.py`
- 按题评估：切分完整、选项数量、答案匹配、anchor_status
- 失败只标低置信度，不整批丢弃（V1_LESSONS 3.20）
- `missing`/`retry` 不允许自动发布

**验收**：Golden Set 中每题有 confidence + issues[]

### Task 1.7：纵向闭环评估

- 用 Golden Set 做字段级准确率
- 迭代 Prompt 和校正规则

**验收指标**：

| 指标 | 目标 |
|---|---|
| 题号识别 | 100% |
| 题干提取 | ≥95% |
| 单选题选项完整性 | 100% |
| 答案匹配 | ≥95% |
| 详解匹配 | ≥90% |
| source provenance | 100% 非空 |
| missing/retry 自动发布 | 0 |
| 低置信度按题保存 | 100% |

**Phase 1 交付物**：单份数学 PDF 的完整 Annotation 闭环 + 准确率报告

---

## 9. Phase 2：扩展覆盖

### Task 2.1：OCR/VL L1 与 Canonical L1 融合

- 所有 OCR/VL Provider 统一输出 L1Document
- PaddleOCR 必须校验 `extractProgress`（V1_LESSONS 3.3）
- 页码优先用 JSONL `page` 字段，不用 `len(pages) + 1` 猜
- L1 后处理复用 Task 0.4
- 与 native raw L1 对齐后生成 canonical L1；冲突行默认低置信度

### Task 2.2：图片元数据 + 文档级去重

- Native 图片：`page.get_image_rects(xref)` 获取 bbox（V1_LESSONS 3.27）
- OCR 图片：从 layoutParsingResults 提取
- 物理图文档级去重：IoU/中心距离（V1_LESSONS 3.4/3.26）
- **题-图关联允许多对多**：物理图存储只保留一份，question_images 关联允许一条或多条
- 无 page/bbox 时记录 `missing_figure`，不整页兜底
- 无显式证据的跨题广播仍要抑制

### Task 2.3：英语共享材料题验证

- 用 Golden Set 中的英语 PDF 验证 section 级处理（V1_LESSONS 3.18）
- LLM 识别 section/材料块 + 题号范围
- section 材料作为共享上下文

### Task 2.4：管线编排 + Background Task 接入

- 重写 `parser.py` 为完整管线：
  ```
  上传 → Native/OCR 路由 → L1 生成 → L1 后处理 → LLM 标注 → 锚点校正
  → 内容切片 → 答案匹配 → 图片关联 → 元数据标注 → 质量门 → 入库/审核
  ```
- 接入 Background Task：进度、stage、error_detail
- 遵守 V1_LESSONS 3.14：富化任务不阻塞主任务

### Task 2.5：Live 全量验证

- 用 3 份 PDF（数学/英语/物理）跑完整管线
- 产出字段级准确率报告
- 对照 Phase 1 验收指标

**Phase 2 交付物**：3 份 PDF 完整管线 + 准确率报告

---

## 10. Phase 3：规模化

### Task 3.1：30 份 PDF 基线

- 用 `run_parse_baseline.py` 跑全部 30 份
- 用 `evaluate_parse_accuracy.py` 统计 9 科准确率
- 产出基线报告

### Task 3.2：DOCX 支持

- DOCX L1 生成器（段落/表格/图片/公式）
- 复用标注/校正/切片链路

### Task 3.3：前端对接

- 解析结果展示 API
- 审核队列 API

---

## 11. 依赖关系

```
Phase 0（契约）
  ├─ Task 0.1 Schema ──────────────────────────────┐
  ├─ Task 0.2 Golden Set ──────────────────────────┤
  ├─ Task 0.3 Smoke Test ──────────────────────────┤
  └─ Task 0.4 L1 后处理 ──────────────────────────┘
                                                    ↓
Phase 1（纵向闭环）                                 │
  ├─ Task 1.1 L1 双源 ←─────────────────────────┘
  ├─ Task 1.2 LLM 标注 ←── 0.1 Schema + 0.3 Smoke
  ├─ Task 1.3 锚点校正 ←── 0.1 Schema
  ├─ Task 1.4 内容切片 ←── 1.3 校正
  ├─ Task 1.5 答案匹配 ←── 1.4 切片
  ├─ Task 1.6 质量门 ←─── 1.5 答案
  └─ Task 1.7 评估 ←───── 0.2 Golden Set + 1.6 质量门
                                                    ↓
Phase 2（扩展）                                     │
  ├─ Task 2.1 OCR L1 ←── 0.4 后处理               │
  ├─ Task 2.2 图片去重                              │
  ├─ Task 2.3 英语验证 ←── 0.2 Golden Set          │
  ├─ Task 2.4 管线集成 ←── 1.1-1.6 全部            │
  └─ Task 2.5 Live 验证                             │
                                                    ↓
Phase 3（规模化）                                   │
  ├─ Task 3.1 30 份基线                             │
  ├─ Task 3.2 DOCX                                  │
  └─ Task 3.3 前端                                  │
```

---

## 12. 执行约束

- 单任务制：同一时间只推进一个任务
- 每任务不超过 4 小时，必须产出可运行结果
- 阶段验收通过前，不进入下一阶段
- 文档解析代码必须遵守 `V1_LESSONS.md` 全部 31 条约束
- 常规 pytest 使用 mock；live LLM/OCR 验证单独隔离
- 表结构变更必须同步 Alembic migration
- 完成后更新 `LOG.md`、`PROJECT_STATUS.md`，必要时更新权威文档

---

## 13. 变更记录

### 2026-08-11

- 创建本文件，作为 T3 实施的执行基线。
- 整合 V1 代码/日志分析、Codex 评审意见，确定 Annotation Paradigm 实施路线。
- 定义 L1 行模型（PP 用 P1L001，Native 用 N1L001，canonical 保留 PP 行号）、L2 标注契约、锚点校正契约、Source Provenance 契约。
- 建立 Phase 0-3 四阶段 Task 列表和依赖关系。

### 2026-08-11 23:49:10

- 架构调整为 L1 双源：PyMuPDF native 与 PP-StructureV3 raw L1 并存，canonical L1 由代码按证据选择。
- PyMuPDF 降级为辅助工具，不再作为整份正文 L1 基座。
- LLM 只允许做行级仲裁，禁止输出或生成 L1 原文。
- 上下标/化学式默认双源校验，禁止直接接受 PP 识别结果。

### 2026-08-20 22:40:51

- 明确 L1 行模型：PP 用 `P1L001`，Native 用 `N1L001`，canonical 保留 PP 行号。
- native 行号通过 `raw_sources["native_line_id"]` 溯源，不暴露给 LLM 标注阶段。
