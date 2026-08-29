"""
多学科关键词索引构建器

从 9 科知识树（v2 课标教材体系）构建 {keyword → [node_code, ...]} 倒排索引。
每个关键词映射到其节点及其所有祖先节点代码。

向后兼容: get_keyword_index() 签名不变，mapper.py 无需修改。
"""

from __future__ import annotations

from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed
from app.domains.knowledge.tree_seed.math_v2 import MATH_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.physics_v2 import PHYSICS_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.chemistry_v2 import CHEMISTRY_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.biology_v2 import BIOLOGY_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.chinese_v2 import CHINESE_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.english_v2 import ENGLISH_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.politics_v2 import POLITICS_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.history_v2 import HISTORY_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.geography_v2 import GEOGRAPHY_KNOWLEDGE_TREE_V2

# ═══ 全科树（v2 单一节点库） ══════════════════════════════════════════════════════

ALL_KNOWLEDGE_TREES: dict[str, list[KnowledgeTreeSeed]] = {
    "MATH": MATH_KNOWLEDGE_TREE_V2,
    "PHYS": PHYSICS_KNOWLEDGE_TREE_V2,
    "CHEM": CHEMISTRY_KNOWLEDGE_TREE_V2,
    "BIO": BIOLOGY_KNOWLEDGE_TREE_V2,
    "CHN": CHINESE_KNOWLEDGE_TREE_V2,
    "ENG": ENGLISH_KNOWLEDGE_TREE_V2,
    "POLI": POLITICS_KNOWLEDGE_TREE_V2,
    "HIST": HISTORY_KNOWLEDGE_TREE_V2,
    "GEOG": GEOGRAPHY_KNOWLEDGE_TREE_V2,
}

ALL_NODES: list[KnowledgeTreeSeed] = []
for _tree in ALL_KNOWLEDGE_TREES.values():
    ALL_NODES.extend(_tree)


def build_keyword_index(subject: str | None = None) -> dict[str, list[str]]:
    """构建 {keyword: [node_code, ...]} 倒排索引。"""
    nodes = ALL_KNOWLEDGE_TREES[subject] if subject else ALL_NODES

    parents: dict[str, str | None] = {}
    for node in nodes:
        parents[node.code] = node.parent_code

    def _ancestors(code: str) -> list[str]:
        result = [code]
        cur = code
        while parents.get(cur):
            cur = parents[cur]
            if cur:
                result.append(cur)
        return result

    index: dict[str, list[str]] = {}
    for node in nodes:
        codes = _ancestors(node.code)
        for kw in node.keywords:
            key = kw.lower()
            if key not in index:
                index[key] = []
            for c in codes:
                if c not in index[key]:
                    index[key].append(c)
    return index


# ═══ 懒加载全局单例 ═══════════════════════════════════════════════════════════════

_keyword_index: dict[str, list[str]] | None = None


def get_keyword_index() -> dict[str, list[str]]:
    """获取全科关键词→节点代码索引 (懒加载单例)。向后兼容。"""
    global _keyword_index
    if _keyword_index is None:
        _keyword_index = build_keyword_index()
    return _keyword_index


def get_subject_index(subject: str) -> dict[str, list[str]]:
    """获取指定学科的关键词索引。"""
    return build_keyword_index(subject=subject)


def get_node_by_code(code: str) -> KnowledgeTreeSeed | None:
    """按代码查找节点。"""
    for node in ALL_NODES:
        if node.code == code:
            return node
    return None


def get_cross_refs_for_node(code: str) -> list[str]:
    """查询某节点的跨学科关联目标代码列表。"""
    from app.domains.knowledge.tree_seed.cross_refs import CROSS_DISCIPLINARY_LINKS

    targets: list[str] = []
    for link in CROSS_DISCIPLINARY_LINKS:
        if link.source_code == code:
            targets.append(link.target_code)
    return targets
