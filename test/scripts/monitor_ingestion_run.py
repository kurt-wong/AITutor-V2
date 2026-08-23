"""Monitor the 30-PDF real ingestion run: sample task/doc/question counts over time.

Usage:
    python test/scripts/monitor_ingestion_run.py --interval 60 --out test/results/ingestion_run_snapshot.json

Writes periodic snapshots (status counts, question stats) for post-run data-flow auditing.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "test" / "results" / "ingestion_run_snapshot.json"
API = "http://127.0.0.1:8000"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def sample_db(database_url: str) -> dict:
    eng = create_async_engine(database_url)
    out = {}
    try:
        async with eng.connect() as c:
            for label, sql in [
                ("tasks", "SELECT status, count(*) FROM background_tasks GROUP BY status"),
                ("documents", "SELECT processing_status, count(*) FROM documents GROUP BY processing_status"),
                ("questions", "SELECT count(*) FROM questions"),
                ("question_instances", "SELECT count(*) FROM question_instances"),
                ("question_images", "SELECT count(*) FROM question_images"),
                ("question_knowledge", "SELECT count(*) FROM question_knowledge"),
            ]:
                try:
                    rows = await c.execute(text(sql))
                    result_rows = rows.fetchall()
                    if len(result_rows) == 1 and len(result_rows[0]) == 1:
                        # 单列 count 查询 → 存 {"count": n}
                        out[label] = {"count": result_rows[0][0]}
                    else:
                        out[label] = {r[0]: r[1] for r in result_rows}
                except Exception as exc:
                    out[label] = {"error": str(exc)[:120]}
    finally:
        await eng.dispose()
    return out


async def sample_api() -> dict:
    out = {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{API}/api/admin/questions", params={"page": 1, "page_size": 1})
            body = r.json()
            out["questions_api_total"] = (body.get("data") or {}).get("total")
    except Exception as exc:
        out["api_error"] = str(exc)[:200]
    return out


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=60)
    parser.add_argument("--max-samples", type=int, default=200)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        env_path = ROOT / "backend" / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    database_url = line.split("=", 1)[1].strip()
    if not database_url:
        print("DATABASE_URL not found")
        sys.exit(1)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    snapshots = []
    print(f"monitor started: interval={args.interval}s out={out_path}")
    for i in range(args.max_samples):
        db = await sample_db(database_url)
        api = await sample_api()
        snap = {"ts": _utcnow(), "sample": i + 1, **db, **api}
        snapshots.append(snap)
        tasks = snap.get("tasks", {})
        docs = snap.get("documents", {})
        q_total = 0
        q = snap.get("questions", {})
        if isinstance(q, dict):
            if "count" in q:
                q_total = q.get("count") or 0
            else:
                q_total = sum(v for v in q.values() if isinstance(v, int))
        inst_total = 0
        qi = snap.get("question_instances", {})
        if isinstance(qi, dict):
            if "count" in qi:
                inst_total = qi.get("count") or 0
            else:
                inst_total = sum(v for v in qi.values() if isinstance(v, int))
        print(
            f"[{i+1:03d}] {snap['ts']} tasks={tasks} docs={docs} "
            f"questions={q_total} instances={inst_total} api_total={snap.get('questions_api_total')}"
        )
        out_path.write_text(
            json.dumps({"run_id": "30pdf_real_ingestion", "snapshots": snapshots},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # stop condition: all 30 documents completed (based on documents table,
        # not tasks — historical failed task records from pre-retry remain)
        docs_completed = docs.get("completed", 0) if isinstance(docs, dict) else 0
        if docs_completed >= 30:
            print("all 30 documents completed — stopping")
            break
        await asyncio.sleep(args.interval)
    print(f"monitor finished: {len(snapshots)} snapshots -> {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
