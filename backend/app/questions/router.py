import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.curriculum.models import Concept
from app.questions.models import Question, QuestionConcept
from app.questions.schemas import QuestionCreate, QuestionListItem, QuestionDetail

router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("", response_model=QuestionDetail, status_code=201)
def create_question(
    payload: QuestionCreate, db: Session = Depends(get_db), _=Depends(get_current_user)
):
    """
    Content authoring endpoint. No role/permission system exists yet
    (Section 5: don't build complex auth for MVP) — restricting this to
    real content editors is a Phase 1 follow-up, tracked in later_vault.md.
    """
    primary_concept = (
        db.query(Concept).filter(Concept.concept_code == payload.primary_concept_code).first()
    )
    if not primary_concept:
        raise HTTPException(status_code=400, detail="Unknown primary_concept_code")

    question = Question(
        question_text=payload.question_text,
        answer=payload.answer,
        solution=payload.solution,
        primary_concept_id=primary_concept.id,
        difficulty=payload.difficulty,
        question_type=payload.question_type,
        exam_type=payload.exam_type,
        estimated_time_seconds=payload.estimated_time_seconds,
        problem_solving_skill=payload.problem_solving_skill,
        required_strategy=payload.required_strategy,
    )
    db.add(question)
    db.flush()

    for code in payload.additional_concept_codes:
        concept = db.query(Concept).filter(Concept.concept_code == code).first()
        if concept:
            db.add(QuestionConcept(question_id=question.id, concept_id=concept.id))

    db.commit()
    db.refresh(question)
    return question


@router.get("", response_model=list[QuestionListItem])
def list_questions(
    concept_code: str | None = Query(default=None),
    difficulty: int | None = Query(default=None, ge=1, le=5),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(Question)
    if concept_code:
        concept = db.query(Concept).filter(Concept.concept_code == concept_code).first()
        if not concept:
            raise HTTPException(status_code=404, detail="Unknown concept_code")
        query = query.filter(Question.primary_concept_id == concept.id)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    return query.all()


@router.get("/{question_id}", response_model=QuestionListItem)
def get_question_for_attempt(
    question_id: uuid.UUID, db: Session = Depends(get_db), _=Depends(get_current_user)
):
    """Student-facing fetch — answer/solution deliberately withheld."""
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question
