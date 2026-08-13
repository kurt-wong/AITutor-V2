import json

# Read PP snapshot
with open("test/fixtures/l1_snapshot_math_real_ppsv3.json", "r", encoding="utf-8") as f:
    fixture = json.load(f)
line_map = {l["line_id"]: l["text"] for l in fixture["lines"]}

# Build golden
golden = {"filename": "2026北京朝阳高一（上）期末数学（教师版）.pdf", "created_at": "2026-08-11T00:00:00Z", "annotator": "human_golden", "version": "3.1", "postprocessed": False, "l1_fixture": "l1_snapshot_math_real_ppsv3.json", "questions": []}

# Q2
golden["questions"].append({"question_number": "2", "question_type": "single_choice", "section_id": "选择题", "stem_line_ids": ["P1L009"], "options_line_ids": {"A": ["P1L010"], "B": ["P1L010"], "C": ["P1L010"], "D": ["P1L010"]}, "answer": "C", "answer_line_ids": ["P5L003"], "explanation_line_ids": [], "answer_source": "document_answer_table", "explanation_source": "llm_fallback", "expected_content": {"stem": line_map["P1L009"], "options": {"A": "=-x$", "B": "={rac{1}{x}}$", "C": "=2^{-x}$", "D": "=\log_{0.5}x$"}, "answer": "C"}, "expected_anchor": {"stem_line_ids": ["P1L009"], "options_line_ids": ["P1L010"], "answer_line_ids": ["P5L003"], "explanation_line_ids": []}, "difficulty": 2, "score": 5.0, "knowledge_points": ["函数单调性", "函数值域"], "confidence": 1.0, "source_page": 1})

# Q3
golden["questions"].append({"question_number": "3", "question_type": "single_choice", "section_id": "选择题", "stem_line_ids": ["P1L011"], "options_line_ids": {"A": ["P1L012"], "B": ["P1L012"], "C": ["P1L012"], "D": ["P1L012"]}, "answer": "B", "answer_line_ids": ["P5L003"], "explanation_line_ids": [], "answer_source": "document_answer_table", "explanation_source": "llm_fallback", "expected_content": {"stem": line_map["P1L011"], "options": {"A": "$\exists x>0$，使得$\sin x<x$", "B": "$\exists x>0$，使得$\sin x\geqslant x$", "C": "$orall x>0$，都有$\sin x\geqslant x$", "D": "$orall x>0$，都有$\sin x>x$"}, "answer": "B"}, "expected_anchor": {"stem_line_ids": ["P1L011"], "options_line_ids": ["P1L012"], "answer_line_ids": ["P5L003"], "explanation_line_ids": []}, "difficulty": 1, "score": 5.0, "knowledge_points": ["命题否定", "逻辑量词"], "confidence": 1.0, "source_page": 1})

# Q5
golden["questions"].append({"question_number": "5", "question_type": "single_choice", "section_id": "选择题", "stem_line_ids": ["P1L013"], "options_line_ids": {"A": ["P1L014"], "B": ["P1L014"], "C": ["P1L014"], "D": ["P1L014"]}, "answer": "A", "answer_line_ids": ["P5L003"], "explanation_line_ids": [], "answer_source": "document_answer_table", "explanation_source": "llm_fallback", "expected_content": {"stem": line_map["P1L013"], "options": {"A": "<a<b$", "B": "<c<a$", "C": "<b<a$", "D": "<b<c$"}, "answer": "A"}, "expected_anchor": {"stem_line_ids": ["P1L013"], "options_line_ids": ["P1L014"], "answer_line_ids": ["P5L003"], "explanation_line_ids": []}, "difficulty": 2, "score": 5.0, "knowledge_points": ["指数函数", "对数函数", "大小比较"], "confidence": 1.0, "source_page": 1})

# Q8
golden["questions"].append({"question_number": "8", "question_type": "single_choice", "section_id": "选择题", "stem_line_ids": ["P1L023"], "options_line_ids": {"A": ["P2L001"], "B": ["P2L001"], "C": ["P2L001"], "D": ["P2L001"]}, "answer": "C", "answer_line_ids": ["P5L003"], "explanation_line_ids": [], "answer_source": "document_answer_table", "explanation_source": "llm_fallback", "expected_content": {"stem": line_map["P1L023"], "options": {"A": "充分不必要条件", "B": "必要不充分条件", "C": "充分必要条件", "D": "既不充分也不必要条件"}, "answer": "C"}, "expected_anchor": {"stem_line_ids": ["P1L023"], "options_line_ids": ["P2L001"], "answer_line_ids": ["P5L003"], "explanation_line_ids": []}, "difficulty": 3, "score": 5.0, "knowledge_points": ["三角函数单调性", "充分必要条件"], "confidence": 1.0, "source_page": 1})

# Q9
golden["questions"].append({"question_number": "9", "question_type": "single_choice", "section_id": "选择题", "stem_line_ids": ["P2L002"], "options_line_ids": {"A": ["P2L003"], "B": ["P2L003"], "C": ["P2L003"], "D": ["P2L003"]}, "answer": "D", "answer_line_ids": ["P5L003"], "explanation_line_ids": [], "answer_source": "document_answer_table", "explanation_source": "llm_fallback", "expected_content": {"stem": line_map["P2L002"], "options": {"A": "77分贝", "B": "80分贝", "C": "82分贝", "D": "84分贝"}, "answer": "D"}, "expected_anchor": {"stem_line_ids": ["P2L002"], "options_line_ids": ["P2L003"], "answer_line_ids": ["P5L003"], "explanation_line_ids": []}, "difficulty": 2, "score": 5.0, "knowledge_points": ["对数运算", "声学应用"], "confidence": 1.0, "source_page": 2})

# Q10
golden["questions"].append({"question_number": "10", "question_type": "single_choice", "section_id": "选择题", "stem_line_ids": ["P2L004"], "options_line_ids": {"A": ["P2L005"], "B": ["P2L005"], "C": ["P2L005"], "D": ["P2L005"]}, "answer": "D", "answer_line_ids": ["P5L003"], "explanation_line_ids": [], "answer_source": "document_answer_table", "explanation_source": "llm_fallback", "expected_content": {"stem": line_map["P2L004"], "options": {"A": "506", "B": "507", "C": "675", "D": "676"}, "answer": "D"}, "expected_anchor": {"stem_line_ids": ["P2L004"], "options_line_ids": ["P2L005"], "answer_line_ids": ["P5L003"], "explanation_line_ids": []}, "difficulty": 4, "score": 5.0, "knowledge_points": ["集合", "组合最值"], "confidence": 1.0, "source_page": 2})

# Q11
golden["questions"].append({"question_number": "11", "question_type": "fill_blank", "section_id": "填空题", "stem_line_ids": ["P2L008"], "options_line_ids": {}, "answer": "√2/2", "answer_line_ids": ["P5L005"], "explanation_line_ids": [], "answer_source": "document_answer_table", "explanation_source": "llm_fallback", "expected_content": {"stem": line_map["P2L008"], "options": {}, "answer": "√2/2"}, "expected_anchor": {"stem_line_ids": ["P2L008"], "answer_line_ids": ["P5L005"], "explanation_line_ids": []}, "difficulty": 1, "score": 5.0, "knowledge_points": ["三角函数", "特殊角"], "confidence": 1.0, "source_page": 2})

# Q13
golden["questions"].append({"question_number": "13", "question_type": "fill_blank", "section_id": "填空题", "stem_line_ids": ["P2L010"], "options_line_ids": {}, "answer": "7", "answer_line_ids": ["P5L005"], "explanation_line_ids": [], "answer_source": "document_answer_table", "explanation_source": "llm_fallback", "expected_content": {"stem": line_map["P2L010"], "options": {}, "answer": "7"}, "expected_anchor": {"stem_line_ids": ["P2L010"], "answer_line_ids": ["P5L005"], "explanation_line_ids": []}, "difficulty": 2, "score": 5.0, "knowledge_points": ["均值不等式", "最值"], "confidence": 1.0, "source_page": 2})

# Save
with open("test/annotations/golden/math_real_golden.json", "w", encoding="utf-8") as f:
    json.dump(golden, f, ensure_ascii=False, indent=2)
print("Golden file updated with %d questions" % len(golden["questions"]))
