"""
Phase 2B 测试 — 基础统计与搜索。

覆盖（ROADMAP P4B / PLAN_QUESTION_FAMILY §7.2）：
1. 条件搜索：按学科/题型/知识点/年份/学校筛选题目
2. 统计聚合：total / question_type_distribution / knowledge_point_distribution /
   difficulty_distribution / year_trend
3. 高频知识点排行（knowledge_point_distribution 按次数降序）
4. API 层：GET /api/admin/questions + GET /api/admin/statistics

真实 PostgreSQL 集成测试（每个测试函数独立事务回滚）。
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domains.question.repository import QuestionRepository
from app.domains.question.service import QuestionService
from app.models import (
    Document,
    KnowledgeNode,
    Question,
    QuestionImage,
    QuestionInstance,
    QuestionKnowledge,
    QuestionType,
    Subject,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine(settings.database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(async_engine):
    """带事务的 session，测试结束自动回滚。"""
    async with async_engine.connect() as conn:
        async with conn.begin() as transaction:
            session = AsyncSession(bind=conn, expire_on_commit=False)
            yield session
            await transaction.rollback()


async def _setup_fixture_data(db):
    """构造测试数据：2 学科、2 题型、3 知识点、3 道题（不同年份/学校/难度）。

    q1 在 2024 年出现 2 次（朝阳中学 + 西城中学，不同文档）——
    用于区分「出现频率 COUNT(*)」与「题目数 COUNT(DISTINCT question)」两种语义。
    """
    subj_math = Subject(code=f"TST_MATH_{uuid.uuid4().hex[:6]}", name="测试数学")
    subj_phys = Subject(code=f"TST_PHYS_{uuid.uuid4().hex[:6]}", name="测试物理")
    db.add_all([subj_math, subj_phys])
    await db.flush()

    qt_choice = QuestionType(code=f"tst_choice_{uuid.uuid4().hex[:6]}", name="单选题",
                             subject_id=subj_math.id)
    qt_fill = QuestionType(code=f"tst_fill_{uuid.uuid4().hex[:6]}", name="填空题",
                           subject_id=subj_math.id)
    db.add_all([qt_choice, qt_fill])
    await db.flush()

    # 知识点（挂 MATH 学科）
    kp1 = KnowledgeNode(code=f"TST-KP1-{uuid.uuid4().hex[:6]}", name="函数",
                        subject_id=subj_math.id, level=4)
    kp2 = KnowledgeNode(code=f"TST-KP2-{uuid.uuid4().hex[:6]}", name="三角函数",
                        subject_id=subj_math.id, level=4)
    kp3 = KnowledgeNode(code=f"TST-KP3-{uuid.uuid4().hex[:6]}", name="力学",
                        subject_id=subj_phys.id, level=4)
    db.add_all([kp1, kp2, kp3])
    await db.flush()

    # 3 道题
    q1 = Question(subject_id=subj_math.id, grade="高二", stem="函数题1",
                  question_type_id=qt_choice.id, difficulty=2, status="approved",
                  source_type="document", occurrence_count=2)
    q2 = Question(subject_id=subj_math.id, grade="高二", stem="三角函数题",
                  question_type_id=qt_fill.id, difficulty=3, status="approved",
                  source_type="document", occurrence_count=1)
    q3 = Question(subject_id=subj_phys.id, grade="高一", stem="力学题",
                  question_type_id=qt_choice.id, difficulty=4, status="reviewing",
                  source_type="document", occurrence_count=1)
    db.add_all([q1, q2, q3])
    await db.flush()

    # instances（年份/学校）— 需要真实 Document（document_id FK）+ 唯一 qno（避免唯一索引冲突）
    doc = Document(filename=f"t_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                   object_key="test/t.pdf")
    doc2 = Document(filename=f"t2_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                    object_key="test/t2.pdf")
    db.add_all([doc, doc2])
    await db.flush()
    qno_counter = 1
    for q, yr, school, d in [
        (q1, 2024, "朝阳中学", doc), (q1, 2025, "海淀中学", doc),
        (q1, 2024, "西城中学", doc2),  # 同一题同一年出现 2 次（区分 COUNT(*) vs DISTINCT）
        (q2, 2025, "朝阳中学", doc),
        (q3, 2024, "朝阳中学", doc),
    ]:
        db.add(QuestionInstance(
            question_id=q.id, document_id=d.id, source_type="document",
            source_document_name="t.pdf", source_question_number=str(qno_counter),
            year=yr, school=school, occurrence_no=1,
        ))
        qno_counter += 1

    # knowledge 映射
    db.add_all([
        QuestionKnowledge(question_id=q1.id, knowledge_node_id=kp1.id,
                          mapping_source="rule", review_status="approved"),
        QuestionKnowledge(question_id=q2.id, knowledge_node_id=kp2.id,
                          mapping_source="rule", review_status="approved"),
        QuestionKnowledge(question_id=q1.id, knowledge_node_id=kp2.id,
                          mapping_source="rule", review_status="approved"),
        QuestionKnowledge(question_id=q3.id, knowledge_node_id=kp3.id,
                          mapping_source="rule", review_status="approved"),
    ])
    await db.flush()
    return {
        "math": subj_math, "phys": subj_phys,
        "choice": qt_choice, "fill": qt_fill,
        "kp1": kp1, "kp2": kp2, "kp3": kp3,
        "q1": q1, "q2": q2, "q3": q3,
    }


def _make_repo(db) -> QuestionRepository:
    return QuestionRepository(db)


# ═══════════════════════════════════════════════════════════════════
# 1. 条件搜索
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_search_by_subject(db):
    """按学科筛选：数学 2 题，物理 1 题。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    items, total = await repo.search(subject_id=data["math"].id)
    assert total == 2
    assert {q.stem for q in items} == {"函数题1", "三角函数题"}

    items, total = await repo.search(subject_id=data["phys"].id)
    assert total == 1
    assert items[0].stem == "力学题"


@pytest.mark.asyncio
async def test_search_by_question_type(db):
    """按题型筛选。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    items, total = await repo.search(question_type_id=data["fill"].id)
    assert total == 1
    assert items[0].stem == "三角函数题"


@pytest.mark.asyncio
async def test_search_by_year(db):
    """按年份筛选（question_instances.year）。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    # 2024 年：q1（2024）+ q3（2024）
    items, total = await repo.search(year=2024)
    assert total == 2
    stems = {q.stem for q in items}
    assert stems == {"函数题1", "力学题"}

    # 2025 年：q1（2025）+ q2（2025）
    items, total = await repo.search(year=2025)
    assert total == 2
    stems = {q.stem for q in items}
    assert stems == {"函数题1", "三角函数题"}


@pytest.mark.asyncio
async def test_search_by_school(db):
    """按学校筛选。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    items, total = await repo.search(school="海淀中学")
    assert total == 1
    assert items[0].stem == "函数题1"


@pytest.mark.asyncio
async def test_search_by_knowledge_point(db):
    """按知识点筛选（knowledge_node.name 模糊匹配）。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    items, total = await repo.search(knowledge_point="函数")
    # "函数"命中 kp1（函数）→ q1；也命中"三角函数"→ q2、q1
    assert total == 2
    stems = {q.stem for q in items}
    assert stems == {"函数题1", "三角函数题"}


@pytest.mark.asyncio
async def test_search_pagination(db):
    """分页（按学科过滤，避免残留数据干扰）。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    items, total = await repo.search(subject_id=data["math"].id, skip=0, limit=2)
    assert total == 2  # 数学 2 题
    assert len(items) == 2


# ═══════════════════════════════════════════════════════════════════
# 2. 统计聚合
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_statistics_total_and_distributions(db):
    """统计聚合：total / question_type / difficulty / knowledge_point / year_trend。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    stats = await repo.statistics()

    assert stats["total_questions"] == 3
    # 题型分布
    assert stats["question_type_distribution"].get("单选题") == 2
    assert stats["question_type_distribution"].get("填空题") == 1
    # 难度分布
    assert stats["difficulty_distribution"].get("2") == 1
    assert stats["difficulty_distribution"].get("3") == 1
    assert stats["difficulty_distribution"].get("4") == 1
    # 年份趋势
    years = {t["year"]: t["count"] for t in stats["year_trend"]}
    assert years == {2024: 2, 2025: 2}  # distinct question per year


@pytest.mark.asyncio
async def test_statistics_high_frequency_knowledge_points(db):
    """高频知识点排行：knowledge_point_distribution 按出现次数降序。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    stats = await repo.statistics()
    kp_dist = stats["knowledge_point_distribution"]
    # q1 挂 函数+三角函数（2 个知识点），q2 挂三角函数，q3 挂力学
    assert kp_dist.get("函数") == 1
    assert kp_dist.get("三角函数") == 2  # q1 + q2
    assert kp_dist.get("力学") == 1
    # 降序
    counts = list(kp_dist.values())
    assert counts == sorted(counts, reverse=True)


@pytest.mark.asyncio
async def test_statistics_with_subject_filter(db):
    """按学科过滤统计。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    stats = await repo.statistics(subject_id=data["math"].id)
    assert stats["total_questions"] == 2
    assert stats["difficulty_distribution"].get("4") is None  # 物理题难度 4 被排除
    assert stats["knowledge_point_distribution"].get("力学") is None


# ═══════════════════════════════════════════════════════════════════
# 3. 边界条件：空结果 / 多条件组合 / confidence 筛选 / KP×年份趋势
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_search_no_match_returns_empty(db):
    """不存在的 subject_id → total=0, items=[]（空结果边界）。"""
    repo = _make_repo(db)
    items, total = await repo.search(subject_id=uuid.uuid4())
    assert total == 0
    assert items == []


@pytest.mark.asyncio
async def test_search_multi_condition_combination(db):
    """多条件组合过滤：subject + year + knowledge_point 交叉。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    # 数学 + 2024 年：q1（2024）+ q3 是物理 → 只有 q1
    items, total = await repo.search(subject_id=data["math"].id, year=2024)
    assert total == 1
    assert items[0].stem == "函数题1"

    # 数学 + 2024 + 知识点"函数"：只有 q1
    items, total = await repo.search(
        subject_id=data["math"].id, year=2024, knowledge_point="函数"
    )
    assert total == 1
    assert items[0].stem == "函数题1"

    # 数学 + 2025 + 知识点"三角函数"：q1（三角函数）+ q2（三角函数）都在 2025
    items, total = await repo.search(
        subject_id=data["math"].id, year=2025, knowledge_point="三角函数"
    )
    assert total == 2
    stems = {q.stem for q in items}
    assert stems == {"函数题1", "三角函数题"}


@pytest.mark.asyncio
async def test_search_by_confidence(db):
    """按置信度筛选（ACS §5.3 参数）。"""
    from app.models import Question
    from decimal import Decimal

    subj = Subject(code=f"TST_CONF_{uuid.uuid4().hex[:6]}", name="置信度测试")
    db.add(subj)
    await db.flush()
    db.add_all([
        Question(subject_id=subj.id, stem="高置信题", status="approved",
                 source_type="document", confidence=Decimal("0.9")),
        Question(subject_id=subj.id, stem="低置信题", status="reviewing",
                 source_type="document", confidence=Decimal("0.4")),
    ])
    await db.flush()

    repo = _make_repo(db)
    items, total = await repo.search(subject_id=subj.id, confidence=0.9)
    assert total == 1
    assert items[0].stem == "高置信题"

    items, total = await repo.search(subject_id=subj.id, confidence=0.4)
    assert total == 1
    assert items[0].stem == "低置信题"

    items, total = await repo.search(subject_id=subj.id, confidence=0.99)
    assert total == 0


@pytest.mark.asyncio
async def test_statistics_empty_after_nonexistent_filter(db):
    """不存在的 subject_id → 统计全零/空（空结果边界）。"""
    repo = _make_repo(db)
    stats = await repo.statistics(subject_id=uuid.uuid4())
    assert stats["total_questions"] == 0
    assert stats["question_type_distribution"] == {}
    assert stats["knowledge_point_distribution"] == {}
    assert stats["difficulty_distribution"] == {}
    assert stats["year_trend"] == []
    assert stats["kp_year_trend"] == []


@pytest.mark.asyncio
async def test_statistics_kp_year_trend(db):
    """知识点×年份趋势（ROADMAP P4B #3「按年份看趋势」）。

    语义：出现频率 COUNT(instance)（PLAN §6.3 对齐）——
    同一题同一年出现在 N 份试卷 = N 次出现，不是 COUNT(DISTINCT question)。
    fixture 中 q1 在 2024 年出现 2 次（朝阳 + 西城），(函数, 2024) 应为 2 而非 1。
    """
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    stats = await repo.statistics()
    kp_trend = stats["kp_year_trend"]
    # q1 挂 函数+三角函数：2024 年出现 2 次（朝阳+西城）、2025 年出现 1 次（海淀）
    # q2 挂 三角函数：2025 年出现 1 次
    # q3 挂 力学：2024 年出现 1 次
    by_key = {(t["knowledge_point"], t["year"]): t["count"] for t in kp_trend}
    # 关键断言：q1 同一年 2 个 instance → COUNT(*) = 2（若是 COUNT(DISTINCT question) 则为 1）
    assert by_key.get(("函数", 2024)) == 2, (
        f"(函数, 2024) 应为出现频率 2（q1 在 2024 出现 2 次），实际 {by_key.get(('函数', 2024))}"
    )
    assert by_key.get(("函数", 2025)) == 1
    assert by_key.get(("三角函数", 2025)) == 2  # q1(2025) + q2(2025)
    assert by_key.get(("力学", 2024)) == 1


@pytest.mark.asyncio
async def test_statistics_kp_year_trend_with_subject_filter(db):
    """知识点×年份趋势支持学科过滤。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    stats = await repo.statistics(subject_id=data["math"].id)
    kp_trend = stats["kp_year_trend"]
    kp_names = {t["knowledge_point"] for t in kp_trend}
    assert "力学" not in kp_names  # 物理知识点被排除
    assert "函数" in kp_names
    assert "三角函数" in kp_names


# ═══════════════════════════════════════════════════════════════════
# 4. 题目详情真实 DB 集成测试（对抗性审查 F1）
#    images 查询 + occurrence_count 派生 SQL 必须有真实数据验证，
#    不能只靠 mock（mock 永远返回空列表/None，SQL 写错也测不出来）
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_question_detail_returns_images_and_occurrence_count(db):
    """详情查询：真实 DB 验证 images 列表 + occurrence_count 从 COUNT(instances) 派生。"""
    subj = Subject(code=f"TST_DET_{uuid.uuid4().hex[:6]}", name="详情测试")
    db.add(subj)
    await db.flush()

    q = Question(subject_id=subj.id, stem="详情测试题", status="approved",
                 source_type="document", occurrence_count=99)  # 故意设置错误的缓存值
    db.add(q)
    await db.flush()

    # 2 个 documents + 2 个 instances（同题出现 2 次）
    doc1 = Document(filename=f"det1_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                    object_key="test/d1.pdf")
    doc2 = Document(filename=f"det2_{uuid.uuid4().hex[:6]}.pdf", file_type="pdf",
                    object_key="test/d2.pdf")
    db.add_all([doc1, doc2])
    await db.flush()
    db.add_all([
        QuestionInstance(question_id=q.id, document_id=doc1.id, source_type="document",
                         source_document_name=doc1.filename, source_question_number="1",
                         occurrence_no=1),
        QuestionInstance(question_id=q.id, document_id=doc2.id, source_type="document",
                         source_document_name=doc2.filename, source_question_number="3",
                         occurrence_no=1),
    ])

    # 2 张配图（不同 order）
    db.add_all([
        QuestionImage(question_id=q.id, image_key="test/img1.png", image_type="diagram",
                      image_order=1, placement="stem"),
        QuestionImage(question_id=q.id, image_key="test/img2.png", image_type="figure",
                      image_order=0, placement="options"),
    ])
    await db.flush()

    service = QuestionService(QuestionRepository(db))
    question, images, occurrence_count = await service.get_question_detail(q.id)

    assert question is not None
    assert question.id == q.id
    # 出现次数派生（不信任缓存字段 99）
    assert occurrence_count == 2, f"occurrence_count 应为 COUNT(instances)=2，实际 {occurrence_count}"
    # 配图按 image_order 排序：order=0 的 img2 在前
    assert [img.image_key for img in images] == ["test/img2.png", "test/img1.png"]
    assert images[0].placement == "options"
    assert images[1].placement == "stem"


@pytest.mark.asyncio
async def test_question_detail_not_found_returns_none(db):
    """详情查询：不存在的 question_id → (None, [], 0)。"""
    service = QuestionService(QuestionRepository(db))
    question, images, occurrence_count = await service.get_question_detail(uuid.uuid4())
    assert question is None
    assert images == []
    assert occurrence_count == 0


# ═══════════════════════════════════════════════════════════════════
# 5. start_year/end_year 全局过滤（对抗性审查 F3）
#    total 和所有 distribution 必须受年份范围约束，不只是 trend
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_statistics_start_year_filters_total(db):
    """start_year/end_year 全局过滤：total_questions 只统计范围内的题。"""
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    # 无过滤：3 题（q1, q2, q3）
    stats_all = await repo.statistics()
    assert stats_all["total_questions"] == 3

    # start_year=2025：q1(2025) + q2(2025) = 2（q3 只有 2024 被排除）
    stats_2025 = await repo.statistics(start_year=2025)
    assert stats_2025["total_questions"] == 2, (
        f"start_year=2025 时 total 应为 2，实际 {stats_2025['total_questions']}"
    )
    years = {t["year"] for t in stats_2025["year_trend"]}
    assert years == {2025}
    # 题型分布同步过滤：填空题只有 q2（2025 出现）→ 1
    assert stats_2025["question_type_distribution"].get("填空题") == 1
    # kp_year_trend 同步过滤：2024 行必须被排除（q1 挂函数+三角函数都有 2024 instance）
    kp_years = {t["year"] for t in stats_2025["kp_year_trend"]}
    assert kp_years == {2025}, f"kp_year_trend 年份应为 {2025}，实际 {kp_years}"
    by_kp = {(t["knowledge_point"], t["year"]): t["count"] for t in stats_2025["kp_year_trend"]}
    assert by_kp.get(("函数", 2025)) == 1  # q1 在 2025 出现 1 次
    assert by_kp.get(("三角函数", 2025)) == 2  # q1(2025) + q2(2025)

    # end_year=2024：q1(2024) + q3(2024) = 2（q2 只有 2025 被排除）
    stats_2024 = await repo.statistics(end_year=2024)
    assert stats_2024["total_questions"] == 2
    years = {t["year"] for t in stats_2024["year_trend"]}
    assert years == {2024}


@pytest.mark.asyncio
async def test_statistics_knowledge_point_filter(db):
    """statistics 的 knowledge_point 过滤（对抗性审查 G1 回归）。

    此前该参数被静默忽略（ACS §5.4 违反）：GET /api/admin/statistics?knowledge_point=函数
    返回全量统计。修复后过滤影响 total 和所有分布。
    """
    data = await _setup_fixture_data(db)
    repo = _make_repo(db)

    # "函数" 模糊命中 kp1(函数)→q1 + kp2(三角函数)→q2,q1 → total=2（q3 力学被排除）
    stats_func = await repo.statistics(knowledge_point="函数")
    assert stats_func["total_questions"] == 2, (
        f"knowledge_point=函数 应过滤出 2 题（q1+q2），实际 {stats_func['total_questions']}"
    )
    assert stats_func["knowledge_point_distribution"].get("力学") is None
    kp_names = {t["knowledge_point"] for t in stats_func["kp_year_trend"]}
    assert "力学" not in kp_names

    # "力学" 过滤 → 只 q3
    stats_mech = await repo.statistics(knowledge_point="力学")
    assert stats_mech["total_questions"] == 1
    assert stats_mech["knowledge_point_distribution"].get("函数") is None
