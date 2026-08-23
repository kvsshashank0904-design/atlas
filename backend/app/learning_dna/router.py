import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.students.models import StudentProfile
from app.students.dependencies import get_current_student_profile
from app.curriculum.models import Concept
from app.learning_dna.models import LearningState
from app.learning_dna.service import explain_learning_state
from app.learning_dna.schemas import LearningStateOut, LearningStateExplanationOut

router = APIRouter(prefix="/learning-dna", tags=["learning-dna"])


def _to_learning_state_out(state: LearningState, concept: Concept) -> LearningStateOut:
    return LearningStateOut(
        concept_id=concept.id,
        concept_code=concept.concept_code,
        concept_name=concept.name,
        concept_mastery=state.concept_mastery,
        accuracy=state.accuracy,
        problem_solving_score=state.problem_solving_score,
        hint_dependence=state.hint_dependence,
        evidence_count=state.evidence_count,
        confidence_score=state.confidence_score,
        last_updated=state.last_updated,
    )


@router.get("/me", response_model=list[LearningStateOut])
def get_my_learning_dna(
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    """
    Section 33. Student is derived entirely from the JWT via
    get_current_student_profile — there is no student_id parameter
    anywhere on this route, so a client cannot request another
    student's data even by accident. Returns [] if the student has no
    LearningState rows yet, which is a normal state, not an error.
    """
    rows = (
        db.query(LearningState, Concept)
        .join(Concept, LearningState.concept_id == Concept.id)
        .filter(LearningState.student_id == student.id)
        .all()
    )
    return [_to_learning_state_out(state, concept) for state, concept in rows]


@router.get("/me/{concept_id}", response_model=LearningStateOut)
def get_my_learning_dna_for_concept(
    concept_id: uuid.UUID,
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    """
    404s both when the concept doesn't exist and when this student has
    no LearningState for it — deliberately the same response in both
    cases so the endpoint never confirms or denies that another
    student's LearningState exists for a valid concept_id.
    """
    concept = db.get(Concept, concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    state = (
        db.query(LearningState)
        .filter(LearningState.student_id == student.id, LearningState.concept_id == concept_id)
        .first()
    )
    if not state:
        raise HTTPException(status_code=404, detail="No Learning DNA for this concept yet")

    return _to_learning_state_out(state, concept)


@router.get("/me/{concept_id}/explanation", response_model=LearningStateExplanationOut)
def get_my_learning_dna_explanation(
    concept_id: uuid.UUID,
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    """
    Section 42. Fully deterministic — see
    learning_dna/service.explain_learning_state. No LLM call, no stored
    explanation text, and no answer/solution data anywhere in the
    response (it's derived purely from EvidenceEvent, which never held
    that data in the first place).
    """
    concept = db.get(Concept, concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    explanation = explain_learning_state(db, student.id, concept_id)
    return LearningStateExplanationOut(**explanation)
