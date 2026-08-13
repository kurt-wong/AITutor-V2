from app.models import WrongQuestion, WrongUploadItem, WrongUploadTask
from app.repositories.base import BaseRepository


class WrongQuestionRepository(BaseRepository[WrongQuestion]):
    model = WrongQuestion


class WrongUploadTaskRepository(BaseRepository[WrongUploadTask]):
    model = WrongUploadTask


class WrongUploadItemRepository(BaseRepository[WrongUploadItem]):
    model = WrongUploadItem
