# AI Tutor Personal Edition — 文档入库管线规范

Version: 4.0
Status: 开发指引基线
Date: 2026-08-10
Supersedes: PIPELINE v3.2
Source of truth: `Docs/00_Requirements/REQUIREMENTS_AND_SOLUTION.md`

---

## 1. 目标

本管线负责将教师版 PDF/DOCX 转换为结构化题库数据。

最终输出：

- 题目内容：题干、选项、答案、详解、配图
- 元数据：学科、年级、年份、学校、题型、分值、难度、知识点、出现次数
- 状态：高置信度自动入库，低置信度进入人工审核

---

## 2. 输入范围

支持：

- 带文字层的 PDF
- 排版规范的 DOCX
- 扫描版或图片型 PDF

扫描版和图片型 PDF 会进入 OCR/VL 处理，识别结果默认按低置信度处理。

单个文件上限：50MB。

---

## 3. 管线总览

```text
1. 上传与原始文件存储
2. 源文件解析
3. 文本/公式/表格/图片提取
4. 题目切分
5. 配图关联
6. 答案与详解匹配
7. 元数据标注
8. 置信度判断
9. 重复题合并
10. 入库与异步富化
```

---

## 4. 阶段说明

### 4.1 上传与原始文件存储

- 管理员批量上传 PDF/DOCX。
- 原始文件写入 MinIO 或 NAS 对象存储。
- 创建 documents 记录。
- 解析任务进入队列。

### 4.2 源文件解析

PDF：

- 优先使用 PP-StructureV3 做版面解析。
- 提取 PDF 文字层。
- 提取图片对象、矢量图形和公式区域。
- 扫描页进入 OCR/VL。

DOCX：

- 解析段落、表格、图片和公式对象。
- 尽量利用 Word 排版结构辅助题目切分。

### 4.3 文本/公式/表格/图片提取

输出统一的中间表示：

- 文本块
- 公式块
- 表格块
- 图片块
- 题目编号和题型线索

公式内部使用结构化表示，页面和导出时渲染为印刷体，不显示 LaTeX 源码。

### 4.4 题目切分

- 使用 LLM 判断题目边界。
- 支持按学科细粒度题型识别。
- 支持复合题、材料题、一题多问。
- 机械操作，如纯题号提取，可以使用正则；语义判断必须使用 LLM。

### 4.5 配图关联

- 数学/物理/化学中的几何图、电路图、装置图、函数图需要独立截取。
- 图片资源写入对象存储。
- 每张配图与 question_id 建立关联。
- 如果题目本身是图片，保留原图，并尽量提取图片文本。

### 4.6 答案与详解匹配

支持两种结构：

- 文末答案：按题号反查。
- 题后答案：就近匹配。

匹配规则：

- 优先使用文档结构信息。
- LLM 负责判断答案归属和解释归属。
- 匹配失败进入低置信度审核。

### 4.7 元数据标注

使用 LLM 按规范自动标注：

- 学科
- 年级
- 年份
- 学校
- 题型
- 分值
- 难度
- 知识点

元数据必须符合 `Docs/03_Data/DSD.md` 中的定义。

### 4.8 置信度判断

判定维度：

- 题目切分是否完整
- 题干是否完整
- 答案是否匹配
- 详解是否匹配
- 配图是否关联
- 元数据是否可信

高置信度自动入库。

低置信度进入审核队列，由管理员修正后入库。

### 4.9 重复题合并

查重方式：

- 文本规则匹配。
- embedding 语义相似度。

同一道题重复出现时：

- 合并为一道题。
- 保留多个来源信息。
- 累加出现次数。

### 4.10 入库与异步富化

入库后异步执行：

- 生成 embedding。
- 更新出现次数统计。
- 校验答案和详解完整性。
- 生成可供统计分析使用的聚合数据。

---

## 5. 准确率策略

- 高优先级科目：数学、物理、化学、英语、语文、生物、政治。
- 目标：题干、答案、详解、配图关联准确率达到 95% 以上。
- 其他科目可以适当降低精度要求。
- 开发阶段使用真实教师版文档建立测试集，按科目统计准确率。

---

## 6. 模型分工

| 任务 | 模型/方式 |
|---|---|
| PDF 版面解析 | PP-StructureV3 |
| DOCX 解析 | 本地解析 + LLM 结构化 |
| OCR/VL | PaddleOCR-VL、MIMO、Qwen |
| 题目切分 | LLM |
| 配图截取 | 本地图像处理 + 文档结构 |
| 答案匹配 | 文档结构 + LLM |
| 元数据标注 | DeepSeek / MIMO |
| embedding | NAS 本地轻量模型 |
| 难度评估 | LLM + 规则 + 学习数据 |

所有 LLM 调用必须经过 LLM Gateway。

---

## 7. 配置项

主要配置项：

| 配置 | 说明 |
|---|---|
| PADDLEOCR_VL_ENABLED | 是否启用 PP-StructureV3 |
| PADDLEOCR_VL_TOKEN | PP-StructureV3 API Token |
| DEEPSEEK_API_KEY | DeepSeek API Key |
| MIMO_API_KEY | MIMO API Key |
| QWEN_VL_API_KEY | Qwen VL API Key |
| EMBEDDING_PROVIDER | 本地 embedding Provider |
| DOCUMENT_MAX_SIZE_MB | 单文件大小上限，默认 50 |
| BATCH_UPLOAD_LIMIT | 批量上传上限 |
| AUTO_APPROVE_THRESHOLD | 高置信度自动入库阈值 |

API Key 必须通过 `.env` 管理，禁止硬编码。

---

## 8. 目标源码结构

建议按以下结构实现：

```text
backend/app/domains/document/
├── api.py
├── service.py
├── pdf_parser.py
├── docx_parser.py
├── image_extractor.py
├── question_splitter.py
├── answer_matcher.py
├── metadata_annotator.py
├── confidence.py
└── tasks.py
```

