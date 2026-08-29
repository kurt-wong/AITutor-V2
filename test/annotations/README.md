# 解析准确率标注目录

每个 PDF 一个 JSON 标注文件，文件名为 `<pdf文件名>.json`，例如：

```text
2026北京朝阳高一（上）期末数学（教师版）.pdf.json
```

标注文件结构：

```json
{
  "filename": "2026北京朝阳高一（上）期末数学（教师版）.pdf",
  "subject": "数学",
  "grade": "高一",
  "year": 2026,
  "school": "",
  "questions": [
    {
      "question_number": "1",
      "stem": "题干原文",
      "options": [{"label": "A", "text": "选项"}],
      "answer": "A",
      "explanation": "解析原文",
      "images": [],
      "question_type": "单选",
      "difficulty": 3,
      "score": 5,
      "knowledge_points": ["知识点"]
    }
  ]
}
```

运行：

```powershell
python test\scripts\evaluate_parse_accuracy.py
```

结果写入 `test/results/accuracy_summary.json`。
