"""
Diagnostic session lifecycle for Phase 3D-1. Deliberately does NOT
reimplement grading or evidence creation — every diagnostic answer goes
through app.students.attempt_service.grade_and_record_attempt, the exact
same function Phase 2's POST /attempts uses, so there is only ever one
grading/evidence pipeline in the whole system.

Also deliberately does NOT trigger Learning DNA recalculation or mark a
session COMPLETED — that's Phase 3D-2, per instruction.
"""
import uuid

from sqlalchemy.orm import Session

from app.curriculum.models import Chapter, Concept
from app.questions.models import Question
from app.students.attempt_models import Attempt
from app.students.attempt_schemas import AttemptSubmit
from app.students.attempt_service import grade_and_record_attempt
from app.diagnostics.models import DiagnosticSession, DiagnosticSessionItem
from app.diagnostics.schemas import DiagnosticAnswerSubmit
from app.diagnostics.config import (
    DIAGNOSTIC_DEFAULT_SUBJECT_EXAM_PACK,
    DIAGNOSTIC_DEFAULT_CHAPTER_NAME,
    DIAGNOSTIC_TARGET_DISTRIBUTION,
    DIAGNOSTIC_CATEGORY_CRITERIA,
)


class ChapterNotFoundError(ValueError):
    pass


class InsufficientQuestionBankError(ValueError):
    """
    Raised when the question bank can't satisfy the requested
    distribution. Carries the shortfall detail per category rather than
    just a message, so the caller (the router) can surface exactly
    what's missing instead of a generic failure — PRD instruction: "Do
    not fail silently if the question bank is insufficient."
    """

    def __init__(self, shortfalls: dict[str, dict[str, int]]):
        self.shortfalls = shortfalls
        super().__init__(f"Insufficient questions for diagnostic: {shortfalls}")


class DuplicateAnswerError(ValueError):
    pass


class OutOfSessionQuestionError(ValueError):
    pass


def _question_matches_criteria(question: Question, criteria: dict) -> bool:
    if "question_type" in criteria and question.question_type not in criteria["question_type"]:
        return False
    if (
        "problem_solving_skill" in criteria
        and question.problem_solving_skill not in criteria["problem_solving_skill"]
    ):
        return False
    return True


def select_diagnostic_questions(
    db: Session,
    chapter_id: uuid.UUID,
    distribution: dict[str, int] | None = None,
) -> tuple[list[Question], dict[str, dict[str, int]]]:
    """
    Deterministic, non-adaptive selection across the given chapter's
    concepts, filling each category in DIAGNOSTIC_CATEGORY_CRITERIA up to
    its target count. A `distribution` override is accepted so tests (or
    a future caller) can ask for a smaller mix without touching the
    production defaults in config.py — this is the "configurable
    selection logic" / "allow tests to use smaller fixtures" requirement.

    Returns (selected_questions, shortfalls). shortfalls is empty when
    every category was fully satisfied; non-empty means the bank
    couldn't meet the request for those categories — the caller decides
    what to do (start_diagnostic below treats any shortfall as an error
    rather than silently starting an under-filled diagnostic).

    Selection order within each category is deterministic (concept_code,
    difficulty, then id) so the same question bank always produces the
    same diagnostic — no randomness, no adaptivity, per PRD Section 13.
    """
    distribution = distribution or DIAGNOSTIC_TARGET_DISTRIBUTION

    concept_ids = [c.id for c in db.query(Concept).filter(Concept.chapter_id == chapter_id).all()]
    candidates = (
        db.query(Question).filter(Question.primary_concept_id.in_(concept_ids)).all()
        if concept_ids
        else []
    )

    used_ids: set[uuid.UUID] = set()
    selected: list[Question] = []
    shortfalls: dict[str, dict[str, int]] = {}

    for category, target_count in distribution.items():
        criteria = DIAGNOSTIC_CATEGORY_CRITERIA[category]
        pool = [
            q for q in candidates
            if q.id not in used_ids and _question_matches_criteria(q, criteria)
        ]
        pool.sort(key=lambda q: (q.primary_concept.concept_code, q.difficulty, str(q.id)))

        chosen = pool[:target_count]
        used_ids.update(q.id for q in chosen)
        selected.extend(chosen)

        if len(chosen) < target_count:
            shortfalls[category] = {"requested": target_count, "available": len(chosen)}

    return selected, shortfalls


def _resolve_chapter(db: Session, chapter_id: uuid.UUID | None) -> Chapter:
    if chapter_id is not None:
        chapter = db.get(Chapter, chapter_id)
        if not chapter:
            raise ChapterNotFoundError(f"Chapter {chapter_id} not found.")
        return chapter

    chapter = (
        db.query(Chapter)
        .join(Chapter.subject)
        .filter(
            Chapter.name == DIAGNOSTIC_DEFAULT_CHAPTER_NAME,
        )
        .first()
    )
    # Narrow further by exam_pack in Python since the join's Subject
    # column name (exam_pack) is straightforward to filter directly too;
    # done as a second query attribute check to keep this readable.
    if chapter and chapter.subject.exam_pack != DIAGNOSTIC_DEFAULT_SUBJECT_EXAM_PACK:
        chapter = None
    if not chapter:
        raise ChapterNotFoundError(
            f"No default diagnostic chapter found "
            f"(exam_pack={DIAGNOSTIC_DEFAULT_SUBJECT_EXAM_PACK!r}, "
            f"chapter={DIAGNOSTIC_DEFAULT_CHAPTER_NAME!r})."
        )
    return chapter


def start_diagnostic(
    db: Session,
    student_id: uuid.UUID,
    chapter_id: uuid.UUID | None = None,
    distribution: dict[str, int] | None = None,
) -> DiagnosticSession:
    """
    Resolves the scope, selects questions, and freezes them as
    DiagnosticSessionItem rows in one transaction. Raises
    InsufficientQuestionBankError (never a silent partial diagnostic) if
    the bank can't fill the requested distribution.
    """
    chapter = _resolve_chapter(db, chapter_id)
    questions, shortfalls = select_diagnostic_questions(db, chapter.id, distribution)
    if shortfalls:
        raise InsufficientQuestionBankError(shortfalls)

    session = DiagnosticSession(
        student_id=student_id, chapter_id=chapter.id, total_questions=len(questions)
    )
    db.add(session)
    db.flush()

    for index, question in enumerate(questions):
        db.add(
            DiagnosticSessionItem(session_id=session.id, question_id=question.id, order_index=index)
        )

    db.commit()
    db.refresh(session)
    return session


def get_progress(db: Session, session: DiagnosticSession) -> tuple[int, int]:
    """Returns (answered_count, remaining_count), always derived live from the item rows."""
    answered = (
        db.query(DiagnosticSessionItem)
        .filter(DiagnosticSessionItem.session_id == session.id, DiagnosticSessionItem.attempt_id.isnot(None))
        .count()
    )
    return answered, session.total_questions - answered


def get_next_item(db: Session, session: DiagnosticSession) -> DiagnosticSessionItem | None:
    """First unanswered item in the frozen order, or None if every item has an attempt."""
    return (
        db.query(DiagnosticSessionItem)
        .filter(DiagnosticSessionItem.session_id == session.id, DiagnosticSessionItem.attempt_id.is_(None))
        .order_by(DiagnosticSessionItem.order_index)
        .first()
    )


def submit_diagnostic_answer(
    db: Session,
    session: DiagnosticSession,
    student_id: uuid.UUID,
    payload: DiagnosticAnswerSubmit,
) -> tuple[Attempt, int]:
    """
    Validates the question belongs to this frozen session and hasn't
    already been answered, then grades it via the shared Phase 2
    pipeline. session_id on the resulting Attempt is always this
    session's own id — never taken from the client — so every
    diagnostic attempt is unambiguously traceable to its session.
    """
    item = (
        db.query(DiagnosticSessionItem)
        .filter(
            DiagnosticSessionItem.session_id == session.id,
            DiagnosticSessionItem.question_id == payload.question_id,
        )
        .first()
    )
    if item is None:
        raise OutOfSessionQuestionError(
            "This question is not part of this diagnostic session."
        )
    if item.attempt_id is not None:
        raise DuplicateAnswerError("This diagnostic question has already been answered.")

    question = db.get(Question, payload.question_id)

    attempt_payload = AttemptSubmit(
        question_id=payload.question_id,
        selected_answer=payload.selected_answer,
        response_time_seconds=payload.response_time_seconds,
        hints_used=payload.hints_used,
        confidence=payload.confidence,
        session_id=str(session.id),
    )
    attempt = grade_and_record_attempt(db, student_id, attempt_payload, question)

    item.attempt_id = attempt.id
    db.commit()

    _, remaining = get_progress(db, session)
    return attempt, remaining
