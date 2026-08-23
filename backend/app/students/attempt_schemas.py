import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.students.attempt_models import ConfidenceLevel


class AttemptSubmit(BaseModel):
    """
    What the client sends. Deliberately has NO `correct` field —
    correctness is never accepted from the client, only computed
    server-side against the canonical Question.answer.
    """
    question_id: uuid.UUID
    selected_answer: str = Field(min_length=1)
    response_time_seconds: int = Field(ge=0, le=7200)
    hints_used: int = Field(default=0, ge=0)
    confidence: ConfidenceLevel | None = None
    session_id: str = Field(min_length=1, max_length=100)


class AttemptOut(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    selected_answer: str
    correct: bool
    response_time_seconds: int
    hints_used: int
    confidence: ConfidenceLevel | None
    session_id: str
    timestamp: datetime

    class Config:
        from_attributes = True
