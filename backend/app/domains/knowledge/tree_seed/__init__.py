"""
Knowledge Tree Seed Package — 9 学科 × 5 级深度 × 跨学科 DAG 网络

向后兼容: 所有旧导入路径可用（v1 名称指向 v2 数据）。
新增: 9科独立树（v2 课标教材体系）、跨学科关联网络、单科索引、节点查询。
"""

from app.domains.knowledge.tree_seed.types import (
    KnowledgeTreeSeed, CrossDisciplinaryLink, SUBJECT_CODES, RELATION_LABELS,
)
from app.domains.knowledge.tree_seed.math_v2 import MATH_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.physics_v2 import PHYSICS_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.chemistry_v2 import CHEMISTRY_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.biology_v2 import BIOLOGY_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.chinese_v2 import CHINESE_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.english_v2 import ENGLISH_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.politics_v2 import POLITICS_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.history_v2 import HISTORY_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.geography_v2 import GEOGRAPHY_KNOWLEDGE_TREE_V2
from app.domains.knowledge.tree_seed.cross_refs import CROSS_DISCIPLINARY_LINKS
from app.domains.knowledge.tree_seed.index_builder import (
    ALL_KNOWLEDGE_TREES, ALL_NODES,
    build_keyword_index, get_keyword_index, get_subject_index,
    get_node_by_code, get_cross_refs_for_node,
)

# Backward-compatible aliases (v1 names now point to v2 data)
MATH_KNOWLEDGE_TREE = MATH_KNOWLEDGE_TREE_V2
PHYSICS_KNOWLEDGE_TREE = PHYSICS_KNOWLEDGE_TREE_V2
CHEMISTRY_KNOWLEDGE_TREE = CHEMISTRY_KNOWLEDGE_TREE_V2
BIOLOGY_KNOWLEDGE_TREE = BIOLOGY_KNOWLEDGE_TREE_V2
CHINESE_KNOWLEDGE_TREE = CHINESE_KNOWLEDGE_TREE_V2
ENGLISH_KNOWLEDGE_TREE = ENGLISH_KNOWLEDGE_TREE_V2
POLITICS_KNOWLEDGE_TREE = POLITICS_KNOWLEDGE_TREE_V2
HISTORY_KNOWLEDGE_TREE = HISTORY_KNOWLEDGE_TREE_V2
GEOGRAPHY_KNOWLEDGE_TREE = GEOGRAPHY_KNOWLEDGE_TREE_V2

__all__ = [
    "KnowledgeTreeSeed", "CrossDisciplinaryLink", "SUBJECT_CODES", "RELATION_LABELS",
    "MATH_KNOWLEDGE_TREE", "PHYSICS_KNOWLEDGE_TREE", "CHEMISTRY_KNOWLEDGE_TREE",
    "BIOLOGY_KNOWLEDGE_TREE", "CHINESE_KNOWLEDGE_TREE", "ENGLISH_KNOWLEDGE_TREE",
    "POLITICS_KNOWLEDGE_TREE", "HISTORY_KNOWLEDGE_TREE", "GEOGRAPHY_KNOWLEDGE_TREE",
    "MATH_KNOWLEDGE_TREE_V2", "PHYSICS_KNOWLEDGE_TREE_V2", "CHEMISTRY_KNOWLEDGE_TREE_V2",
    "BIOLOGY_KNOWLEDGE_TREE_V2", "CHINESE_KNOWLEDGE_TREE_V2", "ENGLISH_KNOWLEDGE_TREE_V2",
    "POLITICS_KNOWLEDGE_TREE_V2", "HISTORY_KNOWLEDGE_TREE_V2", "GEOGRAPHY_KNOWLEDGE_TREE_V2",
    "CROSS_DISCIPLINARY_LINKS", "ALL_KNOWLEDGE_TREES", "ALL_NODES",
    "build_keyword_index", "get_keyword_index", "get_subject_index",
    "get_node_by_code", "get_cross_refs_for_node",
]
