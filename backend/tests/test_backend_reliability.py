"""Regression coverage for milestone 1; exercise real ORM and HTTP paths."""
import uuid

import pytest
from sqlalchemy import event

from app.auth.models import User
from app.auth.security import create_access_token
from app.curriculum.models import Chapter, Concept, ExamImportance, Subject
from app.diagnostics import service as diagnostics
from app.diagnostics.models import DiagnosticSession, DiagnosticSessionItem, DiagnosticStatus
from app.diagnostics.schemas import DiagnosticAnswerSubmit
from app.evidence.models import EvidenceEvent
from app.learning_dna.models import LearningState
from app.questions.models import ExamType, ProblemSolvingSkill, Question, QuestionType
from app.students.attempt_models import Attempt
from app.students.models import PreparationLevel, StudentProfile


def make_student(db):
    user = User(name="Student", email=f"{uuid.uuid4()}@example.com", hashed_password="unused")
    db.add(user)
    db.flush()
    student = StudentProfile(
        user_id=user.id, available_time_minutes_per_day=60, days_available_per_week=5,
        preparation_level=PreparationLevel.JUST_STARTING,
    )
    db.add(student)
    db.commit()
    return student, {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def make_bank(db, concept_count=1):
    subject = Subject(name="Physics", exam_pack="jee")
    db.add(subject)
    db.flush()
    chapter = Chapter(name="Mechanics", subject_id=subject.id, order_index=1)
    db.add(chapter)
    db.flush()
    questions = []
    for i in range(concept_count):
        concept = Concept(
            chapter_id=chapter.id, concept_code=f"TEST_{i}", name=f"Concept {i}",
            difficulty=2, exam_importance=ExamImportance.HIGH,
        )
        db.add(concept)
        db.flush()
        question = Question(
            question_text=f"Question {i}", answer="42", solution="Canonical explanation",
            primary_concept_id=concept.id, difficulty=2, question_type=QuestionType.CONCEPTUAL,
            exam_type=ExamType.JEE_MAIN, estimated_time_seconds=60,
            problem_solving_skill=ProblemSolvingSkill.UNDERSTANDING,
        )
        db.add(question)
        questions.append(question)
    db.commit()
    return chapter, questions


def practice_payload(question, answer="42"):
    return dict(question_id=str(question.id), selected_answer=answer,
                response_time_seconds=30, hints_used=0, session_id="practice")


def answer_payload(question, answer="42"):
    return DiagnosticAnswerSubmit(question_id=question.id, selected_answer=answer,
                                 response_time_seconds=30, hints_used=0)


def start_small(db, student, chapter, count=1):
    return diagnostics.start_diagnostic(
        db, student.id, chapter.id, distribution={"concept_understanding": count}
    )


def test_subjects_lists_nested_chapters_and_concepts(client, db_session):
    _, headers = make_student(db_session)
    chapter, questions = make_bank(db_session, 2)
    response = client.get("/curriculum/subjects", headers=headers)
    assert response.status_code == 200
    subjects = response.json()
    assert len(subjects) == 1
    assert subjects[0]["name"] == "Physics"
    assert subjects[0]["chapters"][0]["id"] == str(chapter.id)
    assert {c["id"] for c in subjects[0]["chapters"][0]["concepts"]} == {
        str(q.primary_concept_id) for q in questions
    }
    assert client.get("/curriculum/subjects").status_code == 401


def test_subjects_returns_empty_list(client, db_session):
    _, headers = make_student(db_session)
    assert client.get("/curriculum/subjects", headers=headers).json() == []


def test_practice_creates_then_updates_only_owned_primary_concept_state(client, db_session):
    student, headers = make_student(db_session)
    other, other_headers = make_student(db_session)
    _, questions = make_bank(db_session, 2)
    q = questions[0]
    assert client.post("/attempts", headers=other_headers, json=practice_payload(q)).status_code == 201
    other_state = db_session.query(LearningState).filter_by(student_id=other.id).one()
    other_before = (other_state.id, other_state.evidence_count, other_state.accuracy)
    assert client.post("/attempts", headers=headers, json=practice_payload(q)).status_code == 201
    state = db_session.query(LearningState).filter_by(student_id=student.id).one()
    first_id = state.id
    assert (state.evidence_count, state.accuracy, state.concept_mastery) == (1, 100, 100)
    assert client.post("/attempts", headers=headers, json=practice_payload(q, "wrong")).status_code == 201
    db_session.expire_all()
    state = db_session.query(LearningState).filter_by(student_id=student.id).one()
    assert (state.id, state.evidence_count, state.accuracy, state.problem_solving_score) == (first_id, 2, 50, 50)
    assert state.concept_id == q.primary_concept_id
    other_state = db_session.query(LearningState).filter_by(student_id=other.id).one()
    assert (other_state.id, other_state.evidence_count, other_state.accuracy) == other_before
    evidence = client.get("/evidence/me", headers=headers).json()
    explanation = client.get(f"/learning-dna/me/{q.primary_concept_id}/explanation", headers=headers).json()
    assert explanation["evidence_count"] == len(evidence) == 2
    assert explanation["correct_count"] == 1
    assert len(client.get("/learning-dna/me", headers=headers).json()) == 1


def test_rejected_practice_does_not_create_evidence_or_state(client, db_session):
    _, headers = make_student(db_session)
    response = client.post("/attempts", headers=headers, json={
        "question_id": str(uuid.uuid4()), "selected_answer": "42",
        "response_time_seconds": 30, "session_id": "practice",
    })
    assert response.status_code == 404
    for model in (Attempt, EvidenceEvent, LearningState):
        assert db_session.query(model).count() == 0


def test_practice_rolls_back_attempt_evidence_and_existing_state_on_failure(client, db_session):
    student, headers = make_student(db_session)
    _, questions = make_bank(db_session)
    q = questions[0]
    client.post("/attempts", headers=headers, json=practice_payload(q))

    def fail_state_update(mapper, connection, target):
        raise RuntimeError("injected state persistence failure")

    event.listen(LearningState, "before_update", fail_state_update)
    try:
        with pytest.raises(RuntimeError, match="injected state"):
            client.post("/attempts", headers=headers, json=practice_payload(q, "wrong"))
    finally:
        event.remove(LearningState, "before_update", fail_state_update)
    assert db_session.query(Attempt).count() == db_session.query(EvidenceEvent).count() == 1
    state = db_session.query(LearningState).filter_by(student_id=student.id).one()
    assert (state.evidence_count, state.accuracy) == (1, 100)
    assert client.post("/attempts", headers=headers, json=practice_payload(q, "wrong")).status_code == 201
    assert db_session.query(LearningState).one().evidence_count == 2


def test_diagnostic_answer_remains_deferred_until_completion(client, db_session):
    student, headers = make_student(db_session)
    chapter, questions = make_bank(db_session)
    session = start_small(db_session, student, chapter)
    response = client.post(f"/diagnostics/{session.id}/answer", headers=headers,
                           json=answer_payload(questions[0]).model_dump(mode="json"))
    assert response.status_code == 200
    assert db_session.query(EvidenceEvent).count() == 1
    assert db_session.query(LearningState).count() == 0
    assert client.post(f"/diagnostics/{session.id}/complete", headers=headers).status_code == 200
    assert db_session.query(LearningState).one().evidence_count == 1


def test_diagnostic_link_failure_rolls_back_evidence_and_allows_retry(db_session):
    student, _ = make_student(db_session)
    chapter, questions = make_bank(db_session)
    session = start_small(db_session, student, chapter)
    payload = answer_payload(questions[0])

    def fail_link(mapper, connection, target):
        raise RuntimeError("injected linkage failure")

    event.listen(DiagnosticSessionItem, "before_update", fail_link)
    try:
        with pytest.raises(RuntimeError, match="injected linkage"):
            diagnostics.submit_diagnostic_answer(db_session, session, student.id, payload)
    finally:
        event.remove(DiagnosticSessionItem, "before_update", fail_link)
    assert db_session.query(Attempt).count() == db_session.query(EvidenceEvent).count() == 0
    assert db_session.query(DiagnosticSessionItem).one().attempt_id is None
    diagnostics.submit_diagnostic_answer(db_session, session, student.id, payload)
    assert db_session.query(Attempt).count() == db_session.query(EvidenceEvent).count() == 1


def test_completion_failure_rolls_back_every_concept_and_allows_retry(db_session):
    student, _ = make_student(db_session)
    chapter, questions = make_bank(db_session, 2)
    session = start_small(db_session, student, chapter, 2)
    for q in questions:
        diagnostics.submit_diagnostic_answer(db_session, session, student.id, answer_payload(q))
    calls = []

    def fail_second_state(mapper, connection, target):
        calls.append(target.concept_id)
        if len(calls) == 2:
            raise RuntimeError("injected second concept failure")

    event.listen(LearningState, "before_insert", fail_second_state)
    try:
        with pytest.raises(RuntimeError, match="second concept"):
            diagnostics.complete_diagnostic(db_session, session)
    finally:
        event.remove(LearningState, "before_insert", fail_second_state)
    assert len(calls) == 2
    assert db_session.query(LearningState).count() == 0
    assert session.status == DiagnosticStatus.IN_PROGRESS
    assert session.completed_at is None
    assert db_session.query(EvidenceEvent).count() == 2
    diagnostics.complete_diagnostic(db_session, session)
    assert db_session.query(LearningState).count() == 2
    assert session.status == DiagnosticStatus.COMPLETED


def test_completion_status_failure_rolls_back_state_updates(client, db_session):
    student, headers = make_student(db_session)
    chapter, questions = make_bank(db_session)
    q = questions[0]
    client.post("/attempts", headers=headers, json=practice_payload(q, "wrong"))
    session = start_small(db_session, student, chapter)
    diagnostics.submit_diagnostic_answer(db_session, session, student.id, answer_payload(q))

    def fail_status(mapper, connection, target):
        if target.status == DiagnosticStatus.COMPLETED:
            raise RuntimeError("injected completion status failure")

    event.listen(DiagnosticSession, "before_update", fail_status)
    try:
        with pytest.raises(RuntimeError, match="completion status"):
            diagnostics.complete_diagnostic(db_session, session)
    finally:
        event.remove(DiagnosticSession, "before_update", fail_status)
    state = db_session.query(LearningState).one()
    assert (state.evidence_count, state.accuracy) == (1, 0)
    assert session.status == DiagnosticStatus.IN_PROGRESS
    assert session.completed_at is None
    diagnostics.complete_diagnostic(db_session, session)
    assert (state.evidence_count, state.accuracy) == (2, 50)


def test_repeated_completion_includes_later_practice_without_duplicate_history(client, db_session):
    student, headers = make_student(db_session)
    chapter, questions = make_bank(db_session)
    q = questions[0]
    session = start_small(db_session, student, chapter)
    diagnostics.submit_diagnostic_answer(db_session, session, student.id, answer_payload(q))
    diagnostics.complete_diagnostic(db_session, session)
    completed_at = session.completed_at
    state_id = db_session.query(LearningState).one().id
    client.post("/attempts", headers=headers, json=practice_payload(q, "wrong"))
    diagnostics.complete_diagnostic(db_session, session)
    state = db_session.query(LearningState).one()
    assert (state.id, state.evidence_count, state.accuracy) == (state_id, 2, 50)
    assert session.completed_at == completed_at
    assert db_session.query(Attempt).count() == db_session.query(EvidenceEvent).count() == 2
