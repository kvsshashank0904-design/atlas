import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.students.models import StudentProfile
from app.students.dependencies import get_current_student_profile
from app.curriculum.models import Concept
from app.diagnostics.models import DiagnosticSession
from app.diagnostics.schemas import (
    DiagnosticStartRequest,
    DiagnosticSessionOut,
    DiagnosticNextQuestionOut,
    DiagnosticNoMoreQuestionsOut,
    DiagnosticAnswerSubmit,
    DiagnosticAnswerResult,
    DiagnosticCompletionOut,
)
from app.diagnostics import service as diagnostic_service
from app.learning_dna.router import _to_learning_state_out

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def _get_owned_session(
    db: Session, session_id: uuid.UUID, student: StudentProfile
) -> DiagnosticSession:
    """
    Ownership check lives in exactly one place so every route below is
    automatically scoped to "my own diagnostic" — a session_id belonging
    to another student can never be reached through any of these routes.
    404 (not 403) is used deliberately so the endpoint doesn't confirm
    that a given session_id exists at all for someone else's account.
    """
    session = db.get(DiagnosticSession, session_id)
    if not session or session.student_id != student.id:
        raise HTTPException(status_code=404, detail="Diagnostic session not found")
    return session


def _to_session_out(db: Session, session: DiagnosticSession) -> DiagnosticSessionOut:
    answered, remaining = diagnostic_service.get_progress(db, session)
    return DiagnosticSessionOut(
        id=session.id,
        chapter_id=session.chapter_id,
        status=session.status,
        total_questions=session.total_questions,
        answered_count=answered,
        remaining_questions=remaining,
        started_at=session.started_at,
        completed_at=session.completed_at,
        created_at=session.created_at,
    )


@router.post("/start", response_model=DiagnosticSessionOut, status_code=201)
def start_diagnostic(
    payload: DiagnosticStartRequest | None = None,
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    """
    student_id is always student.id from the JWT-derived profile — this
    request body has no student_id field to spoof in the first place.
    The body itself is fully optional (payload defaults to None) so the
    common case — start a Mechanics diagnostic — needs no request body
    at all; explicitly typing it as Optional rather than relying on a
    mutable Pydantic-instance default avoids any ambiguity about how an
    empty request body is handled.
    """
    chapter_id = payload.chapter_id if payload else None
    try:
        session = diagnostic_service.start_diagnostic(db, student.id, chapter_id)
    except diagnostic_service.ChapterNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except diagnostic_service.InsufficientQuestionBankError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "The question bank does not have enough questions to start this diagnostic.",
                "shortfalls": e.shortfalls,
            },
        )
    return _to_session_out(db, session)


@router.get("/{session_id}", response_model=DiagnosticSessionOut)
def get_diagnostic_status(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    session = _get_owned_session(db, session_id, student)
    return _to_session_out(db, session)


@router.get(
    "/{session_id}/next",
    response_model=DiagnosticNextQuestionOut | DiagnosticNoMoreQuestionsOut,
)
def get_next_question(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    """Answer/solution are never on this response — DiagnosticNextQuestionOut has no such fields."""
    session = _get_owned_session(db, session_id, student)
    item = diagnostic_service.get_next_item(db, session)
    if item is None:
        return DiagnosticNoMoreQuestionsOut()

    question = item.question
    _, remaining = diagnostic_service.get_progress(db, session)
    return DiagnosticNextQuestionOut(
        question_id=question.id,
        question_text=question.question_text,
        difficulty=question.difficulty,
        question_type=question.question_type.value,
        estimated_time_seconds=question.estimated_time_seconds,
        remaining_questions=remaining,
    )


@router.post("/{session_id}/answer", response_model=DiagnosticAnswerResult)
def answer_diagnostic_question(
    session_id: uuid.UUID,
    payload: DiagnosticAnswerSubmit,
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    session = _get_owned_session(db, session_id, student)

    try:
        attempt, remaining = diagnostic_service.submit_diagnostic_answer(
            db, session, student.id, payload
        )
    except diagnostic_service.OutOfSessionQuestionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except diagnostic_service.DuplicateAnswerError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return DiagnosticAnswerResult(
        attempt=attempt, remaining_questions=remaining, diagnostic_complete=remaining == 0
    )


@router.post("/{session_id}/complete", response_model=DiagnosticCompletionOut)
def complete_diagnostic(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    student: StudentProfile = Depends(get_current_student_profile),
):
    """
    Section 13's "EvidenceEvents -> Learning DNA -> LearningState" flow,
    triggered explicitly rather than automatically, and reusing Phase
    3B's recalculate_learning_state as-is (see
    diagnostics/service.complete_diagnostic — no scoring logic lives
    here). Idempotent: calling this again on an already-completed
    session safely re-returns a (re-)computed result rather than erroring
    or duplicating anything.
    """
    session = _get_owned_session(db, session_id, student)

    try:
        session, states = diagnostic_service.complete_diagnostic(db, session)
    except diagnostic_service.DiagnosticIncompleteError as e:
        raise HTTPException(status_code=400, detail=str(e))

    answered, _ = diagnostic_service.get_progress(db, session)
    tested_concept_ids = diagnostic_service.get_tested_concepts(db, session)

    concepts_by_id = {
        c.id: c for c in db.query(Concept).filter(Concept.id.in_(tested_concept_ids)).all()
    }
    # states is already ordered to match tested_concept_ids (see
    # complete_diagnostic), so this stays deterministic.
    learning_states = [_to_learning_state_out(state, concepts_by_id[state.concept_id]) for state in states]

    return DiagnosticCompletionOut(
        id=session.id,
        status=session.status,
        total_questions=session.total_questions,
        answered_count=answered,
        completed_at=session.completed_at,
        concepts_evaluated=tested_concept_ids,
        learning_states=learning_states,
    )
