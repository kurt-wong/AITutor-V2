"""
Phase 2B API 测试 — 搜索与统计端点。

用 dependency override 注入 fake service，避免 TestClient + async engine
在无事件循环时的连接池问题（沙箱环境限制）。

覆盖：GET /api/admin/questions（搜索+confidence 参数）、GET /api/admin/statistics（统计）、
GET /api/admin/questions/{id}（详情含配图+occurrence_count 派生）、参数校验。
"""
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_question_application_service
from app.core.database import get_db_session
from app.main import app


class _MockSession:
    """模拟 AsyncSession：resolve 查询返回 None（不匹配任何学科/题型）。

    详情端点会查询 QuestionImage（scalars）和 COUNT(QuestionInstance)（scalar），
    返回空配图列表和 0 次数。
    """

    async def scalar(self, stmt):
        return None

    async def scalars(self, stmt):
        class _Result:
            def __init__(self, items):
                self._items = items

            def __iter__(self):
                return iter(self._items)

        return _Result([])


async def _mock_db_session():
    return _MockSession()


class FakeQuestionApplicationService:
    """模拟 QuestionApplicationService。"""

    def __init__(self) -> None:
        self.last_search_kwargs: dict = {}
        self.last_statistics_kwargs: dict = {}
        self.question_service = SimpleNamespace(
            get_question=self._fake_get_question,
        )

    async def _fake_get_question(self, question_id):
        return SimpleNamespace(
            id=question_id, subject_id=uuid4(), grade="高二", question_type_id=None,
            stem="函数单调性选择题", options=[{"label": "A", "text": "增函数"}],
            answer="A", explanation="详解", difficulty=2, score=4.0,
            source_type="document", source_document_name="a.pdf", status="approved",
            confidence=0.9, occurrence_count=2, is_composite=False,
            created_at=None,
        )

    async def search_questions(self, **kwargs):
        self.last_search_kwargs = kwargs
        items = [
            SimpleNamespace(
                id=uuid4(), subject_id=uuid4(), grade="高二", question_type_id=None,
                stem="函数单调性选择题", options=[{"label": "A", "text": "增函数"}],
                answer="A", explanation="详解", difficulty=2, score=4.0,
                source_type="document", source_document_name="a.pdf", status="approved",
                confidence=0.9, occurrence_count=2, is_composite=False,
                created_at=None,
            )
        ]
        return items, 1

    async def get_question_detail(self, question_id):
        question = await self.question_service.get_question(question_id)
        if question is None:
            return None, [], 0
        return question, [], 0

    async def get_statistics(self, **kwargs):
        self.last_statistics_kwargs = kwargs
        return {
            "total_questions": 3,
            "question_type_distribution": {"单选题": 2, "填空题": 1},
            "knowledge_point_distribution": {"函数": 1, "三角函数": 2},
            "difficulty_distribution": {"2": 1, "3": 1, "4": 1},
            "year_trend": [{"year": 2024, "count": 2}, {"year": 2025, "count": 2}],
            "kp_year_trend": [
                {"knowledge_point": "函数", "year": 2024, "count": 1},
                {"knowledge_point": "三角函数", "year": 2025, "count": 2},
            ],
        }


fake = FakeQuestionApplicationService()


def _override():
    app.dependency_overrides[get_question_application_service] = lambda: fake
    app.dependency_overrides[get_db_session] = _mock_db_session


def _clear():
    app.dependency_overrides.clear()


def test_search_questions_api() -> None:
    """GET /api/admin/questions 返回题目列表。"""
    _override()
    try:
        client = TestClient(app)
        r = client.get("/api/admin/questions?subject=数学&year=2024&page_size=5")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["stem"] == "函数单调性选择题"
        assert data["page"] == 1
    finally:
        _clear()


def test_search_questions_forwards_confidence_param() -> None:
    """confidence 参数透传到 service（ACS §5.3 参数）。"""
    _override()
    try:
        client = TestClient(app)
        r = client.get("/api/admin/questions?confidence=0.9")
        assert r.status_code == 200
        assert fake.last_search_kwargs.get("confidence") == 0.9
    finally:
        _clear()


def test_search_questions_validates_source_type() -> None:
    """非法 source_type → 400。"""
    _override()
    try:
        client = TestClient(app)
        r = client.get("/api/admin/questions?source_type=bogus")
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        _clear()


def test_search_questions_validates_confidence_range() -> None:
    """confidence 超出 0-1 → 422（FastAPI Query 校验）。"""
    _override()
    try:
        client = TestClient(app)
        r = client.get("/api/admin/questions?confidence=1.5")
        assert r.status_code == 422
    finally:
        _clear()


def test_get_question_api() -> None:
    """GET /api/admin/questions/{id} 返回详情含 images + occurrence_count（ACS §5.3 合约）。"""
    _override()
    try:
        client = TestClient(app)
        qid = uuid4()
        r = client.get(f"/api/admin/questions/{qid}")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["stem"] == "函数单调性选择题"
        assert data["occurrence_count"] == 0  # mock session 返回 COUNT=0（派生值，不信任缓存）
        assert data["images"] == []  # mock session 返回空配图列表
    finally:
        _clear()


def test_get_question_not_found() -> None:
    """不存在的 question_id → 404。"""
    _override()
    try:
        fake.question_service.get_question = _fake_none
        client = TestClient(app)
        r = client.get(f"/api/admin/questions/{uuid4()}")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "NOT_FOUND"
    finally:
        fake.question_service.get_question = fake._fake_get_question
        _clear()


async def _fake_none(question_id):
    return None


def test_statistics_api() -> None:
    """GET /api/admin/statistics 返回聚合数据（ACS §5.4 合约）。"""
    _override()
    try:
        client = TestClient(app)
        r = client.get("/api/admin/statistics?subject=数学&start_year=2024")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_questions"] == 3
        assert "question_type_distribution" in data
        assert "knowledge_point_distribution" in data
        assert "difficulty_distribution" in data
        assert "year_trend" in data
        assert "kp_year_trend" in data
    finally:
        _clear()


def test_statistics_forwards_filters() -> None:
    """statistics 过滤参数透传到 service（无需 DB 解析的参数直传）。"""
    _override()
    try:
        client = TestClient(app)
        r = client.get("/api/admin/statistics?grade=高二&knowledge_point=函数")
        assert r.status_code == 200
        assert fake.last_statistics_kwargs.get("grade") == "高二"
        assert fake.last_statistics_kwargs.get("knowledge_point") == "函数"
    finally:
        _clear()
