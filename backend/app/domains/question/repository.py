from sqlalchemy import func, select
from uuid import UUID

from app.models import (
    Question,
    QuestionEmbedding,
    QuestionImage,
    QuestionInstance,
    QuestionKnowledge,
)
from app.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    model = Question

    async def list_by_filters(
        self,
        *,
        status: str | None = None,
        source_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Question]:
        stmt = select(Question)
        if status is not None:
            stmt = stmt.where(Question.status == status)
        if source_type is not None:
            stmt = stmt.where(Question.source_type == source_type)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result)

    def _build_search_stmt(
        self,
        *,
        subject_id: UUID | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
        question_type_id: UUID | None = None,
        knowledge_point: str | None = None,
        difficulty: int | None = None,
        source_type: str | None = None,
        status: str | None = None,
        confidence: float | None = None,
        count_only: bool = False,
    ):
        """Phase 2B：构建条件搜索 SQL（JOIN instances 支持 year/school，JOIN knowledge 支持知识点）。"""
        if count_only:
            stmt = select(func.count(func.distinct(Question.id)))
        else:
            stmt = select(Question)
        if subject_id is not None:
            stmt = stmt.where(Question.subject_id == subject_id)
        if grade is not None:
            stmt = stmt.where(Question.grade == grade)
        if question_type_id is not None:
            stmt = stmt.where(Question.question_type_id == question_type_id)
        if difficulty is not None:
            stmt = stmt.where(Question.difficulty == difficulty)
        if source_type is not None:
            stmt = stmt.where(Question.source_type == source_type)
        if status is not None:
            stmt = stmt.where(Question.status == status)
        if confidence is not None:
            stmt = stmt.where(Question.confidence == confidence)

        # year / school 在 question_instances（Phase 2A 迁移）
        if year is not None or school is not None:
            stmt = stmt.join(QuestionInstance, QuestionInstance.question_id == Question.id)
            if year is not None:
                stmt = stmt.where(QuestionInstance.year == year)
            if school is not None:
                stmt = stmt.where(QuestionInstance.school == school)

        # knowledge_point 筛选（question_knowledge → knowledge_nodes.name 模糊匹配）
        if knowledge_point is not None:
            from app.models import KnowledgeNode
            stmt = stmt.join(
                QuestionKnowledge, QuestionKnowledge.question_id == Question.id
            ).join(KnowledgeNode, KnowledgeNode.id == QuestionKnowledge.knowledge_node_id)
            stmt = stmt.where(KnowledgeNode.name.ilike(f"%{knowledge_point}%"))
        return stmt

    async def search(
        self,
        *,
        subject_id: UUID | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
        question_type_id: UUID | None = None,
        knowledge_point: str | None = None,
        difficulty: int | None = None,
        source_type: str | None = None,
        status: str | None = None,
        confidence: float | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Question], int]:
        """Phase 2B 条件搜索：按学科/题型/知识点/年份/学校等筛选题目，返回 (items, total)。"""
        stmt = self._build_search_stmt(
            subject_id=subject_id,
            grade=grade,
            year=year,
            school=school,
            question_type_id=question_type_id,
            knowledge_point=knowledge_point,
            difficulty=difficulty,
            source_type=source_type,
            status=status,
            confidence=confidence,
        )
        # distinct（JOIN 多表可能产生重复行）
        stmt = stmt.distinct().order_by(Question.created_at.desc()).offset(skip).limit(limit)
        items = list(await self.session.scalars(stmt))

        count_stmt = self._build_search_stmt(
            subject_id=subject_id,
            grade=grade,
            year=year,
            school=school,
            question_type_id=question_type_id,
            knowledge_point=knowledge_point,
            difficulty=difficulty,
            source_type=source_type,
            status=status,
            confidence=confidence,
            count_only=True,
        )
        total = await self.session.scalar(count_stmt)
        return items, int(total or 0)

    async def statistics(
        self,
        *,
        subject_id: UUID | None = None,
        grade: str | None = None,
        year: int | None = None,
        school: str | None = None,
        question_type_id: UUID | None = None,
        knowledge_point: str | None = None,
        difficulty: int | None = None,
        source_type: str | None = None,
        status: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> dict:
        """Phase 2B 统计聚合：total / question_type_distribution / knowledge_point_distribution /
        difficulty_distribution / year_trend / kp_year_trend
        （基于 question_instances + question_knowledge + questions）。

        年份过滤（对抗性审查 F3）：start_year/end_year 在 _base() 统一处理，
        影响 total 和所有 distribution（不只是 trend），避免「start_year=2024 但 total 仍含旧数据」。

        语义说明（对抗性审查 G3）：
        - year_trend：COUNT(DISTINCT question_id)，「每年有多少道不同的题被考」；
        - kp_year_trend：COUNT(instance)，「某知识点每年出现多少次」（PLAN §6.3 出现频率）。
          两者维度不同（题目数 vs 出现次数），各自可解释，勿混用。
        """
        from app.models import KnowledgeNode, QuestionType

        # 基础过滤（不含直接 join knowledge，避免 join 干扰各分布聚合）
        # 年份/学校过滤统一在此 JOIN instances（单年 year 或范围 start_year/end_year）
        def _base():
            stmt = select(Question.id)
            if subject_id is not None:
                stmt = stmt.where(Question.subject_id == subject_id)
            if grade is not None:
                stmt = stmt.where(Question.grade == grade)
            if question_type_id is not None:
                stmt = stmt.where(Question.question_type_id == question_type_id)
            if difficulty is not None:
                stmt = stmt.where(Question.difficulty == difficulty)
            if source_type is not None:
                stmt = stmt.where(Question.source_type == source_type)
            if status is not None:
                stmt = stmt.where(Question.status == status)
            if year is not None or school is not None or start_year is not None or end_year is not None:
                stmt = stmt.join(QuestionInstance, QuestionInstance.question_id == Question.id)
                if year is not None:
                    stmt = stmt.where(QuestionInstance.year == year)
                if school is not None:
                    stmt = stmt.where(QuestionInstance.school == school)
                if start_year is not None:
                    stmt = stmt.where(QuestionInstance.year >= start_year)
                if end_year is not None:
                    stmt = stmt.where(QuestionInstance.year <= end_year)
            if knowledge_point is not None:
                # Phase 2B 修复（对抗性审查 G1）：knowledge_point 过滤此前被静默忽略
                # （ACS §5.4 查询参数）。用 EXISTS 子查询避免 join 干扰各分布聚合。
                kp_sub = (
                    select(QuestionKnowledge.question_id)
                    .join(KnowledgeNode, KnowledgeNode.id == QuestionKnowledge.knowledge_node_id)
                    .where(KnowledgeNode.name.ilike(f"%{knowledge_point}%"))
                )
                stmt = stmt.where(Question.id.in_(kp_sub))
            return stmt

        result: dict = {
            "total_questions": 0,
            "question_type_distribution": {},
            "knowledge_point_distribution": {},
            "difficulty_distribution": {},
            "year_trend": [],
            "kp_year_trend": [],
        }

        # total（年份过滤已含在 _base() 中）
        result["total_questions"] = int(
            await self.session.scalar(
                select(func.count(func.distinct(Question.id))).where(Question.id.in_(_base()))
            ) or 0
        )

        # question_type_distribution
        qt_rows = await self.session.execute(
            select(QuestionType.name, func.count(func.distinct(Question.id)))
            .join(Question, Question.question_type_id == QuestionType.id)
            .where(Question.id.in_(_base()))
            .group_by(QuestionType.name)
        )
        result["question_type_distribution"] = {r[0] or "unknown": r[1] for r in qt_rows}

        # difficulty_distribution
        diff_rows = await self.session.execute(
            select(Question.difficulty, func.count(func.distinct(Question.id)))
            .where(Question.id.in_(_base()))
            .group_by(Question.difficulty)
        )
        result["difficulty_distribution"] = {str(r[0]): r[1] for r in diff_rows}

        # knowledge_point_distribution（含高频知识点排行，按出现次数降序）
        kp_rows = await self.session.execute(
            select(
                KnowledgeNode.name,
                func.count(func.distinct(QuestionKnowledge.question_id)),
            )
            .join(QuestionKnowledge, QuestionKnowledge.knowledge_node_id == KnowledgeNode.id)
            .where(QuestionKnowledge.question_id.in_(_base()))
            .group_by(KnowledgeNode.name)
            .order_by(func.count(func.distinct(QuestionKnowledge.question_id)).desc())
            .limit(50)
        )
        result["knowledge_point_distribution"] = {r[0]: r[1] for r in kp_rows}

        # year_trend（基于 instances.year；年份范围过滤与 _base() 保持一致）
        trend_stmt = (
            select(
                QuestionInstance.year,
                func.count(func.distinct(QuestionInstance.question_id)),
            )
            .join(Question, Question.id == QuestionInstance.question_id)
            .where(Question.id.in_(_base()))
        )
        if start_year is not None:
            trend_stmt = trend_stmt.where(QuestionInstance.year >= start_year)
        if end_year is not None:
            trend_stmt = trend_stmt.where(QuestionInstance.year <= end_year)
        trend_rows = await self.session.execute(
            trend_stmt.group_by(QuestionInstance.year).order_by(QuestionInstance.year)
        )
        result["year_trend"] = [
            {"year": r[0], "count": r[1]} for r in trend_rows if r[0] is not None
        ]

        # kp_year_trend（Phase 2B：知识点×年份趋势，ROADMAP P4B #3「按年份看趋势」）
        # 回答「某知识点每年考多少次」—— 出现频率 = COUNT(instance)，与 PLAN §6.3 SQL 对齐
        # （COUNT(*) 语义：同一题同一年出现在 N 份试卷 = N 次出现；不是 COUNT(DISTINCT question)）
        kp_trend_stmt = (
            select(
                KnowledgeNode.name,
                QuestionInstance.year,
                func.count(QuestionInstance.id),
            )
            .join(QuestionKnowledge, QuestionKnowledge.knowledge_node_id == KnowledgeNode.id)
            .join(Question, Question.id == QuestionKnowledge.question_id)
            .join(QuestionInstance, QuestionInstance.question_id == Question.id)
            .where(Question.id.in_(_base()))
        )
        if start_year is not None:
            kp_trend_stmt = kp_trend_stmt.where(QuestionInstance.year >= start_year)
        if end_year is not None:
            kp_trend_stmt = kp_trend_stmt.where(QuestionInstance.year <= end_year)
        kp_trend_rows = await self.session.execute(
            kp_trend_stmt.group_by(KnowledgeNode.name, QuestionInstance.year)
            .order_by(KnowledgeNode.name, QuestionInstance.year)
        )
        result["kp_year_trend"] = [
            {"knowledge_point": r[0], "year": r[1], "count": r[2]}
            for r in kp_trend_rows if r[1] is not None
        ]

        return result

    async def find_by_document_and_question_number(
        self,
        document_id: UUID,
        question_number: str,
    ) -> Question | None:
        """通过 question_instances(document_id, source_question_number) 唯一定位 Question。

        Phase 2A Step 2：审核写回时必须更新该文档对应的正确题目，禁止按题号全局匹配。
        """
        stmt = (
            select(Question)
            .join(QuestionInstance, QuestionInstance.question_id == Question.id)
            .where(QuestionInstance.document_id == document_id)
            .where(QuestionInstance.source_question_number == question_number)
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def list_images(self, question_id: UUID) -> list[QuestionImage]:
        """返回题目配图列表（按 image_order 排序）。

        Phase 2B 修复（对抗性审查 F1）：详情端点配图查询从 API 层下沉到 Repository，
        使 SQL 可被真实 DB 集成测试覆盖。
        """
        stmt = (
            select(QuestionImage)
            .where(QuestionImage.question_id == question_id)
            .order_by(QuestionImage.image_order)
        )
        return list(await self.session.scalars(stmt))

    async def count_instances(self, question_id: UUID) -> int:
        """返回题目出现次数 = COUNT(question_instances)。

        Phase 2B 修复（对抗性审查 F5/B5）：occurrence_count 不信任缓存字段，
        由 Instance COUNT 实时派生（PLAN §2.2/2.3「出现次数 = COUNT(instances)」）。
        """
        stmt = (
            select(func.count())
            .select_from(QuestionInstance)
            .where(QuestionInstance.question_id == question_id)
        )
        return int(await self.session.scalar(stmt) or 0)


class QuestionInstanceRepository(BaseRepository[QuestionInstance]):
    model = QuestionInstance


class QuestionImageRepository(BaseRepository[QuestionImage]):
    model = QuestionImage


class QuestionKnowledgeRepository(BaseRepository[QuestionKnowledge]):
    model = QuestionKnowledge


class QuestionEmbeddingRepository(BaseRepository[QuestionEmbedding]):
    model = QuestionEmbedding
