import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.diagnostics.models import DiagnosticStatus
from app.students.attempt_models import ConfidenceLevel
from app.students.attempt_schemas import AttemptOut


class DiagnosticStartRequest(BaseModel):
    """
    chapter_id is optional so the common case (start a Mechanics
    diagnostic) needs no body at all — the service resolves the default
    scope from diagnostics/config.py. Passing a chapter_id explicitly is
    what makes the same endpoint reusable for a future chapter/subject
    without any route change.
    """
    chapter_id: uuid.UUID | None = None


class DiagnosticSessionOut(BaseModel):
    """
    GET /diagnostics/{id} shape. answered_count/remaining_questions are
    always computed from DiagnosticSessionItem at request time — see the
    model docstring for why nothing here is a stored counter.
    """
    id: uuid.UUID
    chapter_id: uuid.UUID
    status: DiagnosticStatus
    total_questions: int
    answered_count: int
    remaining_questions: int
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime


class DiagnosticNextQuestionOut(BaseModel):
    """
    Student-facing question shape for the diagnostic flow. No
    answer/solution field exists on this schema at all — same
    no-leak guarantee as Phase 1's QuestionListItem, just scoped to the
    diagnostic flow instead of duplicated.
    """
    question_id: uuid.UUID
    question_text: str
    difficulty: int
    question_type: str
    estimated_time_seconds: int
    remaining_questions: int


class DiagnosticNoMoreQuestionsOut(BaseModel):
    diagnostic_complete: bool = True


class DiagnosticAnswerSubmit(BaseModel):
    """
    Same shape as Phase 2's AttemptSubmit minus session_id — the
    diagnostic session supplies its own session_id server-side (see
    diagnostics/service.submit_diagnostic_answer), so a client can never
    attribute a diagnostic answer to a different session.
    """
    question_id: uuid.UUID
    selected_answer: str = Field(min_length=1)
    response_time_seconds: int = Field(ge=0, le=7200)
    hints_used: int = Field(default=0, ge=0)
    confidence: ConfidenceLevel | None = None


class DiagnosticAnswerResult(BaseModel):
    attempt: AttemptOut
    remaining_questions: int
    diagnostic_complete: bool
