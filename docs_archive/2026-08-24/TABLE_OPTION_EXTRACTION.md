# Table Option Extraction Architecture

## 1. Problem Statement

化学试卷中 Q16/Q18 的选项在 HTML table 标签里，PPS 和 VL 都无法正确提取选项内容。

### Current L1 Output Example

```
[P3L007] <html><body><table><tr><td>选项</td><td>实验操作</td><td>试剂A</td><td>现象</td><td>结论</td></tr><tr><td>A</td><td rowspan="4">试剂A
[P3L008] A.A
[P3L009] B.B
```

**问题分析**：
1. 表格内容在 HTML 标签里，但 L1 行只有 "A.A", "B.B"（空标签）
2. 选项的实际内容在 `rowspan="4"` 的单元格中，跨越多行
3. 当前代码按 `\n` 拆分，无法正确解析 HTML 表格结构

## 2. Current Code Flow

### ocr_l1_converter.py 处理逻辑

```python
# Line 44-62: 块处理逻辑
for block in ocr_page.blocks:
    raw_text = block.content.strip()
    if not raw_text:
        continue
    sub_lines = raw_text.split("\n")  # ← 问题：按 \n 拆分，HTML 标签被拆散
    for sub_text in sub_lines:
        sub_text = sub_text.strip()
        if not sub_text:
            continue
        # ... 创建 L1Line
```

### _map_block_type() 映射

```python
def _map_block_type(label: str) -> str:
    label_lower = label.lower()
    if "formula" in label_lower:
        return "formula"
    if "table" in label_lower:      # ← table 类型识别正确
        return "table"
    if "figure" in label_lower or "image" in label_lower:
        return "figure_placeholder"
    return "text"
```

**问题**：虽然识别了 `table` 类型，但没有对 table 内容做特殊处理。

## 3. Proposed Solution

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    OCR Provider Output                       │
│  (PaddleOCR-VL / PPS)                                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    ocr_l1_converter.py                       │
│  - _map_block_type(): 识别 table 类型                        │
│  - _process_table_block(): 新增，处理 HTML 表格              │
│    - 解析 HTML table 结构                                    │
│    - 提取选项行 (A/B/C/D)                                    │
│    - 处理 rowspan/colspan 合并单元格                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    L1Document                                │
│  - table 类型的 L1Line                                      │
│  - 选项内容正确提取                                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Implementation Strategy

#### Phase 1: HTML Table Parser

创建 `table_parser.py` 模块，负责：

1. **解析 HTML table 结构**
   - 使用 `html.parser.HTMLParser` 或 `BeautifulSoup`（如果可用）
   - 提取 `<table>`, `<tr>`, `<td>` 结构

2. **处理合并单元格**
   - `rowspan`: 纵向合并，需要向下填充
   - `colspan`: 横向合并，需要向右填充

3. **提取选项内容**
   - 识别选项行（A/B/C/D）
   - 合并相关单元格内容

#### Phase 2: Table Block Processor

修改 `ocr_l1_converter.py`，添加：

```python
def _process_table_block(block: OcrBlock) -> list[dict]:
    """处理 table 类型的 block，提取选项内容。
    
    Args:
        block: 包含 HTML table 的 OcrBlock
        
    Returns:
        解析后的行列表，每行包含 text 和 metadata
    """
    # 1. 检测是否包含选项
    if not _contains_options(block.content):
        # 非选项表格，按原逻辑处理
        return _split_table_by_newlines(block)
    
    # 2. 解析 HTML table
    table_data = parse_html_table(block.content)
    
    # 3. 提取选项行
    option_lines = _extract_option_lines(table_data)
    
    # 4. 转换为 L1Line 格式
    return option_lines
```

#### Phase 3: Option Extraction Logic

```python
def _extract_option_lines(table_data: list[list[str]]) -> list[str]:
    """从表格数据中提取选项行。
    
    化学试卷表格格式示例：
    | 选项 | 实验操作 | 试剂A | 现象 | 结论 |
    |------|----------|-------|------|------|
    | A    | 试剂A    | ...   | ...  | ...  |
    | B    | 试剂B    | ...   | ...  | ...  |
    | C    | 试剂C    | ...   | ...  | ...  |
    | D    | 试剂D    | ...   | ...  | ...  |
    
    需要提取为：
    - A. [实验操作内容] [试剂A] [现象] [结论]
    - B. [实验操作内容] [试剂B] [现象] [结论]
    - C. [实验操作内容] [试剂C] [现象] [结论]
    - D. [实验操作内容] [试剂D] [现象] [结论]
    """
```

### 3.3 Detailed Algorithm

#### Step 1: HTML Table Parsing

```python
import re
from html.parser import HTMLParser

class TableParser(HTMLParser):
    """解析 HTML table 为二维数组。"""
    
    def __init__(self):
        super().__init__()
        self.table = []
        self.current_row = []
        self.current_cell = ""
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.rowspan = 1
        self.colspan = 1
    
    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in ("td", "th") and self.in_row:
            self.in_cell = True
            self.current_cell = ""
            attrs_dict = dict(attrs)
            self.rowspan = int(attrs_dict.get("rowspan", 1))
            self.colspan = int(attrs_dict.get("colspan", 1))
    
    def handle_endtag(self, tag):
        if tag == "table":
            self.in_table = False
        elif tag == "tr" and self.in_row:
            self.in_row = False
            self.table.append(self.current_row)
        elif tag in ("td", "th") and self.in_cell:
            self.in_cell = False
            # 处理 rowspan 和 colspan
            for _ in range(self.rowspan):
                for _ in range(self.colspan):
                    self.current_row.append(self.current_cell)
    
    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data
```

#### Step 2: Option Pattern Recognition

```python
def _contains_options(content: str) -> bool:
    """检测内容是否包含选项（A/B/C/D）。"""
    # 匹配选项标签
    option_pattern = re.compile(r'\b[A-D]\b')
    # 匹配选项格式（如 A.xxx, (A), A、）
    option_format = re.compile(r'[A-D]\s*[.、．]|[（(]\s*[A-D]\s*[）)]')
    
    # 检查是否有选项标签
    if not option_pattern.search(content):
        return False
    
    # 检查是否有选项格式
    return bool(option_format.search(content))
```

#### Step 3: Rowspan Handling

```python
def _expand_rowspan(table: list[list[str]]) -> list[list[str]]:
    """展开 rowspan 合并单元格。
    
    示例：
    输入：
    [
        ["A", "内容1"],
        ["", "内容2"],   # ← 被 rowspan 合并
        ["B", "内容3"],
    ]
    
    输出：
    [
        ["A", "内容1"],
        ["A", "内容2"],   # ← 从上一行继承
        ["B", "内容3"],
    ]
    """
    if not table:
        return table
    
    # 创建副本
    expanded = [row[:] for row in table]
    
    # 处理 rowspan
    for i, row in enumerate(expanded):
        for j, cell in enumerate(row):
            if cell == "" and i > 0:
                # 从上一行继承
                expanded[i][j] = expanded[i-1][j]
    
    return expanded
```

#### Step 4: Option Line Extraction

```python
def _extract_option_lines_from_table(table: list[list[str]]) -> list[str]:
    """从展开后的表格中提取选项行。
    
    假设表格结构：
    - 第一行是表头
    - 后续行是选项（A/B/C/D）
    - 第一列是选项标签
    
    Returns:
        选项行列表，如：
        [
            "A. 实验操作内容 试剂A 现象 结论",
            "B. 实验操作内容 试剂B 现象 结论",
            ...
        ]
    """
    if len(table) < 2:
        return []
    
    # 跳过表头
    option_lines = []
    for row in table[1:]:
        if not row:
            continue
        
        # 检查第一列是否是选项标签
        option_label = row[0].strip()
        if option_label not in ("A", "B", "C", "D"):
            continue
        
        # 合并后续列内容
        content_parts = [cell.strip() for cell in row[1:] if cell.strip()]
        if content_parts:
            option_line = f"{option_label}. {' '.join(content_parts)}"
            option_lines.append(option_line)
    
    return option_lines
```

### 3.4 Integration Points

#### 修改 ocr_l1_converter.py

```python
def convert_ocr_to_l1(ocr_doc: OcrDocument, *, filename: str | None = None) -> L1Document:
    # ... existing code ...
    
    for ocr_page in ocr_doc.pages:
        page_lines: list[L1Line] = []
        
        if ocr_page.blocks:
            line_no = 0
            for block in ocr_page.blocks:
                raw_text = block.content.strip()
                if not raw_text:
                    continue
                
                # 新增：table 类型特殊处理
                if block.label.lower() == "table" and _contains_options(raw_text):
                    # 解析 HTML table 提取选项
                    option_lines = _process_table_block(block)
                    for sub_text in option_lines:
                        line_no += 1
                        line = L1Line(
                            line_id="", page_no=page_no, line_no_in_page=line_no,
                            order=global_order, text=sub_text, block_type="table",
                            bbox=block.bbox, source="ppsv3",
                        )
                        page_lines.append(line)
                        all_lines.append(line)
                        global_order += 1
                else:
                    # 原逻辑：按 \n 拆分
                    sub_lines = raw_text.split("\n")
                    for sub_text in sub_lines:
                        sub_text = sub_text.strip()
                        if not sub_text:
                            continue
                        line_no += 1
                        block_type = _map_block_type(block.label)
                        line = L1Line(
                            line_id="", page_no=page_no, line_no_in_page=line_no,
                            order=global_order, text=sub_text, block_type=block_type,
                            bbox=block.bbox, source="ppsv3",
                        )
                        page_lines.append(line)
                        all_lines.append(line)
                        global_order += 1
        # ... rest of existing code ...
```

### 3.5 Edge Cases and Considerations

#### 1. 非选项表格
- 化学试卷中可能有其他表格（如数据表、对比表）
- 需要区分选项表格和非选项表格
- **解决方案**：使用 `_contains_options()` 检测

#### 2. 选项格式多样性
- `A. xxx`
- `(A) xxx`
- `A、xxx`
- `A xxx`（无分隔符）
- **解决方案**：正则表达式匹配多种格式

#### 3. 表格结构复杂性
- 嵌套表格
- 不规则表格
- 空单元格
- **解决方案**：稳健的 HTML 解析器，错误容忍

#### 4. 性能考虑
- HTML 解析可能较慢
- 大量表格时需要优化
- **解决方案**：缓存解析结果，批量处理

## 4. Implementation Plan

### Phase 1: Core Parser (1-2 days)
- [ ] 创建 `table_parser.py` 模块
- [ ] 实现 HTML table 解析
- [ ] 实现 rowspan/colspan 处理
- [ ] 单元测试

### Phase 2: Option Extraction (1 day)
- [ ] 实现选项模式识别
- [ ] 实现选项行提取
- [ ] 处理边缘情况
- [ ] 单元测试

### Phase 3: Integration (1 day)
- [ ] 修改 `ocr_l1_converter.py`
- [ ] 集成测试
- [ ] 性能测试
- [ ] 文档更新

### Phase 4: Testing and Validation (1-2 days)
- [ ] 化学试卷测试
- [ ] 边缘情况测试
- [ ] 性能优化
- [ ] 代码审查

## 5. Testing Strategy

### Unit Tests

```python
def test_parse_html_table():
    """测试 HTML table 解析。"""
    html = """
    <table>
        <tr><td>A</td><td>内容1</td></tr>
        <tr><td>B</td><td>内容2</td></tr>
    </table>
    """
    parser = TableParser()
    parser.feed(html)
    assert parser.table == [["A", "内容1"], ["B", "内容2"]]


def test_expand_rowspan():
    """测试 rowspan 展开。"""
    table = [
        ["A", "内容1"],
        ["", "内容2"],
        ["B", "内容3"],
    ]
    expanded = _expand_rowspan(table)
    assert expanded == [
        ["A", "内容1"],
        ["A", "内容2"],
        ["B", "内容3"],
    ]


def test_extract_option_lines():
    """测试选项行提取。"""
    table = [
        ["选项", "实验操作", "试剂A", "现象", "结论"],
        ["A", "操作1", "试剂A1", "现象1", "结论1"],
        ["B", "操作2", "试剂A2", "现象2", "结论2"],
    ]
    options = _extract_option_lines_from_table(table)
    assert options == [
        "A. 操作1 试剂A1 现象1 结论1",
        "B. 操作2 试剂A2 现象2 结论2",
    ]
```

### Integration Tests

```python
def test_ocr_l1_converter_table_options():
    """测试完整的 OCR → L1 转换（含表格选项）。"""
    ocr_doc = OcrDocument(
        filename="test.pdf",
        pages=[OcrPage(
            page_number=1,
            markdown="",
            blocks=[OcrBlock(
                label="table",
                content="<html><body><table>...</table></body></html>",
                bbox={"x1": 0, "y1": 0, "x2": 100, "y2": 100},
            )],
            source_provider="ppsv3",
        )],
    )
    
    l1_doc = convert_ocr_to_l1(ocr_doc, filename="test.pdf")
    
    # 验证选项被正确提取
    option_lines = [l for l in l1_doc.lines if l.text.startswith(("A.", "B.", "C.", "D."))]
    assert len(option_lines) == 4
```

## 6. Risks and Mitigations

### Risk 1: HTML 解析失败
- **概率**：中
- **影响**：高（选项丢失）
- **缓解**：降级到原始拆分逻辑，记录警告日志

### Risk 2: 性能问题
- **概率**：低
- **影响**：中（处理延迟）
- **缓解**：异步处理，缓存结果

### Risk 3: 选项格式变化
- **概率**：中
- **影响**：中（部分选项丢失）
- **缓解**：正则表达式覆盖多种格式，配置化

## 7. Success Metrics

1. **功能指标**
   - 化学试卷选项提取准确率 > 95%
   - 非选项表格处理无影响

2. **性能指标**
   - 单页处理时间 < 100ms
   - 内存使用无显著增加

3. **质量指标**
   - 单元测试覆盖率 > 90%
   - 集成测试通过率 100%

## 8. Future Enhancements

### 8.1 配置化选项模式
- 支持自定义选项格式（如 E、F 等）
- 支持不同科目的选项格式

### 8.2 智能表格识别
- 使用机器学习识别表格类型
- 自动调整解析策略

### 8.3 多语言支持
- 支持英文选项（A/B/C/D）
- 支持其他语言选项格式

## 9. References

- [HTML Parser Documentation](https://docs.python.org/3/library/html.parser.html)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [PaddleOCR VL Model Documentation](https://github.com/PaddlePaddle/PaddleOCR)
- [V1_LESSONS 3.21/3.23](../01_Product/V1_LESSONS.md)

## 10. Appendix

### A. Sample HTML Table Structures

#### 选项表格示例 1（rowspan）
```html
<html>
<body>
<table>
  <tr>
    <td>选项</td>
    <td>实验操作</td>
    <td>试剂A</td>
    <td>现象</td>
    <td>结论</td>
  </tr>
  <tr>
    <td>A</td>
    <td rowspan="4">试剂A</td>
    <td>操作1</td>
    <td>现象1</td>
    <td>结论1</td>
  </tr>
  <tr>
    <td>B</td>
    <td>操作2</td>
    <td>现象2</td>
    <td>结论2</td>
  </tr>
  <tr>
    <td>C</td>
    <td>操作3</td>
    <td>现象3</td>
    <td>结论3</td>
  </tr>
  <tr>
    <td>D</td>
    <td>操作4</td>
    <td>现象4</td>
    <td>结论4</td>
  </tr>
</table>
</body>
</html>
```

#### 选项表格示例 2（无 rowspan）
```html
<html>
<body>
<table>
  <tr>
    <td>选项</td>
    <td>内容</td>
  </tr>
  <tr>
    <td>A</td>
    <td>选项A内容</td>
  </tr>
  <tr>
    <td>B</td>
    <td>选项B内容</td>
  </tr>
</table>
</body>
</html>
```

### B. Regular Expression Patterns

```python
# 选项标签匹配
OPTION_LABEL_PATTERN = re.compile(r'\b[A-D]\b')

# 选项格式匹配
OPTION_FORMAT_PATTERN = re.compile(
    r'[A-D]\s*[.、．]|'  # A. A、 A．
    r'[（(]\s*[A-D]\s*[）)]|'  # (A) （A）
    r'\b[A-D]\s'  # A （后跟空格）
)

# 表格标签匹配
TABLE_TAG_PATTERN = re.compile(r'<table[^>]*>|</table>|<tr[^>]*>|</tr>|<td[^>]*>|</td>')
```

### C. Error Handling Strategy

```python
def _process_table_block_safe(block: OcrBlock) -> list[str]:
    """安全处理 table block，失败时降级到原始逻辑。"""
    try:
        return _process_table_block(block)
    except Exception as e:
        logger.warning("Failed to parse table block: %s", e)
        # 降级到原始拆分逻辑
        return block.content.split("\n")
```
