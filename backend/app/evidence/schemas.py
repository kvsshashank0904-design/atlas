import uuid
from datetime import datetime

from pydantic import BaseModel

from app.evidence.models import EvidenceEventType


class EvidenceEventOut(BaseModel):
    """
    Read-only by design: there is no EvidenceEventCreate schema and no
    POST endpoint for evidence anywhere in the API. Evidence is only ever
    produced internally, as a side effect of grading an attempt
    (see attempts/service.py), never submitted directly by a client.
    """
    id: uuid.UUID
    student_id: uuid.UUID
    concept_id: uuid.UUID
    question_id: uuid.UUID
    attempt_id: uuid.UUID
    event_type: EvidenceEventType
    correct: bool
    difficulty: int
    question_type: str
    response_time_seconds: int
    hints_used: int
    timestamp: datetime

    class Config:
        from_attributes = True
