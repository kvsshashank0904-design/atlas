import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LearningStateOut(BaseModel):
    """
    Response shape for a LearningState row, as-is — no joined concept
    name/code, no derived fields (e.g. "biggest weakness"), and no
    evidence breakdown. Those depend on scoring/explainability logic
    that doesn't exist yet (Phase 3B+). The Field bounds here mirror the
    database CHECK constraints on the model so the API contract and the
    schema agree, but they don't imply anything computes these values
    yet — they just describe what a valid row looks like.
    """
    id: uuid.UUID
    student_id: uuid.UUID
    concept_id: uuid.UUID
    concept_mastery: float = Field(ge=0.0, le=100.0)
    accuracy: float = Field(ge=0.0, le=100.0)
    problem_solving_score: float = Field(ge=0.0, le=100.0)
    hint_dependence: float = Field(ge=0.0, le=100.0)
    evidence_count: int = Field(ge=0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    last_updated: datetime

    class Config:
        from_attributes = True
