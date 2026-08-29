"""
知识树种子数据完整性测试。

验证知识节点库的关键词不包含纯题型词（题型与知识点正交）。
"""
from app.domains.knowledge.tree_seed import index_builder


# 纯题型词——这些属于 question_type_seed，不应出现在 knowledge_node keywords 中
QUESTION_TYPE_ONLY_WORDS = {
    "七选五",
    "完形填空",
    "cloze",
    "cloze test",
}


def test_knowledge_keywords_exclude_question_type_words():
    """知识节点的关键词不得包含纯题型词。"""
    nodes = index_builder.ALL_NODES
    violations = []
    for node in nodes:
        for kw in node.keywords:
            if kw.strip().lower() in {w.lower() for w in QUESTION_TYPE_ONLY_WORDS}:
                violations.append(f"{node.code} ({node.name}): \"{kw}\"")

    assert not violations, (
        f"Found {len(violations)} question-type words in knowledge keywords:\n"
        + "\n".join(violations)
    )
