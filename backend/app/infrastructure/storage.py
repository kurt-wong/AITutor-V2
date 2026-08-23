from typing import BinaryIO

from minio import Minio

from app.core.config import settings


class StorageError(RuntimeError):
    pass


class MinIOStorage:
    def __init__(self, client: Minio | None = None) -> None:
        self.bucket = settings.minio_bucket
        self.client = client or Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as exc:
            raise StorageError(f"MinIO bucket unavailable: {exc}") from exc

    def put_object(
        self,
        *,
        object_key: str,
        file_obj: BinaryIO,
        size: int,
        content_type: str,
    ) -> None:
        try:
            self.ensure_bucket()
            file_obj.seek(0)
            self.client.put_object(
                self.bucket,
                object_key,
                file_obj,
                size,
                content_type=content_type,
            )
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f"MinIO upload failed: {exc}") from exc

    def get_object(self, object_key: str) -> bytes:
        """从 MinIO 下载对象并返回 bytes。"""
        try:
            response = self.client.get_object(self.bucket, object_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except Exception as exc:
            raise StorageError(f"MinIO download failed: {exc}") from exc

    def health_check(self) -> bool:
        try:
            self.ensure_bucket()
            return True
        except StorageError:
            return False
