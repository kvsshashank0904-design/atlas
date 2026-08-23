import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LearningStateOut(BaseModel):
    """
    Response shape for GET /learning-dna/me and its detail endpoint.
    Extends the Phase 3A row with concept_code/concept_name (Phase 3C:
    "include concept identification useful to a future frontend") — the
    router joins Concept to populate these two fields; everything else
    is the LearningState row as-is. Still no answer/solution data
    anywhere, since this model never touches Question at all.
    """
    concept_id: uuid.UUID
    concept_code: str
    concept_name: str
    concept_mastery: float = Field(ge=0.0, le=100.0)
    accuracy: float = Field(ge=0.0, le=100.0)
    problem_solving_score: float = Field(ge=0.0, le=100.0)
    hint_dependence: float = Field(ge=0.0, le=100.0)
    evidence_count: int = Field(ge=0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    last_updated: datetime


class QuestionTypeBreakdownItem(BaseModel):
    question_type: str
    count: int
    correct_count: int
    accuracy: float = Field(ge=0.0, le=100.0)


class LearningStateExplanationOut(BaseModel):
    """
    GET /learning-dna/me/{concept_id}/explanation shape. Every field is
    computed live from EvidenceEvent in learning_dna/service.explain_learning_state
    — nothing here is stored, and nothing here is LLM-generated.
    """
    concept_id: uuid.UUID
    evidence_count: int = Field(ge=0)
    correct_count: int = Field(ge=0)
    incorrect_count: int = Field(ge=0)
    average_hints_used: float = Field(ge=0.0)
    question_type_breakdown: list[QuestionTypeBreakdownItem]
    strongest_signal: str | None
    weakest_signal: str | None
    confidence_explanation: str
