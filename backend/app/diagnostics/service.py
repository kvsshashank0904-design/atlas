"""
Diagnostic session lifecycle for Phase 3D-1/3D-2. Deliberately does NOT
reimplement grading or evidence creation — every diagnostic answer goes
through app.students.attempt_service.grade_and_record_attempt, the exact
same function Phase 2's POST /attempts uses, so there is only ever one
grading/evidence pipeline in the whole system.

Phase 3D-2 adds completion -> Learning DNA recalculation. It reuses
app.learning_dna.service.recalculate_learning_state exactly as-is — no
scoring logic is duplicated here.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.curriculum.models import Chapter, Concept
from app.questions.models import Question
from app.students.attempt_models import Attempt
from app.students.attempt_schemas import AttemptSubmit
from app.students.attempt_service import grade_and_record_attempt
from app.diagnostics.models import DiagnosticSession, DiagnosticSessionItem, DiagnosticStatus
from app.diagnostics.schemas import DiagnosticAnswerSubmit
from app.diagnostics.config import (
    DIAGNOSTIC_DEFAULT_SUBJECT_EXAM_PACK,
    DIAGNOSTIC_DEFAULT_CHAPTER_NAME,
    DIAGNOSTIC_TARGET_DISTRIBUTION,
    DIAGNOSTIC_CATEGORY_CRITERIA,
)
from app.learning_dna.models import LearningState
from app.learning_dna.service import recalculate_learning_state


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


class DiagnosticIncompleteError(ValueError):
    """Raised when /complete is called before every frozen item has an attempt."""
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

    Categories are processed skill-criteria-first, not in the dict's
    declaration order. problem_solving_skill and question_type are
    independent fields on the same Question row, so a skill-based
    category (currently only strategy_selection) can match a question
    that a type-based category (e.g. standard_application, which accepts
    numerical/application/formula_recall/pyq_style) would ALSO match.
    Skill-tagged questions are the narrower, more specific signal, so
    they must be claimed first — otherwise a broad type-based category
    processed earlier can greedily consume questions a skill-based
    category actually needs, understating the bank's true availability
    for that category. This generalizes to any future category/config
    change (it keys off the *kind* of criteria, not category names), so
    it doesn't need to be re-fixed if the distribution is retuned later.
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

    def _category_priority(category: str) -> int:
        return 0 if "problem_solving_skill" in DIAGNOSTIC_CATEGORY_CRITERIA[category] else 1

    ordered_categories = sorted(distribution.items(), key=lambda item: _category_priority(item[0]))

    for category, target_count in ordered_categories:
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


def get_tested_concepts(db: Session, session: DiagnosticSession) -> list[uuid.UUID]:
    """
    The unique primary_concept_id values actually represented among this
    session's frozen DiagnosticSessionItem questions — never a hardcoded
    concept/chapter name, and never inferred from anything other than
    the frozen question set itself. This is what keeps the completion
    step reusable for any future chapter/subject: it only ever looks at
    "which concepts did the questions in THIS session actually belong
    to," regardless of what those concepts are called.

    Sorted by string form of the id purely for deterministic response
    ordering — it carries no other meaning.
    """
    rows = (
        db.query(Question.primary_concept_id)
        .join(DiagnosticSessionItem, DiagnosticSessionItem.question_id == Question.id)
        .filter(DiagnosticSessionItem.session_id == session.id)
        .distinct()
        .all()
    )
    concept_ids = {row[0] for row in rows}
    return sorted(concept_ids, key=str)


def complete_diagnostic(
    db: Session, session: DiagnosticSession
) -> tuple[DiagnosticSession, list[LearningState]]:
    """
    Determines which concepts this session actually tested, calls the
    EXISTING Phase 3B recalculate_learning_state(...) once per concept
    (no scoring logic duplicated here), and marks the session COMPLETED
    only after every recalculation succeeds.

    Idempotent: if the session is already COMPLETED, this skips the
    "fully answered" check (it was already satisfied the first time —
    frozen items never change afterward) and re-runs the same
    recalculation. recalculate_learning_state is itself a pure
    read-evidence/upsert-state operation, so calling it again with no
    new evidence reproduces the same LearningState values and never
    creates a duplicate row (Phase 3A's unique constraint) or touches
    Attempt/EvidenceEvent at all. completed_at is set only on the
    transition into COMPLETED, so repeated calls don't move it.

    Transaction safety: session.status/completed_at are only written
    AFTER every recalculate_learning_state call has returned
    successfully. If recalculation raises partway through, the session
    is left IN_PROGRESS rather than being marked COMPLETED over a
    partial result — the student (or a retry) can safely call complete
    again later, since recalculation is idempotent per concept.
    """
    if session.status != DiagnosticStatus.COMPLETED:
        _, remaining = get_progress(db, session)
        if remaining > 0:
            raise DiagnosticIncompleteError(
                f"Diagnostic session is not fully answered yet: "
                f"{remaining} of {session.total_questions} question(s) remain."
            )

    tested_concept_ids = get_tested_concepts(db, session)

    states: list[LearningState] = [
        recalculate_learning_state(db, session.student_id, concept_id)
        for concept_id in tested_concept_ids
    ]

    if session.status != DiagnosticStatus.COMPLETED:
        session.status = DiagnosticStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)

    return session, states
