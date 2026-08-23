import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.models import User
from app.students.models import StudentProfile, PreparationLevel
from app.curriculum.models import Subject, Chapter, Concept, ExamImportance
from app.learning_dna.models import LearningState


def _seed_student_and_concept(db_session):
    user = User(name="Rahul", email="rahul@example.com", hashed_password="hashed")
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
        chapter_id=chapter.id, concept_code="PHY_NLM_001", name="Newton's Laws",
        difficulty=3, exam_importance=ExamImportance.HIGH,
    )
    db_session.add(concept)
    db_session.commit()

    return student, concept


def test_learning_state_can_be_created_with_values_stored_correctly(db_session):
    student, concept = _seed_student_and_concept(db_session)

    state = LearningState(
        student_id=student.id,
        concept_id=concept.id,
        concept_mastery=78.5,
        accuracy=71.0,
        problem_solving_score=49.25,
        hint_dependence=34.0,
        evidence_count=24,
        confidence_score=0.73,
    )
    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    fetched = db_session.query(LearningState).filter_by(id=state.id).first()
    assert fetched is not None
    assert fetched.student_id == student.id
    assert fetched.concept_id == concept.id
    assert fetched.concept_mastery == 78.5
    assert fetched.accuracy == 71.0
    assert fetched.problem_solving_score == 49.25
    assert fetched.hint_dependence == 34.0
    assert fetched.evidence_count == 24
    assert fetched.confidence_score == 0.73
    assert fetched.last_updated is not None


def test_learning_state_student_and_concept_relationships_work(db_session):
    student, concept = _seed_student_and_concept(db_session)

    state = LearningState(
        student_id=student.id,
        concept_id=concept.id,
        concept_mastery=50.0,
        accuracy=50.0,
        problem_solving_score=50.0,
        hint_dependence=0.0,
        evidence_count=1,
        confidence_score=0.3,
    )
    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    assert state.student.id == student.id
    assert state.concept.id == concept.id
    assert state.concept.concept_code == "PHY_NLM_001"


def test_duplicate_learning_state_for_same_student_and_concept_is_rejected(db_session):
    student, concept = _seed_student_and_concept(db_session)

    first = LearningState(
        student_id=student.id, concept_id=concept.id,
        concept_mastery=50.0, accuracy=50.0, problem_solving_score=50.0,
        hint_dependence=0.0, evidence_count=1, confidence_score=0.3,
    )
    db_session.add(first)
    db_session.commit()

    duplicate = LearningState(
        student_id=student.id, concept_id=concept.id,
        concept_mastery=60.0, accuracy=60.0, problem_solving_score=60.0,
        hint_dependence=10.0, evidence_count=2, confidence_score=0.5,
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # exactly one row exists for this (student, concept) pair
    count = (
        db_session.query(LearningState)
        .filter_by(student_id=student.id, concept_id=concept.id)
        .count()
    )
    assert count == 1


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("concept_mastery", -0.1),
        ("concept_mastery", 100.1),
        ("accuracy", -1.0),
        ("accuracy", 101.0),
        ("problem_solving_score", -5.0),
        ("problem_solving_score", 150.0),
        ("hint_dependence", -0.01),
        ("hint_dependence", 100.01),
        ("confidence_score", -0.1),
        ("confidence_score", 1.1),
    ],
)
def test_score_range_constraints_are_enforced(db_session, field, bad_value):
    student, concept = _seed_student_and_concept(db_session)

    values = dict(
        concept_mastery=50.0, accuracy=50.0, problem_solving_score=50.0,
        hint_dependence=50.0, evidence_count=1, confidence_score=0.5,
    )
    values[field] = bad_value

    state = LearningState(student_id=student.id, concept_id=concept.id, **values)
    db_session.add(state)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_evidence_count_cannot_be_negative(db_session):
    student, concept = _seed_student_and_concept(db_session)

    state = LearningState(
        student_id=student.id, concept_id=concept.id,
        concept_mastery=50.0, accuracy=50.0, problem_solving_score=50.0,
        hint_dependence=50.0, evidence_count=-1, confidence_score=0.5,
    )
    db_session.add(state)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_different_concepts_for_same_student_are_allowed(db_session):
    """The unique constraint is (student_id, concept_id) together, not student_id alone."""
    student, concept_1 = _seed_student_and_concept(db_session)

    chapter = concept_1.chapter
    concept_2 = Concept(
        chapter_id=chapter.id, concept_code="PHY_FRIC_001", name="Friction",
        difficulty=3, exam_importance=ExamImportance.HIGH,
    )
    db_session.add(concept_2)
    db_session.commit()

    db_session.add(LearningState(
        student_id=student.id, concept_id=concept_1.id,
        concept_mastery=50.0, accuracy=50.0, problem_solving_score=50.0,
        hint_dependence=0.0, evidence_count=1, confidence_score=0.3,
    ))
    db_session.add(LearningState(
        student_id=student.id, concept_id=concept_2.id,
        concept_mastery=60.0, accuracy=60.0, problem_solving_score=60.0,
        hint_dependence=0.0, evidence_count=1, confidence_score=0.3,
    ))
    db_session.commit()  # should not raise

    count = db_session.query(LearningState).filter_by(student_id=student.id).count()
    assert count == 2
