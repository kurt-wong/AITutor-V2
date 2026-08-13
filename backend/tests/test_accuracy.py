from app.domains.document.evaluation import aggregate_evaluations, evaluate_document


def test_field_level_evaluation_counts_document_and_question_fields() -> None:
    expected = {
        "filename": "a.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "stem": "题干",
                "answer": "A",
            }
        ],
    }
    actual = {
        "filename": "a.pdf",
        "subject": "数学",
        "questions": [
            {
                "question_number": "1",
                "stem": "题干",
                "answer": "B",
            }
        ],
    }

    evaluation = evaluate_document(expected, actual)
    summary = aggregate_evaluations([evaluation])

    assert evaluation["document_fields"]["subject"]["correct"] == 1
    assert evaluation["question_fields"]["answer"]["correct"] == 0
    assert summary["fields"]["answer"]["accuracy"] == 0.0
    assert summary["fields"]["stem"]["accuracy"] == 1.0
