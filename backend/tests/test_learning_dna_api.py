import uuid as uuid_lib

from app.curriculum.models import Subject, Chapter, Concept, ExamImportance
from app.questions.models import Question, QuestionType, ExamType as QExamType, ProblemSolvingSkill
from app.evidence.models import EvidenceEvent
from app.learning_dna.service import recalculate_learning_state


def _signup_login(client, email):
    client.post("/auth/signup", json={"name": "S", "email": email, "password": "password123"})
    login = client.post("/auth/login", data={"username": email, "password": "password123"})
    return login.json()["access_token"]


def _onboard(client, headers):
    client.post(
        "/students/onboarding",
        headers=headers,
        json={
            "available_time_minutes_per_day": 180,
            "days_available_per_week": 6,
            "preparation_level": "some_chapters_completed",
            "goal": {"exam_type": "jee_main", "target_score": 180, "exam_date": "2027-01-15"},
        },
    )


def _setup_student(client, db_session, email="rahul@example.com"):
    token = _signup_login(client, email)
    headers = {"Authorization": f"Bearer {token}"}
    _onboard(client, headers)
    profile = client.get("/students/me/profile", headers=headers).json()
    return headers, profile["id"]


def _seed_concept(db_session, code="PHY_NLM_001", name="Newton's Laws"):
    subject = Subject(name="Physics", exam_pack="jee")
    db_session.add(subject)
    db_session.flush()
    chapter = Chapter(subject_id=subject.id, name="Mechanics", order_index=1)
    db_session.add(chapter)
    db_session.flush()
    concept = Concept(
        chapter_id=chapter.id, concept_code=code, name=name,
        difficulty=3, exam_importance=ExamImportance.HIGH,
    )
    db_session.add(concept)
    db_session.commit()
    return concept


def _seed_question(db_session, concept, qtype=QuestionType.NUMERICAL):
    question = Question(
        question_text="Secret question text", answer="THE_ANSWER", solution="THE_SOLUTION",
        primary_concept_id=concept.id, difficulty=2, question_type=qtype,
        exam_type=QExamType.JEE_MAIN, estimated_time_seconds=60,
        problem_solving_skill=ProblemSolvingSkill.EXECUTION,
    )
    db_session.add(question)
    db_session.commit()
    return question


def _add_evidence(db_session, student_id, concept_id, question_id, correct, question_type, hints_used=0):
    db_session.add(
        EvidenceEvent(
            student_id=student_id, concept_id=concept_id, question_id=question_id,
            attempt_id=uuid_lib.uuid4(),
            event_type="correct_attempt" if correct else "incorrect_attempt",
            correct=correct, difficulty=2, question_type=question_type,
            response_time_seconds=30, hints_used=hints_used,
        )
    )
    db_session.commit()


# ---------------------------------------------------------------------
# GET /learning-dna/me
# ---------------------------------------------------------------------

def test_unauthenticated_request_is_rejected(client):
    resp = client.get("/learning-dna/me")
    assert resp.status_code == 401


def test_student_with_no_learning_state_gets_empty_list(client, db_session):
    headers, _ = _setup_student(client, db_session)
    resp = client.get("/learning-dna/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_learning_dna_me_returns_only_current_students_states(client, db_session):
    headers_a, student_a_id = _setup_student(client, db_session, email="a@example.com")
    headers_b, student_b_id = _setup_student(client, db_session, email="b@example.com")
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)

    _add_evidence(db_session, student_a_id, concept.id, question.id, True, "numerical")
    recalculate_learning_state(db_session, student_a_id, concept.id)

    dna_a = client.get("/learning-dna/me", headers=headers_a).json()
    dna_b = client.get("/learning-dna/me", headers=headers_b).json()
    assert len(dna_a) == 1
    assert len(dna_b) == 0  # B has no evidence and no LearningState at all


def test_concept_metadata_is_returned_correctly(client, db_session):
    headers, student_id = _setup_student(client, db_session)
    concept = _seed_concept(db_session, code="PHY_NLM_001", name="Newton's Laws")
    question = _seed_question(db_session, concept)
    _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical")
    recalculate_learning_state(db_session, student_id, concept.id)

    dna = client.get("/learning-dna/me", headers=headers).json()
    assert len(dna) == 1
    assert dna[0]["concept_id"] == str(concept.id)
    assert dna[0]["concept_code"] == "PHY_NLM_001"
    assert dna[0]["concept_name"] == "Newton's Laws"
    assert dna[0]["evidence_count"] == 1
    assert dna[0]["accuracy"] == 100.0


# ---------------------------------------------------------------------
# GET /learning-dna/me/{concept_id}
# ---------------------------------------------------------------------

def test_concept_detail_endpoint_works(client, db_session):
    headers, student_id = _setup_student(client, db_session)
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)
    _add_evidence(db_session, student_id, concept.id, question.id, False, "transfer")
    recalculate_learning_state(db_session, student_id, concept.id)

    resp = client.get(f"/learning-dna/me/{concept.id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["concept_id"] == str(concept.id)
    assert body["accuracy"] == 0.0


def test_concept_detail_missing_state_returns_404(client, db_session):
    headers, _ = _setup_student(client, db_session)
    concept = _seed_concept(db_session)
    # No evidence, no recalculation -> no LearningState row exists.
    resp = client.get(f"/learning-dna/me/{concept.id}", headers=headers)
    assert resp.status_code == 404


def test_concept_detail_unknown_concept_returns_404(client, db_session):
    headers, _ = _setup_student(client, db_session)
    resp = client.get(f"/learning-dna/me/{uuid_lib.uuid4()}", headers=headers)
    assert resp.status_code == 404


def test_another_students_state_never_leaks_via_detail_endpoint(client, db_session):
    headers_a, student_a_id = _setup_student(client, db_session, email="a@example.com")
    headers_b, _ = _setup_student(client, db_session, email="b@example.com")
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)
    _add_evidence(db_session, student_a_id, concept.id, question.id, True, "numerical")
    recalculate_learning_state(db_session, student_a_id, concept.id)

    resp_a = client.get(f"/learning-dna/me/{concept.id}", headers=headers_a)
    resp_b = client.get(f"/learning-dna/me/{concept.id}", headers=headers_b)
    assert resp_a.status_code == 200
    assert resp_b.status_code == 404  # B has no state for this concept, even though A does


# ---------------------------------------------------------------------
# GET /learning-dna/me/{concept_id}/explanation
# ---------------------------------------------------------------------

def test_explanation_counts_correct_and_incorrect_evidence_correctly(client, db_session):
    headers, student_id = _setup_student(client, db_session)
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)
    _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical")
    _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical")
    _add_evidence(db_session, student_id, concept.id, question.id, False, "transfer")

    resp = client.get(f"/learning-dna/me/{concept.id}/explanation", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["evidence_count"] == 3
    assert body["correct_count"] == 2
    assert body["incorrect_count"] == 1


def test_explanation_question_type_breakdown_is_correct(client, db_session):
    headers, student_id = _setup_student(client, db_session)
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)
    _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical")
    _add_evidence(db_session, student_id, concept.id, question.id, False, "numerical")
    _add_evidence(db_session, student_id, concept.id, question.id, True, "transfer")

    resp = client.get(f"/learning-dna/me/{concept.id}/explanation", headers=headers)
    breakdown = {item["question_type"]: item for item in resp.json()["question_type_breakdown"]}

    assert breakdown["numerical"]["count"] == 2
    assert breakdown["numerical"]["correct_count"] == 1
    assert breakdown["numerical"]["accuracy"] == 50.0

    assert breakdown["transfer"]["count"] == 1
    assert breakdown["transfer"]["correct_count"] == 1
    assert breakdown["transfer"]["accuracy"] == 100.0


def test_explanation_average_hints_calculation_is_correct(client, db_session):
    headers, student_id = _setup_student(client, db_session)
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)
    _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical", hints_used=0)
    _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical", hints_used=2)
    _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical", hints_used=4)

    resp = client.get(f"/learning-dna/me/{concept.id}/explanation", headers=headers)
    assert resp.json()["average_hints_used"] == 2.0  # (0+2+4)/3


def test_low_evidence_produces_limited_confidence_explanation(client, db_session):
    headers, student_id = _setup_student(client, db_session)
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)
    _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical")  # only 1

    resp = client.get(f"/learning-dna/me/{concept.id}/explanation", headers=headers)
    explanation = resp.json()["confidence_explanation"]
    assert "limited" in explanation
    assert "1" in explanation


def test_higher_evidence_produces_different_confidence_explanation(client, db_session):
    headers, student_id = _setup_student(client, db_session)
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)
    for _ in range(12):
        _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical")

    resp = client.get(f"/learning-dna/me/{concept.id}/explanation", headers=headers)
    explanation = resp.json()["confidence_explanation"]
    assert "limited" not in explanation
    assert "higher" in explanation


def test_explanation_does_not_expose_answer_or_solution(client, db_session):
    headers, student_id = _setup_student(client, db_session)
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)  # answer="THE_ANSWER", solution="THE_SOLUTION"
    _add_evidence(db_session, student_id, concept.id, question.id, True, "numerical")

    resp = client.get(f"/learning-dna/me/{concept.id}/explanation", headers=headers)
    assert "THE_ANSWER" not in resp.text
    assert "THE_SOLUTION" not in resp.text
    body = resp.json()
    assert "answer" not in body
    assert "solution" not in body


def test_explanation_does_not_mutate_evidence_events(client, db_session):
    headers, student_id = _setup_student(client, db_session)
    concept = _seed_concept(db_session)
    question = _seed_question(db_session, concept)
    _add_evidence(db_session, student_id, concept.id, question.id, True, "transfer", hints_used=1)

    before = [
        (e.id, e.correct, e.question_type, e.hints_used, e.timestamp)
        for e in db_session.query(EvidenceEvent).filter_by(student_id=student_id).all()
    ]

    client.get(f"/learning-dna/me/{concept.id}/explanation", headers=headers)
    client.get(f"/learning-dna/me/{concept.id}/explanation", headers=headers)  # call twice

    after = [
        (e.id, e.correct, e.question_type, e.hints_used, e.timestamp)
        for e in db_session.query(EvidenceEvent).filter_by(student_id=student_id).all()
    ]
    assert before == after
    assert len(after) == 1  # no rows added or removed


def test_explanation_requires_authentication(client, db_session):
    concept = _seed_concept(db_session)
    resp = client.get(f"/learning-dna/me/{concept.id}/explanation")
    assert resp.status_code == 401
