import json

golden_path = "test/annotations/golden/math_real_golden.json"

golden = {
    "filename": "2026北京朝阳高一（上）期末数学（教师版）.pdf",
    "created_at": "2026-08-11T00:00:00Z",
    "annotator": "human_golden",
    "version": "3.1",
    "postprocessed": False,
    "l1_fixture": "l1_snapshot_math_real_ppsv3.json",
    "questions": [
        {
            "question_number": "2",
            "question_type": "single_choice",
            "section_id": "选择题",
            "stem_line_ids": ["P1L009"],
            "options_line_ids": {"A": ["P1L010"], "B": ["P1L010"], "C": ["P1L010"], "D": ["P1L010"]},
            "answer": "C",
            "answer_line_ids": ["P5L003"],
            "explanation_line_ids": [],
            "answer_source": "document_answer_table",
            "explanation_source": "llm_fallback",
            "expected_content": {
                "stem": "下列函数中，在定义域内单调递减且值域为$的是",
                "options": {"A": "=-x$", "B": "={rac{1}{x}}$", "C": "=2^{-x}$", "D": "=\log_{0.5}x$"},
                "answer": "C"
            },
            "expected_anchor": {
                "stem_line_ids": ["P1L009"],
                "options_line_ids": ["P1L010"],
                "answer_line_ids": ["P5L003"],
                "explanation_line_ids": []
            },
            "difficulty": 2,
            "score": 5.0,
            "knowledge_points": ["函数单调性", "函数值域"],
            "confidence": 1.0,
            "source_page": 1
        }
    ]
}

with open(golden_path, "w", encoding="utf-8") as f:
    json.dump(golden, f, ensure_ascii=False, indent=2)

print("Golden file updated")
