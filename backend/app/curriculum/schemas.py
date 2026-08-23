import uuid

from pydantic import BaseModel

from app.curriculum.models import ExamImportance, ConceptStatus


class ConceptOut(BaseModel):
    id: uuid.UUID
    concept_code: str
    name: str
    difficulty: int
    exam_importance: ExamImportance
    status: ConceptStatus
    prerequisite_concept_codes: list[str] = []

    class Config:
        from_attributes = True


class ChapterOut(BaseModel):
    id: uuid.UUID
    name: str
    order_index: int
    concepts: list[ConceptOut] = []

    class Config:
        from_attributes = True


class SubjectOut(BaseModel):
    id: uuid.UUID
    name: str
    exam_pack: str
    chapters: list[ChapterOut] = []

    class Config:
        from_attributes = True
