from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.students.models import StudentProfile
from app.students.dependencies import get_current_student_profile
from app.students.attempt_models import Attempt
from app.students.attempt_schemas import AttemptSubmit, AttemptOut
from app.students.attempt_service import grade_and_record_attempt
from app.questions.models import Question

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("", response_model=AttemptOut, status_code=201)
def submit_attempt(
    payload: AttemptSubmit,
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    """
    Section 9. `correct` is computed here from Question.answer — the
    client-submitted payload has no `correct` field at all (see
    AttemptSubmit), so there is nothing to "trust" in the first place.
    Grading + evidence creation happen atomically in one service call.
    """
    question = db.get(Question, payload.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    attempt = grade_and_record_attempt(db, student.id, payload, question)
    return attempt


@router.get("/me", response_model=list[AttemptOut])
def get_my_attempts(
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    """
    Section 9 attempt history. Scoped to the authenticated student only —
    student.id comes from get_current_student_profile (derived from the
    JWT), never from a client-supplied student_id, so there is no request
    shape that lets one student read another's attempts.
    """
    return (
        db.query(Attempt)
        .filter(Attempt.student_id == student.id)
        .order_by(Attempt.timestamp.desc())
        .all()
    )
