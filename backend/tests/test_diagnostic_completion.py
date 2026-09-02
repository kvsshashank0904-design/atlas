import uuid as uuid_lib

from app.curriculum.models import Concept, ExamImportance
from app.questions.models import QuestionType, ProblemSolvingSkill
from app.learning_dna.models import LearningState
from app.students.attempt_models import Attempt
from app.evidence.models import EvidenceEvent
from app.diagnostics import service as diagnostic_service

from tests.test_diagnostics import (
    _signup_login,
    _onboard,
    _setup_student,
    _seed_mechanics_chapter,
    _make_question,
    SMALL_DISTRIBUTION,
)


def _student_id(client, headers):
    return client.get("/students/me/profile", headers=headers).json()["id"]


def _start_small_diagnostic(db_session, student_id, chapter, distribution=SMALL_DISTRIBUTION):
    """Bypasses the API's fixed production distribution so completion
    tests don't need to seed a full 20-question bank."""
    if isinstance(student_id, str):
        student_id = uuid_lib.UUID(student_id)
    session = diagnostic_service.start_diagnostic(
        db_session, student_id, chapter_id=chapter.id, distribution=distribution
    )
    return session


def _seed_one_question_per_category(db_session, chapter, concept, distribution=SMALL_DISTRIBUTION):
    qtype_map = {
        "concept_understanding": (QuestionType.CONCEPTUAL, ProblemSolvingSkill.EXECUTION),
        "standard_application": (QuestionType.APPLICATION, ProblemSolvingSkill.EXECUTION),
        "strategy_selection": (QuestionType.NUMERICAL, ProblemSolvingSkill.STRATEGY_SETUP),
        "multi_step": (QuestionType.MULTI_STEP, ProblemSolvingSkill.EXECUTION),
        "transfer": (QuestionType.TRANSFER, ProblemSolvingSkill.EXECUTION),
    }
    for category, count in distribution.items():
        qtype, skill = qtype_map[category]
        for _ in range(count):
            _make_question(db_session, concept, qtype, skill=skill)
    db_session.commit()


def _answer_all(client, headers, session_id):
    """Answers every remaining question in a session, all correctly ('42' matches the fixture answer)."""
    while True:
        next_q = client.get(f"/diagnostics/{session_id}/next", headers=headers).json()
        if next_q.get("diagnostic_complete"):
            break
        client.post(
            f"/diagnostics/{session_id}/answer",
            headers=headers,
            json={
                "question_id": next_q["question_id"],
                "selected_answer": "42",
                "response_time_seconds": 30,
                "hints_used": 0,
            },
        )


# ---------------------------------------------------------------------
# Completion validation
# ---------------------------------------------------------------------

def test_incomplete_diagnostic_cannot_be_completed(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_id = _student_id(client, headers)
    session = _start_small_diagnostic(db_session, student_id, chapter)

    # Answer only one of the five questions.
    next_q = client.get(f"/diagnostics/{session.id}/next", headers=headers).json()
    client.post(
        f"/diagnostics/{session.id}/answer",
        headers=headers,
        json={
            "question_id": next_q["question_id"],
            "selected_answer": "42",
            "response_time_seconds": 30,
            "hints_used": 0,
        },
    )

    resp = client.post(f"/diagnostics/{session.id}/complete", headers=headers)
    assert resp.status_code == 400
    assert "remain" in resp.json()["detail"]


def test_fully_answered_diagnostic_can_be_completed(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_id = _student_id(client, headers)
    session = _start_small_diagnostic(db_session, student_id, chapter)

    _answer_all(client, headers, session.id)

    resp = client.post(f"/diagnostics/{session.id}/complete", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    assert body["answered_count"] == body["total_questions"] == 5


def test_wrong_student_cannot_complete_another_students_diagnostic(client, db_session):
    headers_a = _setup_student(client, db_session, email="a@example.com")
    headers_b = _setup_student(client, db_session, email="b@example.com")
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_a_id = _student_id(client, headers_a)
    session = _start_small_diagnostic(db_session, student_a_id, chapter)
    _answer_all(client, headers_a, session.id)

    resp = client.post(f"/diagnostics/{session.id}/complete", headers=headers_b)
    assert resp.status_code == 404


# ---------------------------------------------------------------------
# Learning DNA recalculation
# ---------------------------------------------------------------------

def test_learning_state_created_for_tested_concept(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_id = _student_id(client, headers)
    session = _start_small_diagnostic(db_session, student_id, chapter)
    _answer_all(client, headers, session.id)

    resp = client.post(f"/diagnostics/{session.id}/complete", headers=headers)
    body = resp.json()

    assert len(body["concepts_evaluated"]) == 1
    assert body["concepts_evaluated"][0] == str(concept.id)
    assert len(body["learning_states"]) == 1
    state_out = body["learning_states"][0]
    assert state_out["concept_id"] == str(concept.id)
    assert state_out["concept_code"] == concept.concept_code
    assert state_out["evidence_count"] == 5

    row_count = (
        db_session.query(LearningState)
        .filter_by(student_id=uuid_lib.UUID(student_id), concept_id=concept.id)
        .count()
    )
    assert row_count == 1


def test_existing_learning_state_is_updated_not_duplicated(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_id = _student_id(client, headers)

    # Pre-existing LearningState from unrelated evidence (simulating prior activity).
    db_session.add(
        EvidenceEvent(
            student_id=uuid_lib.UUID(student_id), concept_id=concept.id,
            question_id=uuid_lib.uuid4(), attempt_id=uuid_lib.uuid4(),
            event_type="correct_attempt", correct=True, difficulty=2,
            question_type="conceptual", response_time_seconds=20, hints_used=0,
        )
    )
    db_session.commit()
    from app.learning_dna.service import recalculate_learning_state
    pre_state = recalculate_learning_state(db_session, uuid_lib.UUID(student_id), concept.id)
    assert pre_state.evidence_count == 1

    session = _start_small_diagnostic(db_session, student_id, chapter)
    _answer_all(client, headers, session.id)
    resp = client.post(f"/diagnostics/{session.id}/complete", headers=headers)
    body = resp.json()

    # 1 pre-existing + 5 from the diagnostic = 6, on the SAME row.
    assert body["learning_states"][0]["evidence_count"] == 6
    row_count = (
        db_session.query(LearningState)
        .filter_by(student_id=uuid_lib.UUID(student_id), concept_id=concept.id)
        .count()
    )
    assert row_count == 1


def test_only_tested_concepts_are_recalculated(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_id = _student_id(client, headers)

    # A second, UNTESTED concept in the same chapter with its own prior evidence/state.
    untested_concept = Concept(
        chapter_id=chapter.id, concept_code="PHY_FRIC_001", name="Friction",
        difficulty=3, exam_importance=ExamImportance.HIGH,
    )
    db_session.add(untested_concept)
    db_session.commit()
    db_session.add(
        EvidenceEvent(
            student_id=uuid_lib.UUID(student_id), concept_id=untested_concept.id,
            question_id=uuid_lib.uuid4(), attempt_id=uuid_lib.uuid4(),
            event_type="correct_attempt", correct=True, difficulty=2,
            question_type="conceptual", response_time_seconds=20, hints_used=0,
        )
    )
    db_session.commit()
    from app.learning_dna.service import recalculate_learning_state
    untested_state_before = recalculate_learning_state(
        db_session, uuid_lib.UUID(student_id), untested_concept.id
    )
    untested_last_updated_before = untested_state_before.last_updated

    session = _start_small_diagnostic(db_session, student_id, chapter)  # only touches `concept`
    _answer_all(client, headers, session.id)
    resp = client.post(f"/diagnostics/{session.id}/complete", headers=headers)
    body = resp.json()

    assert len(body["concepts_evaluated"]) == 1
    assert body["concepts_evaluated"][0] == str(concept.id)

    db_session.refresh(untested_state_before)
    assert untested_state_before.evidence_count == 1  # unchanged
    assert untested_state_before.last_updated == untested_last_updated_before  # never touched


def test_multiple_tested_concepts_each_get_their_own_learning_state(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept_a = _seed_mechanics_chapter(db_session)
    concept_b = Concept(
        chapter_id=chapter.id, concept_code="PHY_FRIC_001", name="Friction",
        difficulty=3, exam_importance=ExamImportance.HIGH,
    )
    db_session.add(concept_b)
    db_session.commit()

    # 3 categories' worth of questions on concept_a, 2 on concept_b — still 5 total.
    _make_question(db_session, concept_a, QuestionType.CONCEPTUAL)
    _make_question(db_session, concept_a, QuestionType.APPLICATION)
    _make_question(db_session, concept_a, QuestionType.NUMERICAL, skill=ProblemSolvingSkill.STRATEGY_SETUP)
    _make_question(db_session, concept_b, QuestionType.MULTI_STEP)
    _make_question(db_session, concept_b, QuestionType.TRANSFER)
    db_session.commit()

    student_id = _student_id(client, headers)
    session = _start_small_diagnostic(db_session, student_id, chapter)
    _answer_all(client, headers, session.id)

    resp = client.post(f"/diagnostics/{session.id}/complete", headers=headers)
    body = resp.json()

    assert len(body["concepts_evaluated"]) == 2
    assert set(body["concepts_evaluated"]) == {str(concept_a.id), str(concept_b.id)}
    assert len(body["learning_states"]) == 2

    by_concept = {s["concept_id"]: s for s in body["learning_states"]}
    assert by_concept[str(concept_a.id)]["evidence_count"] == 3
    assert by_concept[str(concept_b.id)]["evidence_count"] == 2

    total_rows = db_session.query(LearningState).filter_by(student_id=uuid_lib.UUID(student_id)).count()
    assert total_rows == 2


# ---------------------------------------------------------------------
# Attempt/evidence history preserved, no duplication
# ---------------------------------------------------------------------

def test_completion_does_not_create_new_attempt_or_evidence_rows(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_id = _student_id(client, headers)
    session = _start_small_diagnostic(db_session, student_id, chapter)
    _answer_all(client, headers, session.id)

    attempts_before = db_session.query(Attempt).count()
    evidence_before = db_session.query(EvidenceEvent).count()

    client.post(f"/diagnostics/{session.id}/complete", headers=headers)

    assert db_session.query(Attempt).count() == attempts_before
    assert db_session.query(EvidenceEvent).count() == evidence_before


def test_repeated_completion_is_idempotent(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_id = _student_id(client, headers)
    session = _start_small_diagnostic(db_session, student_id, chapter)
    _answer_all(client, headers, session.id)

    first = client.post(f"/diagnostics/{session.id}/complete", headers=headers).json()
    attempts_after_first = db_session.query(Attempt).count()
    evidence_after_first = db_session.query(EvidenceEvent).count()
    learning_state_rows_after_first = db_session.query(LearningState).count()

    second = client.post(f"/diagnostics/{session.id}/complete", headers=headers)
    assert second.status_code == 200
    second_body = second.json()

    assert second_body["status"] == "completed"
    assert second_body["completed_at"] == first["completed_at"]  # not bumped on repeat
    assert second_body["learning_states"][0]["evidence_count"] == first["learning_states"][0]["evidence_count"]

    assert db_session.query(Attempt).count() == attempts_after_first
    assert db_session.query(EvidenceEvent).count() == evidence_after_first
    assert db_session.query(LearningState).count() == learning_state_rows_after_first  # no duplicate row


# ---------------------------------------------------------------------
# Response shape / leak protection
# ---------------------------------------------------------------------

def test_completion_payload_contains_learning_dna_summaries(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_id = _student_id(client, headers)
    session = _start_small_diagnostic(db_session, student_id, chapter)
    _answer_all(client, headers, session.id)

    body = client.post(f"/diagnostics/{session.id}/complete", headers=headers).json()
    state_out = body["learning_states"][0]
    for field in (
        "concept_id", "concept_code", "concept_name", "concept_mastery",
        "accuracy", "problem_solving_score", "hint_dependence",
        "evidence_count", "confidence_score", "last_updated",
    ):
        assert field in state_out


def test_completion_payload_does_not_expose_answer_or_solution(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_one_question_per_category(db_session, chapter, concept)
    student_id = _student_id(client, headers)
    session = _start_small_diagnostic(db_session, student_id, chapter)
    _answer_all(client, headers, session.id)

    body = client.post(f"/diagnostics/{session.id}/complete", headers=headers).json()

    assert "answer" not in body
    assert "solution" not in body
    for state_out in body["learning_states"]:
        assert "answer" not in state_out
        assert "solution" not in state_out
