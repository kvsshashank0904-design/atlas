from types import SimpleNamespace

from app.auth.models import User
from app.students.models import StudentProfile, PreparationLevel
from app.curriculum.models import Subject, Chapter, Concept, ExamImportance
from app.evidence.models import EvidenceEvent
from app.learning_dna.models import LearningState
from app.learning_dna.service import (
    compute_accuracy,
    compute_concept_mastery,
    compute_problem_solving_score,
    compute_hint_dependence,
    compute_confidence,
    recalculate_learning_state,
)


# ---------------------------------------------------------------------
# Pure formula unit tests — no DB access, per the PRD's requirement that
# scoring logic be testable without a database.
# ---------------------------------------------------------------------

def _evt(correct, question_type, hints_used=0):
    """Lightweight stand-in exposing only what the compute_* functions read."""
    return SimpleNamespace(correct=correct, question_type=question_type, hints_used=hints_used)


def test_accuracy_math():
    events = [_evt(True, "conceptual"), _evt(False, "numerical"), _evt(True, "application")]
    assert compute_accuracy(events) == round(2 / 3 * 100, 2)


def test_accuracy_all_correct_evidence():
    events = [_evt(True, "conceptual"), _evt(True, "numerical"), _evt(True, "transfer")]
    assert compute_accuracy(events) == 100.0


def test_accuracy_all_wrong_evidence():
    events = [_evt(False, "conceptual"), _evt(False, "numerical")]
    assert compute_accuracy(events) == 0.0


def test_accuracy_no_evidence_behavior():
    assert compute_accuracy([]) == 0.0


def test_concept_mastery_weighting_is_deterministic():
    events = [_evt(True, "conceptual"), _evt(False, "transfer")]
    result_1 = compute_concept_mastery(events)
    result_2 = compute_concept_mastery(events)
    assert result_1 == result_2  # same input -> same output every time

    # conceptual (weight 1.0) correct + transfer (weight 0.5) incorrect:
    # weighted correct = 1.0, total weight = 1.5 -> 66.67
    assert result_1 == round(1.0 / 1.5 * 100, 2)


def test_concept_mastery_no_evidence_is_zero():
    assert compute_concept_mastery([]) == 0.0


def test_problem_solving_score_favors_transfer_and_application_evidence():
    # Same accuracy (50%), but the incorrect item is transfer in one case
    # and conceptual in the other — transfer failures should hurt more.
    fails_on_transfer = [_evt(True, "conceptual"), _evt(False, "transfer")]
    fails_on_conceptual = [_evt(False, "conceptual"), _evt(True, "transfer")]

    assert compute_problem_solving_score(fails_on_transfer) < compute_problem_solving_score(
        fails_on_conceptual
    )


def test_recall_only_evidence_has_limited_impact_on_problem_solving_score():
    # All-correct recall-only evidence should still produce a low/limited
    # problem-solving signal relative to all-correct application/transfer
    # evidence, since recall contributes little insight into
    # problem-solving ability even when answered correctly. We verify
    # this by comparing how much a single WRONG recall answer vs a single
    # wrong application/transfer answer drags the score down: recall's
    # low weight means it should barely move the needle.
    mostly_transfer_with_wrong_recall = [
        _evt(True, "transfer"), _evt(True, "transfer"), _evt(False, "formula_recall"),
    ]
    mostly_transfer_with_wrong_transfer = [
        _evt(True, "transfer"), _evt(True, "transfer"), _evt(False, "transfer"),
    ]

    score_wrong_recall = compute_problem_solving_score(mostly_transfer_with_wrong_recall)
    score_wrong_transfer = compute_problem_solving_score(mostly_transfer_with_wrong_transfer)

    # Missing a recall question should hurt the problem-solving score far
    # less than missing a transfer question.
    assert score_wrong_recall > score_wrong_transfer


def test_hint_dependence_increases_when_hints_increase():
    low_hints = [_evt(True, "conceptual", hints_used=0), _evt(True, "conceptual", hints_used=0)]
    high_hints = [_evt(True, "conceptual", hints_used=3), _evt(True, "conceptual", hints_used=3)]
    assert compute_hint_dependence(low_hints) < compute_hint_dependence(high_hints)
    assert compute_hint_dependence(low_hints) == 0.0
    assert compute_hint_dependence(high_hints) == 100.0


def test_hint_dependence_no_evidence_is_zero():
    assert compute_hint_dependence([]) == 0.0


def test_confidence_increases_with_evidence_count():
    counts = [1, 2, 3, 5, 6, 10, 15, 50]
    confidences = [compute_confidence(c) for c in counts]
    assert all(confidences[i] <= confidences[i + 1] for i in range(len(confidences) - 1))
    # and it actually increases somewhere, not just non-decreasing everywhere trivially
    assert confidences[0] < confidences[-1]


def test_confidence_never_reaches_one():
    for count in [1, 5, 10, 50, 1000, 100000]:
        assert compute_confidence(count) < 1.0
    assert compute_confidence(100000) <= 0.90


def test_confidence_zero_with_no_evidence():
    assert compute_confidence(0) == 0.0


# ---------------------------------------------------------------------
# recalculate_learning_state — real DB, real EvidenceEvent rows
# ---------------------------------------------------------------------

def _seed_student_and_concept(db_session, email="rahul@example.com", code="PHY_NLM_001"):
    user = User(name="Rahul", email=email, hashed_password="hashed")
    db_session.add(user)
    db_session.flush()

    student = StudentProfile(
        user_id=user.id,
        available_time_minutes_per_day=180,
        days_available_per_week=6,
        preparation_level=PreparationLevel.SOME_CHAPTERS_COMPLETED,
    )
    db_session.add(student)
    db_session.flush()

    subject = Subject(name="Physics", exam_pack="jee")
    db_session.add(subject)
    db_session.flush()
    chapter = Chapter(subject_id=subject.id, name="Mechanics", order_index=1)
    db_session.add(chapter)
    db_session.flush()
    concept = Concept(
        chapter_id=chapter.id, concept_code=code, name="Newton's Laws",
        difficulty=3, exam_importance=ExamImportance.HIGH,
    )
    db_session.add(concept)
    db_session.commit()

    return student, concept


def _add_evidence(db_session, student_id, concept_id, correct, question_type="numerical", hints_used=0, question_id=None):
    import uuid
    db_session.add(
        EvidenceEvent(
            student_id=student_id,
            concept_id=concept_id,
            question_id=question_id or uuid.uuid4(),
            attempt_id=uuid.uuid4(),
            event_type="correct_attempt" if correct else "incorrect_attempt",
            correct=correct,
            difficulty=2,
            question_type=question_type,
            response_time_seconds=30,
            hints_used=hints_used,
        )
    )
    db_session.commit()


def test_recalculate_creates_learning_state(db_session):
    student, concept = _seed_student_and_concept(db_session)
    _add_evidence(db_session, student.id, concept.id, correct=True)
    _add_evidence(db_session, student.id, concept.id, correct=False)

    state = recalculate_learning_state(db_session, student.id, concept.id)

    assert state is not None
    assert state.student_id == student.id
    assert state.concept_id == concept.id
    assert state.evidence_count == 2
    assert state.accuracy == 50.0

    # exactly one row exists
    count = (
        db_session.query(LearningState)
        .filter_by(student_id=student.id, concept_id=concept.id)
        .count()
    )
    assert count == 1


def test_recalculate_updates_existing_learning_state_instead_of_duplicating(db_session):
    student, concept = _seed_student_and_concept(db_session)
    _add_evidence(db_session, student.id, concept.id, correct=True)

    state_1 = recalculate_learning_state(db_session, student.id, concept.id)
    assert state_1.evidence_count == 1

    _add_evidence(db_session, student.id, concept.id, correct=False)
    state_2 = recalculate_learning_state(db_session, student.id, concept.id)

    assert state_2.id == state_1.id  # same row, upserted
    assert state_2.evidence_count == 2

    count = (
        db_session.query(LearningState)
        .filter_by(student_id=student.id, concept_id=concept.id)
        .count()
    )
    assert count == 1  # never a duplicate


def test_recalculate_with_no_evidence_produces_zeroed_state(db_session):
    student, concept = _seed_student_and_concept(db_session)
    state = recalculate_learning_state(db_session, student.id, concept.id)
    assert state.evidence_count == 0
    assert state.accuracy == 0.0
    assert state.confidence_score == 0.0


def test_evidence_remains_unchanged_after_recalculation(db_session):
    student, concept = _seed_student_and_concept(db_session)
    _add_evidence(db_session, student.id, concept.id, correct=True, question_type="transfer", hints_used=2)

    evidence_before = (
        db_session.query(EvidenceEvent)
        .filter_by(student_id=student.id, concept_id=concept.id)
        .all()
    )
    before_snapshot = [
        (e.id, e.correct, e.question_type, e.hints_used, e.timestamp) for e in evidence_before
    ]

    recalculate_learning_state(db_session, student.id, concept.id)
    recalculate_learning_state(db_session, student.id, concept.id)  # recalculate twice for good measure

    evidence_after = (
        db_session.query(EvidenceEvent)
        .filter_by(student_id=student.id, concept_id=concept.id)
        .all()
    )
    after_snapshot = [
        (e.id, e.correct, e.question_type, e.hints_used, e.timestamp) for e in evidence_after
    ]

    assert before_snapshot == after_snapshot
    assert len(evidence_after) == 1  # no rows added or removed


def test_recalculated_scores_respect_db_constraints(db_session):
    """Every score recalculate_learning_state writes must satisfy Phase 3A's CHECK constraints."""
    student, concept = _seed_student_and_concept(db_session)
    for i in range(15):
        _add_evidence(
            db_session, student.id, concept.id,
            correct=(i % 3 != 0), question_type="transfer", hints_used=i % 4,
        )

    state = recalculate_learning_state(db_session, student.id, concept.id)  # would raise IntegrityError if out of range
    assert 0.0 <= state.concept_mastery <= 100.0
    assert 0.0 <= state.accuracy <= 100.0
    assert 0.0 <= state.problem_solving_score <= 100.0
    assert 0.0 <= state.hint_dependence <= 100.0
    assert 0.0 <= state.confidence_score <= 1.0
    assert state.evidence_count >= 0
