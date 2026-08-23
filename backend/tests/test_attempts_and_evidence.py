from app.curriculum.models import Subject, Chapter, Concept, ExamImportance
from app.questions.models import (
    Question, QuestionType, ExamType as QExamType, ProblemSolvingSkill,
)


def _signup_login(client, email):
    client.post("/auth/signup", json={"name": "S", "email": email, "password": "password123"})
    login = client.post("/auth/login", data={"username": email, "password": "password123"})
    return login.json()["access_token"]


def _onboard(client, headers):
    resp = client.post(
        "/students/onboarding",
        headers=headers,
        json={
            "available_time_minutes_per_day": 180,
            "days_available_per_week": 6,
            "preparation_level": "some_chapters_completed",
            "goal": {"exam_type": "jee_main", "target_score": 180, "exam_date": "2027-01-15"},
        },
    )
    return resp.json()


def _seed_question(db_session):
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
    db_session.flush()

    question = Question(
        question_text="A 2 kg block is pushed with 10 N on a frictionless surface. Find a.",
        answer="5 m/s^2",
        solution="F=ma -> a = 10/2 = 5 m/s^2",
        primary_concept_id=concept.id,
        difficulty=2,
        question_type=QuestionType.NUMERICAL,
        exam_type=QExamType.JEE_MAIN,
        estimated_time_seconds=90,
        problem_solving_skill=ProblemSolvingSkill.EXECUTION,
    )
    db_session.add(question)
    db_session.commit()
    return question, concept


def _setup_student(client, db_session, email="rahul@example.com"):
    token = _signup_login(client, email)
    headers = {"Authorization": f"Bearer {token}"}
    _onboard(client, headers)
    return headers


def test_correct_attempt_is_graded_and_creates_evidence(client, db_session):
    headers = _setup_student(client, db_session)
    question, concept = _seed_question(db_session)

    resp = client.post(
        "/attempts",
        headers=headers,
        json={
            "question_id": str(question.id),
            "selected_answer": "5 m/s^2",
            "response_time_seconds": 60,
            "hints_used": 0,
            "session_id": "session_001",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["correct"] is True
    assert "answer" not in body  # attempt response never echoes canonical answer either

    evidence = client.get("/evidence/me", headers=headers)
    assert evidence.status_code == 200
    ev_body = evidence.json()
    assert len(ev_body) == 1
    assert ev_body[0]["correct"] is True
    assert ev_body[0]["event_type"] == "correct_attempt"
    assert ev_body[0]["concept_id"] == str(concept.id)


def test_incorrect_attempt_is_graded_and_creates_evidence(client, db_session):
    headers = _setup_student(client, db_session)
    question, _ = _seed_question(db_session)

    resp = client.post(
        "/attempts",
        headers=headers,
        json={
            "question_id": str(question.id),
            "selected_answer": "10 m/s^2",
            "response_time_seconds": 45,
            "hints_used": 2,
            "session_id": "session_001",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["correct"] is False

    evidence = client.get("/evidence/me", headers=headers).json()
    assert evidence[0]["correct"] is False
    assert evidence[0]["event_type"] == "incorrect_attempt"
    assert evidence[0]["hints_used"] == 2


def test_client_cannot_influence_correctness(client, db_session):
    """AttemptSubmit has no `correct` field — sending one is simply ignored/rejected."""
    headers = _setup_student(client, db_session)
    question, _ = _seed_question(db_session)

    resp = client.post(
        "/attempts",
        headers=headers,
        json={
            "question_id": str(question.id),
            "selected_answer": "10 m/s^2",  # wrong
            "correct": True,  # attempted spoof — not a real field
            "response_time_seconds": 30,
            "session_id": "session_001",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["correct"] is False  # server ignored the spoofed field


def test_multiple_attempts_preserved_in_history(client, db_session):
    headers = _setup_student(client, db_session)
    question, _ = _seed_question(db_session)

    for ans in ["10 m/s^2", "5 m/s^2", "3 m/s^2"]:
        client.post(
            "/attempts",
            headers=headers,
            json={
                "question_id": str(question.id),
                "selected_answer": ans,
                "response_time_seconds": 30,
                "session_id": "session_001",
            },
        )

    attempts = client.get("/attempts/me", headers=headers).json()
    evidence = client.get("/evidence/me", headers=headers).json()
    assert len(attempts) == 3
    assert len(evidence) == 3


def test_student_cannot_access_another_students_attempts(client, db_session):
    headers_a = _setup_student(client, db_session, email="a@example.com")
    headers_b = _setup_student(client, db_session, email="b@example.com")
    question, _ = _seed_question(db_session)

    client.post(
        "/attempts",
        headers=headers_a,
        json={
            "question_id": str(question.id),
            "selected_answer": "5 m/s^2",
            "response_time_seconds": 30,
            "session_id": "session_a",
        },
    )

    a_attempts = client.get("/attempts/me", headers=headers_a).json()
    b_attempts = client.get("/attempts/me", headers=headers_b).json()
    assert len(a_attempts) == 1
    assert len(b_attempts) == 0  # B sees nothing of A's — no student_id param exists to abuse

    a_evidence = client.get("/evidence/me", headers=headers_a).json()
    b_evidence = client.get("/evidence/me", headers=headers_b).json()
    assert len(a_evidence) == 1
    assert len(b_evidence) == 0


def test_attempt_and_evidence_never_leak_answer_or_solution(client, db_session):
    headers = _setup_student(client, db_session)
    question, _ = _seed_question(db_session)

    attempt_resp = client.post(
        "/attempts",
        headers=headers,
        json={
            "question_id": str(question.id),
            "selected_answer": "5 m/s^2",
            "response_time_seconds": 30,
            "session_id": "session_001",
        },
    )
    attempt_json_str = attempt_resp.text
    assert "F=ma" not in attempt_json_str  # solution text never present

    evidence_resp = client.get("/evidence/me", headers=headers)
    evidence_json_str = evidence_resp.text
    assert "F=ma" not in evidence_json_str

    attempts_history = client.get("/attempts/me", headers=headers)
    assert "F=ma" not in attempts_history.text
