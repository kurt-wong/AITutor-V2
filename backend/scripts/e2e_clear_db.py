"""清除所有文档及关联数据，为全量 e2e 重跑做准备。

删除顺序（按 FK 依赖）：
1. question_images (FK → questions)
2. question_knowledge (FK → questions)
3. domain_events (entity_id 逻辑引用)
4. question_instances (FK → questions + documents)
5. questions
6. document_processing_logs (FK → documents)
7. answer_extraction_retries (FK → documents)
8. background_tasks (逻辑引用)
9. documents
"""
import asyncio
import asyncpg
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DSN = "postgresql://postgres:postgres@localhost:15432/aitutors"

async def main():
    conn = await asyncpg.connect(DSN)
    try:
        # 先记录当前状态
        docs = await conn.fetchval("SELECT COUNT(*) FROM documents")
        questions = await conn.fetchval("SELECT COUNT(*) FROM questions")
        instances = await conn.fetchval("SELECT COUNT(*) FROM question_instances")
        images = await conn.fetchval("SELECT COUNT(*) FROM question_images")
        print(f"清除前: {docs} docs, {questions} questions, {instances} instances, {images} images")

        # 按 FK 依赖顺序删除
        tables = [
            "question_images",
            "question_knowledge",
            "domain_events",
            "question_instances",
            "questions",
            "document_processing_logs",
            "answer_extraction_retries",
            "background_tasks",
            "documents",
        ]

        for table in tables:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            if count > 0:
                await conn.execute(f"DELETE FROM {table}")
                print(f"  DELETE FROM {table}: {count} rows")
            else:
                print(f"  {table}: already empty")

        # 验证清空
        docs2 = await conn.fetchval("SELECT COUNT(*) FROM documents")
        questions2 = await conn.fetchval("SELECT COUNT(*) FROM questions")
        print(f"\n清除后: {docs2} docs, {questions2} questions")
        print("清除完成。")
    finally:
        await conn.close()

asyncio.run(main())
