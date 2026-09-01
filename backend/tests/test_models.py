from app.models import Base


EXPECTED_TABLES = {
    "answer_extraction_retries",
    "background_tasks",
    "document_processing_logs",
    "documents",
    "domain_events",
    "generation_jobs",
    "generation_results",
    "knowledge_nodes",
    "mastery_records",
    "practice_answers",
    "practice_sessions",
    "question_candidates",
    "question_embeddings",
    "question_images",
    "question_instances",
    "question_knowledge",
    "question_types",
    "questions",
    "subjects",
    "system_configs",
    "users",
    "wrong_questions",
    "wrong_upload_items",
    "wrong_upload_tasks",
}


def test_model_tables_match_dsd() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES
