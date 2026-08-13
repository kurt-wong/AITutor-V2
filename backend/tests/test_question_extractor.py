import asyncio
import json
from pathlib import Path

from app.domains.document.ocr.providers import (
    MockOCRProvider,
    OCRFallbackChain,
)
from app.domains.document.parser import DocumentParser
from app.domains.document.question_extractor import (
    LLMQuestionExtractor,
    QuestionExtractionError,
)


class FakeGateway:
    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        return json.dumps(
            {
                "subject": "数学",
                "questions": [
                    {
                        "question_number": "1",
                        "stem": "函数 f(x)=x^2 的最小值是多少？",
                        "options": [
                            {"label": "A", "text": "0"},
                            {"label": "B", "text": "1"},
                        ],
                        "answer": "A",
                        "explanation": "x^2 的最小值为 0。",
                        "question_type": "单选",
                        "difficulty": 2,
                        "knowledge_points": ["二次函数"],
                        "confidence": 0.95,
                    }
                ],
                "confidence": 0.95,
            },
            ensure_ascii=False,
        )


class FencedGateway:
    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        payload = {
            "questions": [
                {
                    "question_number": "1",
                    "stem": "2 + 2 = ?",
                    "options": [{"label": "A", "text": "4"}],
                    "answer": "A",
                    "explanation": "2 + 2 = 4",
                    "question_type": "choice",
                    "confidence": 0.99,
                }
            ]
        }
        return f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"


def test_llm_question_extractor_builds_aggregate() -> None:
    extractor = LLMQuestionExtractor(gateway=FakeGateway())

    aggregate = asyncio.run(
        extractor.extract(
            filename="test.pdf",
            markdown="1. 函数 f(x)=x^2 的最小值是多少？",
            metadata={"grade": "高一"},
        )
    )

    assert aggregate.subject == "数学"
    assert aggregate.grade == "高一"
    assert len(aggregate.questions) == 1
    assert aggregate.questions[0].answer == "A"
    assert aggregate.questions[0].knowledge_points == ["二次函数"]


def test_llm_question_extractor_accepts_fenced_json() -> None:
    extractor = LLMQuestionExtractor(gateway=FencedGateway())

    aggregate = asyncio.run(
        extractor.extract(
            filename="test.pdf",
            markdown="1. 2 + 2 = ?",
            metadata={},
        )
    )

    assert len(aggregate.questions) == 1
    assert aggregate.questions[0].answer == "A"


class EmptyGateway:
    async def complete(self, prompt: str, *, temperature: float = 0.2) -> str:
        return json.dumps({"questions": []}, ensure_ascii=False)


def test_llm_question_extractor_rejects_empty_result() -> None:
    extractor = LLMQuestionExtractor(gateway=EmptyGateway())

    try:
        asyncio.run(
            extractor.extract(
                filename="test.pdf",
                markdown="no questions",
                metadata={},
            )
        )
    except QuestionExtractionError:
        return
    raise AssertionError("expected QuestionExtractionError")


def test_document_parser_uses_mock_ocr_provider() -> None:
    extractor = LLMQuestionExtractor(gateway=FakeGateway())
    parser = DocumentParser(
        ocr_chain=OCRFallbackChain([MockOCRProvider()]),
        question_extractor=extractor,
    )

    aggregate = asyncio.run(
        parser.parse_pdf(
            Path("test.pdf"),
            filename="test.pdf",
            subject="数学",
        )
    )

    assert aggregate.provider == "mock"
    assert aggregate.subject == "数学"
    assert len(aggregate.questions) == 1
