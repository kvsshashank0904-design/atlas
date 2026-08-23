import uuid

from pydantic import BaseModel, Field

from app.questions.models import QuestionType, ExamType, ProblemSolvingSkill


class QuestionCreate(BaseModel):
    question_text: str
    answer: str
    solution: str
    primary_concept_code: str
    additional_concept_codes: list[str] = []
    difficulty: int = Field(ge=1, le=5)
    question_type: QuestionType
    exam_type: ExamType
    estimated_time_seconds: int = Field(ge=10, le=3600)
    problem_solving_skill: ProblemSolvingSkill
    required_strategy: str | None = None


class QuestionListItem(BaseModel):
    """
    Used when serving a question to a student attempting it: NEVER
    include answer/solution here (Section 31 — canonical answers must
    not leak client-side before an attempt is graded).
    """
    id: uuid.UUID
    question_text: str
    difficulty: int
    question_type: QuestionType
    exam_type: ExamType
    estimated_time_seconds: int

    class Config:
        from_attributes = True


class QuestionDetail(QuestionListItem):
    """Full record, for admin/debug view (Section 41) only."""
    answer: str
    solution: str
    primary_concept_id: uuid.UUID
    problem_solving_skill: ProblemSolvingSkill
    required_strategy: str | None
