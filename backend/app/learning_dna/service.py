"""
Phase 3B: deterministic Learning DNA scoring.

Every compute_* function below is pure — it takes plain data (not
EvidenceEvent ORM objects specifically, just objects/records exposing
`.correct`, `.question_type`, `.hints_used`) and returns a number, so
each formula can be unit-tested with zero database access. Only
recalculate_learning_state touches the DB, and its job is limited to:
fetch evidence, call the pure functions, upsert LearningState. It never
computes a score itself and never calls an LLM (PRD Section 29/31 — the
LLM must not calculate scores).

EvidenceEvent rows are only ever read here, never modified — Section 10
and Phase 3A's own docstring both establish that EvidenceEvent is
immutable history and LearningState is derived current state, and this
module is the derivation, not a second history.
"""
import uuid

from sqlalchemy.orm import Session

from app.evidence.models import EvidenceEvent
from app.learning_dna.models import LearningState
from app.learning_dna.config import (
    CONCEPT_MASTERY_WEIGHTS,
    CONCEPT_MASTERY_DEFAULT_WEIGHT,
    PROBLEM_SOLVING_WEIGHTS,
    PROBLEM_SOLVING_DEFAULT_WEIGHT,
    HINT_DEPENDENCE_MAX_HINTS,
    CONFIDENCE_BUCKETS,
    CONFIDENCE_INCREMENT_PER_EXTRA_EVIDENCE,
    CONFIDENCE_MAX,
)


def _weighted_accuracy(events, weights: dict[str, float], default_weight: float) -> float:
    """
    Weighted percent-correct: each event contributes its question_type's
    weight to the denominator, and that same weight to the numerator
    only if the attempt was correct. A question_type missing from
    `weights` still counts (via `default_weight`) rather than being
    silently dropped.
    """
    total_weight = 0.0
    correct_weight = 0.0
    for event in events:
        weight = weights.get(event.question_type, default_weight)
        total_weight += weight
        if event.correct:
            correct_weight += weight
    if total_weight == 0:
        return 0.0
    return round((correct_weight / total_weight) * 100, 2)


def compute_accuracy(events) -> float:
    """MVP placeholder, not scientifically validated: correct relevant
    evidence / total relevant evidence * 100 (unweighted, per PRD)."""
    if not events:
        return 0.0
    correct = sum(1 for e in events if e.correct)
    return round((correct / len(events)) * 100, 2)


def compute_concept_mastery(events) -> float:
    """MVP placeholder, not scientifically validated: weighted accuracy
    favoring conceptual/application question types over multi-step/transfer."""
    return _weighted_accuracy(events, CONCEPT_MASTERY_WEIGHTS, CONCEPT_MASTERY_DEFAULT_WEIGHT)


def compute_problem_solving_score(events) -> float:
    """MVP placeholder, not scientifically validated: weighted accuracy
    favoring application/multi-step/transfer, de-emphasizing pure recall."""
    return _weighted_accuracy(events, PROBLEM_SOLVING_WEIGHTS, PROBLEM_SOLVING_DEFAULT_WEIGHT)


def compute_hint_dependence(events) -> float:
    """MVP placeholder, not scientifically validated: average hints used
    per attempt, normalized to 0-100 against the 3-hint ladder."""
    if not events:
        return 0.0
    avg_hints = sum(e.hints_used for e in events) / len(events)
    return min(100.0, round((avg_hints / HINT_DEPENDENCE_MAX_HINTS) * 100, 2))


def compute_confidence(evidence_count: int) -> float:
    """
    MVP placeholder, not scientifically validated and NOT statistical
    certainty — it only reflects "how much evidence backs this number."
    Monotonically non-decreasing in evidence_count, always < 1.0 per the
    PRD's explicit requirement that confidence never reach 100%.
    """
    if evidence_count <= 0:
        return 0.0
    for threshold, value in CONFIDENCE_BUCKETS:
        if evidence_count <= threshold:
            return value
    last_threshold, last_value = CONFIDENCE_BUCKETS[-1]
    extra = evidence_count - last_threshold
    confidence = last_value + extra * CONFIDENCE_INCREMENT_PER_EXTRA_EVIDENCE
    return round(min(confidence, CONFIDENCE_MAX), 4)


def compute_metrics(events) -> dict:
    """
    Single source of truth for "what do these evidence events say" —
    used by recalculate_learning_state. Kept as one function so callers
    (and tests) get all metrics computed from the exact same evidence
    set in one pass.
    """
    return {
        "concept_mastery": compute_concept_mastery(events),
        "accuracy": compute_accuracy(events),
        "problem_solving_score": compute_problem_solving_score(events),
        "hint_dependence": compute_hint_dependence(events),
        "evidence_count": len(events),
        "confidence_score": compute_confidence(len(events)),
    }


def _fetch_relevant_evidence(
    db: Session, student_id: uuid.UUID, concept_id: uuid.UUID
) -> list[EvidenceEvent]:
    """'Relevant evidence' for Phase 3B = all EvidenceEvent rows for this
    (student, concept) pair. EvidenceEvent is read-only here."""
    return (
        db.query(EvidenceEvent)
        .filter(EvidenceEvent.student_id == student_id, EvidenceEvent.concept_id == concept_id)
        .order_by(EvidenceEvent.timestamp)
        .all()
    )


def recalculate_learning_state(
    db: Session, student_id: uuid.UUID, concept_id: uuid.UUID
) -> LearningState:
    """
    Fetches all evidence for (student, concept), recomputes every metric
    from scratch (never incrementally patched), and upserts the single
    LearningState row for that pair — creating it if this is the first
    calculation, updating it in place otherwise (never a second row,
    thanks to Phase 3A's unique constraint). EvidenceEvent rows are only
    read, never written.

    With zero evidence, still upserts a LearningState at all-zero/no-
    confidence values rather than raising — "no evidence yet" is a valid,
    representable state, not an error.
    """
    events = _fetch_relevant_evidence(db, student_id, concept_id)
    metrics = compute_metrics(events)

    state = (
        db.query(LearningState)
        .filter(LearningState.student_id == student_id, LearningState.concept_id == concept_id)
        .first()
    )
    if state:
        state.concept_mastery = metrics["concept_mastery"]
        state.accuracy = metrics["accuracy"]
        state.problem_solving_score = metrics["problem_solving_score"]
        state.hint_dependence = metrics["hint_dependence"]
        state.evidence_count = metrics["evidence_count"]
        state.confidence_score = metrics["confidence_score"]
    else:
        state = LearningState(
            student_id=student_id,
            concept_id=concept_id,
            concept_mastery=metrics["concept_mastery"],
            accuracy=metrics["accuracy"],
            problem_solving_score=metrics["problem_solving_score"],
            hint_dependence=metrics["hint_dependence"],
            evidence_count=metrics["evidence_count"],
            confidence_score=metrics["confidence_score"],
        )
        db.add(state)

    db.commit()
    db.refresh(state)
    return state
