from decimal import Decimal
from uuid import UUID

from app.domains.knowledge.repository import (
    KnowledgeNodeRepository,
    QuestionTypeRepository,
)
from app.domains.knowledge.tree_seed.index_builder import get_subject_index
from app.models import KnowledgeNode, QuestionKnowledge, QuestionType


class KnowledgeService:
    def __init__(
        self,
        node_repository: KnowledgeNodeRepository,
        question_type_repository: QuestionTypeRepository,
    ) -> None:
        self.node_repository = node_repository
        self.question_type_repository = question_type_repository

    async def create_node(
        self,
        *,
        subject_id: UUID,
        code: str,
        name: str,
        parent_id: UUID | None = None,
        level: int = 0,
        description: str | None = None,
    ) -> KnowledgeNode:
        node = KnowledgeNode(
            subject_id=subject_id,
            parent_id=parent_id,
            code=code,
            name=name,
            level=level,
            description=description,
        )
        return await self.node_repository.add(node)

    async def create_question_type(
        self,
        *,
        subject_id: UUID,
        code: str,
        name: str,
        parent_id: UUID | None = None,
        sort_order: int = 0,
    ) -> QuestionType:
        question_type = QuestionType(
            subject_id=subject_id,
            parent_id=parent_id,
            code=code,
            name=name,
            sort_order=sort_order,
        )
        return await self.question_type_repository.add(question_type)

    async def map_question_to_knowledge(
        self,
        *,
        question_id: UUID,
        subject_id: UUID,
        subject_code: str,
        subject_name: str,
        knowledge_points: list[str] | None,
        is_composite: bool = False,
        sub_questions: list | None = None,
        confidence_threshold: float = 0.7,
    ) -> list[QuestionKnowledge]:
        """Phase 2A Step 6：将题目映射到知识树节点并写入 question_knowledge。

        映射规则（rules.md「知识树不可自动扩展 / 映射失败回退 {SUBJ}-UNKNOWN」）：
        - knowledge_points 为空 → 回退 {SUBJ}-UNKNOWN 父节点，review_status='pending'（不静默跳过）
        - 关键词匹配（seed 关键词索引 → node code → DB 节点）：
          confidence = 命中知识点数 / 总知识点数
          confidence >= 阈值 → mapping_source='rule', review_status='approved'
          confidence < 阈值 → review_status='pending'
        - 无命中 → 回退 UNKNOWN + pending
        - 综合题：子题 knowledge_points 也映射（挂同一 question_id）

        Returns:
            写入的 QuestionKnowledge 记录列表
        """
        session = self.node_repository.session
        written: list[QuestionKnowledge] = []

        # 归一化知识点（去重）
        kps = []
        for kp in knowledge_points or []:
            text = str(kp).strip()
            if text and text not in kps:
                kps.append(text)

        # 主知识点映射
        primary_node, primary_conf, primary_source, primary_review = await self._match_one(
            session,
            subject_id=subject_id,
            subject_code=subject_code,
            knowledge_point=";".join(kps) if kps else "",
            confidence_threshold=confidence_threshold,
        )
        if primary_node is not None:
            qk = QuestionKnowledge(
                question_id=question_id,
                knowledge_node_id=primary_node.id,
                confidence=Decimal(str(round(primary_conf, 3))),
                is_primary=True,
                mapping_source=primary_source,
                review_status=primary_review,
            )
            session.add(qk)
            written.append(qk)

        # 综合题子题级映射（子题知识点分别映射）
        if is_composite and sub_questions:
            for sub in sub_questions:
                sub_kps = []
                if isinstance(sub, dict):
                    raw = sub.get("knowledge_points") or []
                else:
                    raw = getattr(sub, "knowledge_points", None) or []
                for kp in raw:
                    text = str(kp).strip()
                    if text and text not in sub_kps:
                        sub_kps.append(text)
                if not sub_kps:
                    continue
                node, conf, source, review = await self._match_one(
                    session,
                    subject_id=subject_id,
                    subject_code=subject_code,
                    knowledge_point=";".join(sub_kps),
                    confidence_threshold=confidence_threshold,
                )
                if node is not None:
                    qk = QuestionKnowledge(
                        question_id=question_id,
                        knowledge_node_id=node.id,
                        confidence=Decimal(str(round(conf, 3))),
                        is_primary=False,
                        mapping_source=source,
                        review_status=review,
                    )
                    session.add(qk)
                    written.append(qk)

        await session.flush()
        return written

    async def _match_one(
        self,
        session,
        *,
        subject_id: UUID,
        subject_code: str,
        knowledge_point: str,
        confidence_threshold: float,
    ) -> tuple[KnowledgeNode | None, float, str, str]:
        """单组知识点匹配，返回 (node, confidence, mapping_source, review_status)。"""
        if not knowledge_point.strip():
            # 知识点为空：不静默跳过，回退 UNKNOWN 父节点 + pending
            unknown = await self._get_or_create_unknown(session, subject_id, subject_code)
            return unknown, 0.0, "rule", "pending"

        # 关键词匹配（seed 关键词索引）
        try:
            index = get_subject_index(subject_code)
        except KeyError:
            index = {}
        kps = [kp.strip() for kp in knowledge_point.split(";") if kp.strip()]
        hits = 0
        matched_codes: list[str] = []
        for kp in kps:
            # 精确关键词命中（kp 本身或包含关系）
            key = kp.lower()
            direct = index.get(key)
            if direct:
                hits += 1
                matched_codes.extend(direct)
            else:
                # 子串匹配：收集**所有**子串命中（不 break），避免只取第一个关键词
                # （对抗性审查修复：原实现 break 后只取第一个匹配关键词，
                #  如 "函数单调性" 只命中 "函数" 而漏掉更具体的 "单调性"）
                sub_hit = False
                for kw, codes in index.items():
                    if kw in kp or kp in kw:
                        matched_codes.extend(codes)
                        sub_hit = True
                if sub_hit:
                    hits += 1

        if hits == 0:
            unknown = await self._get_or_create_unknown(session, subject_id, subject_code)
            return unknown, 0.0, "rule", "pending"

        confidence = hits / len(kps)
        # 收集所有候选节点，选**最具体**（level 最大）的作为主节点
        # （对抗性审查修复：原实现取 matched_codes 第一个，而 index 插入序是父节点在前，
        #  导致 "三角函数" → MATH-ANA（父）而非 MATH-ANA-03（具体），子题映射塌缩到同一节点）
        candidates: list[KnowledgeNode] = []
        seen: set[str] = set()
        for code in matched_codes:
            if code in seen:
                continue
            seen.add(code)
            found = await self.node_repository.find_by_code(code)
            if found is not None and found.subject_id == subject_id:
                candidates.append(found)
        if not candidates:
            unknown = await self._get_or_create_unknown(session, subject_id, subject_code)
            return unknown, confidence, "rule", "pending"
        node = max(candidates, key=lambda n: n.level or 0)

        review_status = "approved" if confidence >= confidence_threshold else "pending"
        return node, confidence, "rule", review_status

    async def _get_or_create_unknown(
        self,
        session,
        subject_id: UUID,
        subject_code: str,
    ) -> KnowledgeNode:
        """查找或创建 {SUBJ}-UNKNOWN 父节点（映射失败回退，知识树不自动扩展其他节点）。"""
        code = f"{subject_code}-UNKNOWN"
        existing = await self.node_repository.find_by_code(code)
        if existing is not None:
            return existing
        node = KnowledgeNode(
            subject_id=subject_id,
            parent_id=None,
            code=code,
            name=f"{subject_code} 未分类",
            level=1,
            description="知识点映射失败时的回退节点（人工审核后重新归类）",
        )
        session.add(node)
        await session.flush()
        return node

    async def commit(self) -> None:
        await self.node_repository.commit()
