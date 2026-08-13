from app.models import MasteryRecord, PracticeAnswer, PracticeSession
from app.repositories.base import BaseRepository


class PracticeSessionRepository(BaseRepository[PracticeSession]):
    model = PracticeSession


class PracticeAnswerRepository(BaseRepository[PracticeAnswer]):
    model = PracticeAnswer


class MasteryRecordRepository(BaseRepository[MasteryRecord]):
    model = MasteryRecord
