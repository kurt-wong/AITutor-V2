"""
Seed full knowledge tree from Python tree_seed definitions → DB.

Reads all 9-subject knowledge tree nodes from tree_seed Python files
and inserts/upserts them into the knowledge_nodes table.

Adapted from V1 for V2:
  - Uses UUID primary keys (not int)
  - Imports from app.models.tables instead of app.domains.knowledge.models
  - Skips Phase 4 (cross-disciplinary edges) — V2 has no KnowledgeEdge table
  - Session factory from app.core.database

Usage:
    cd backend
    .venv/Scripts/python.exe scripts/seed_knowledge_tree.py

The seed is idempotent — re-running won't duplicate nodes (matched by code).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text

from app.core.database import async_session_factory
from app.models.tables import KnowledgeNode, Subject
from app.domains.knowledge.tree_seed import (
    ALL_NODES,
    ALL_KNOWLEDGE_TREES,
    CROSS_DISCIPLINARY_LINKS,
    SUBJECT_CODES,
)
from app.domains.knowledge.tree_seed.types import KnowledgeTreeSeed


# ═══ Helpers ════════════════════════════════════════════════════════════════

def _resolve_level(code: str) -> int:
    """Map node code to DSD level from code structure.

    SUBJ          → level 1 (e.g. "MATH")
    SUBJ-MOD      → level 2 (e.g. "MATH-FUNC")
    SUBJ-MOD-NN   → level 3 (e.g. "MATH-FUNC-01")
    SUBJ-MOD-NN-NN → level 4
    SUBJ-MOD-NN-NN-NN → level 5
    """
    parts = code.split("-")
    # Level = number of parts; clamp to [1, 5]
    return min(max(len(parts), 1), 5)


def _derive_subject_code(node_code: str) -> str:
    """Extract subject code from node code: 'MATH-FUNC-01' → 'MATH'."""
    return node_code.split("-")[0]


# ═══ Main Seed Logic ═════════════════════════════════════════════════════════

async def seed_knowledge_tree() -> dict:
    """Seed all knowledge tree nodes.

    Returns stats dict with counts.
    """
    stats: dict = {
        "subjects": 0,
        "nodes_inserted": 0,
        "nodes_updated": 0,
        "nodes_skipped": 0,
        "parent_links_updated": 0,
    }

    # ── Phase 1: Ensure subjects exist ──
    async with async_session_factory() as session:
        # Get existing subjects
        r = await session.execute(select(Subject))
        existing = {s.code: s for s in r.scalars().all()}

        for code, name in SUBJECT_CODES.items():
            if code not in existing:
                subj = Subject(code=code, name=name, description=f"{name} curriculum")
                session.add(subj)
                stats["subjects"] += 1
                print(f"  + Subject: {code} ({name})")

        if stats["subjects"]:
            await session.commit()
        else:
            print("  All 9 subjects already present")

    # ── Phase 2: Insert/update all knowledge nodes ──
    async with async_session_factory() as session:
        # Get subject map: {code: UUID}
        r = await session.execute(select(Subject))
        subject_map: dict[str, UUID] = {s.code: s.id for s in r.scalars().all()}

        # Get existing node codes
        r = await session.execute(select(KnowledgeNode))
        existing_nodes: dict[str, KnowledgeNode] = {
            n.code: n for n in r.scalars().all() if n.code
        }

        # Sort nodes by level (shallow first) so parent FK is available
        sorted_nodes = sorted(ALL_NODES, key=lambda n: _resolve_level(n.code))

        node_id_map: dict[str, UUID] = {}  # code → DB UUID
        # Start with existing nodes
        for code, node in existing_nodes.items():
            node_id_map[code] = node.id

        for node in sorted_nodes:
            level = _resolve_level(node.code)
            subj_code = _derive_subject_code(node.code)
            subject_id = subject_map.get(subj_code)
            if subject_id is None:
                print(f"  WARN: Unknown subject '{subj_code}' for node {node.code}")
                continue

            existing = existing_nodes.get(node.code)
            if existing:
                node_id_map[node.code] = existing.id
                # Update name/description if changed
                updated = False
                if existing.name != node.name:
                    existing.name = node.name
                    updated = True
                if existing.description != node.description:
                    existing.description = node.description or existing.description
                    updated = True
                if existing.level != level:
                    existing.level = level
                    updated = True
                if updated:
                    stats["nodes_updated"] += 1
                else:
                    stats["nodes_skipped"] += 1
            else:
                db_node = KnowledgeNode(
                    subject_id=subject_id,
                    parent_id=None,  # resolved in Phase 3
                    code=node.code,
                    name=node.name,
                    level=level,
                    description=node.description or "",
                )
                session.add(db_node)
                await session.flush()  # Get the ID
                node_id_map[node.code] = db_node.id
                stats["nodes_inserted"] += 1

        await session.commit()
        print(f"  Nodes: {stats['nodes_inserted']} inserted, "
              f"{stats['nodes_updated']} updated, "
              f"{stats['nodes_skipped']} unchanged")

        # ── Phase 3: Resolve parent_id references ──
        parent_updates = 0
        for node in sorted_nodes:
            if node.parent_code and node.parent_code in node_id_map:
                db_id = node_id_map[node.code]
                parent_db_id = node_id_map[node.parent_code]
                # Update parent FK
                await session.execute(
                    text(
                        "UPDATE knowledge_nodes SET parent_id = :pid "
                        "WHERE id = :nid AND parent_id IS NULL"
                    ),
                    {"pid": str(parent_db_id), "nid": str(db_id)},
                )
                parent_updates += 1

        await session.commit()
        stats["parent_links_updated"] = parent_updates
        print(f"  Parent links: {parent_updates} resolved")

    return stats


# ═══ Entry Point ════════════════════════════════════════════════════════════

async def main():
    print("=" * 60)
    print("Knowledge Tree Seed")
    print("=" * 60)

    total_nodes = len(ALL_NODES)
    total_subjects = len(ALL_KNOWLEDGE_TREES)
    total_links = len(CROSS_DISCIPLINARY_LINKS)
    print(f"  Python definitions: {total_nodes} nodes across "
          f"{total_subjects} subjects, {total_links} cross-refs")
    print(f"  (V2: KnowledgeEdge table not present — skipping cross-refs)")

    stats = await seed_knowledge_tree()

    print("-" * 60)
    print(f"  Subjects created:    {stats['subjects']}")
    print(f"  Nodes inserted:      {stats['nodes_inserted']}")
    print(f"  Nodes updated:       {stats['nodes_updated']}")
    print(f"  Nodes unchanged:     {stats['nodes_skipped']}")
    print(f"  Parent links:        {stats['parent_links_updated']}")
    print("=" * 60)
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
