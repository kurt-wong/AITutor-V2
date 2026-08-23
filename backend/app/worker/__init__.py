"""Background task worker for document processing."""

from app.worker.document_worker import document_parse_worker

__all__ = ["document_parse_worker"]
