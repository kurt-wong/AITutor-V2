"""Question type seed data integrity tests."""
from app.domains.question_type_seed.data import ALL_QUESTION_TYPE_SEEDS
from app.domains.question_type_seed.types import QuestionTypeSeed


def test_all_nine_subjects_present():
    """All 9 subjects have seed data."""
    expected = {"MATH", "PHYS", "CHEM", "BIO", "CHN", "ENG", "POLI", "HIST", "GEOG"}
    assert set(ALL_QUESTION_TYPE_SEEDS.keys()) == expected


def test_all_parent_codes_exist():
    """Every parent_code references an existing code."""
    all_codes = set()
    for seeds in ALL_QUESTION_TYPE_SEEDS.values():
        for s in seeds:
            all_codes.add(s.code)
    missing = []
    for seeds in ALL_QUESTION_TYPE_SEEDS.values():
        for s in seeds:
            if s.parent_code and s.parent_code not in all_codes:
                missing.append(f"{s.code} -> {s.parent_code}")
    assert not missing, f"Missing parent codes: {missing}"


def test_no_duplicate_codes():
    """All codes are unique across subjects."""
    all_codes = []
    for seeds in ALL_QUESTION_TYPE_SEEDS.values():
        all_codes.extend(s.code for s in seeds)
    assert len(all_codes) == len(set(all_codes)), "Duplicate codes found"


def test_level_hierarchy():
    """Level 1 nodes have no parent, level 2/3 nodes have a parent."""
    for seeds in ALL_QUESTION_TYPE_SEEDS.values():
        for s in seeds:
            if s.level == 1:
                assert s.parent_code is None, f"L1 node {s.code} has parent"
            else:
                assert s.parent_code is not None, f"L{s.level} node {s.code} has no parent"


def test_all_subjects_have_l1_nodes():
    """Each subject has at least 2 L1 nodes."""
    for subj, seeds in ALL_QUESTION_TYPE_SEEDS.items():
        l1_count = sum(1 for s in seeds if s.level == 1)
        assert l1_count >= 2, f"{subj} has only {l1_count} L1 nodes"


def test_total_count():
    """Total seed count is reasonable (200-300)."""
    total = sum(len(v) for v in ALL_QUESTION_TYPE_SEEDS.values())
    assert 200 <= total <= 300, f"Total {total} is out of expected range"
