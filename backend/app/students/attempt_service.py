"""
The single place where an attempt is graded and its evidence event is
generated. Kept out of the router so the "correctness is always computed
server-side, never trusted from the client" rule lives in exactly one
function and can't be bypassed by a future endpoint.
"""
from sqlalchemy.orm import Session

from app.questions.models import Question
from app.students.attempt_models import Attempt
from app.students.attempt_schemas import AttemptSubmit
from app.evidence.models import EvidenceEvent, EvidenceEventType


def _normalize(answer: str) -> str:
    """
    Simple MVP grading: case/whitespace-insensitive exact match against
    the canonical answer string. Numerical-tolerance or unit-aware
    grading is not attempted in Phase 2 — flagged in later_vault.md.
    """
    return answer.strip().lower()


def grade_and_record_attempt(
    db: Session, student_id, payload: AttemptSubmit, question: Question, *, commit: bool = True
) -> Attempt:
    """
    Grades `payload` against `question.answer` (never against anything
    the client sent), persists the Attempt, then derives exactly one
    EvidenceEvent from it. Both writes happen in the same transaction so
    an Attempt can never exist without its Evidence, or vice versa.
    Pass commit=False when a caller must atomically persist session linkage
    or LearningState too; that caller owns commit/rollback. Flush in either
    mode so subsequent scoring sees the new evidence with autoflush=False.
    """
    is_correct = _normalize(payload.selected_answer) == _normalize(question.answer)

    attempt = Attempt(
        student_id=student_id,
        question_id=question.id,
        selected_answer=payload.selected_answer,
        correct=is_correct,
        response_time_seconds=payload.response_time_seconds,
        hints_used=payload.hints_used,
        confidence=payload.confidence,
        session_id=payload.session_id,
    )
    db.add(attempt)
    db.flush()  # assigns attempt.id, needed for the evidence FK

    evidence = EvidenceEvent(
        student_id=student_id,
        concept_id=question.primary_concept_id,
        question_id=question.id,
        attempt_id=attempt.id,
        event_type=(
            EvidenceEventType.CORRECT_ATTEMPT
            if is_correct
            else EvidenceEventType.INCORRECT_ATTEMPT
        ),
        correct=is_correct,
        difficulty=question.difficulty,
        question_type=question.question_type.value,
        response_time_seconds=payload.response_time_seconds,
        hints_used=payload.hints_used,
    )
    db.add(evidence)

    db.flush()
    if commit:
        db.commit()
        db.refresh(attempt)
    return attempt
