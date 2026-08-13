from io import BytesIO

from app.infrastructure.storage import MinIOStorage


class FakeMinioClient:
    def __init__(self) -> None:
        self.bucket_exists_calls = 0
        self.make_bucket_calls = 0
        self.put_object_calls = []
        self.bucket = None

    def bucket_exists(self, bucket: str) -> bool:
        self.bucket_exists_calls += 1
        return self.bucket == bucket

    def make_bucket(self, bucket: str) -> None:
        self.make_bucket_calls += 1
        self.bucket = bucket

    def put_object(self, bucket, object_key, file_obj, length, content_type) -> None:
        self.put_object_calls.append(
            {
                "bucket": bucket,
                "object_key": object_key,
                "content_type": content_type,
                "length": length,
            }
        )


def test_storage_ensures_bucket_and_uploads() -> None:
    client = FakeMinioClient()
    storage = MinIOStorage(client=client)
    file_obj = BytesIO(b"pdf-content")

    storage.put_object(
        object_key="documents/abc/test.pdf",
        file_obj=file_obj,
        size=11,
        content_type="application/pdf",
    )

    assert client.make_bucket_calls == 1
    assert client.put_object_calls[0]["object_key"] == "documents/abc/test.pdf"
    assert client.put_object_calls[0]["content_type"] == "application/pdf"
    assert client.put_object_calls[0]["length"] == 11
