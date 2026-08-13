import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from app.application.services import DocumentApplicationService


def test_upload_document_writes_minio_and_publishes_event() -> None:
    async def run() -> None:
        document = SimpleNamespace(id=uuid4())
        task = SimpleNamespace(id=uuid4(), task_type="document_parse")

        document_service = AsyncMock()
        document_service.register_document.return_value = document
        task_service = AsyncMock()
        task_service.create_task.return_value = task
        event_service = AsyncMock()
        storage = Mock()

        service = DocumentApplicationService(
            document_service=document_service,
            task_service=task_service,
            event_service=event_service,
            storage=storage,
        )

        returned_document, returned_task = await service.upload_document(
            filename="期末数学.pdf",
            file_type="pdf",
            file_obj=Mock(),
            size=123,
            content_type="application/pdf",
            subject="数学",
        )

        assert returned_document is document
        assert returned_task is task
        assert storage.put_object.call_count == 1
        object_key = storage.put_object.call_args.kwargs["object_key"]
        assert object_key.startswith("documents/")
        assert object_key.endswith("/期末数学.pdf")
        assert event_service.publish.await_count == 1

    asyncio.run(run())
