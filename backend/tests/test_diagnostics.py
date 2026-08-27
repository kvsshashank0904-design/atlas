import uuid as uuid_lib

from app.curriculum.models import Subject, Chapter, Concept, ExamImportance
from app.questions.models import Question, QuestionType, ExamType as QExamType, ProblemSolvingSkill
from app.diagnostics.config import DIAGNOSTIC_TARGET_DISTRIBUTION


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
    return headers


def _seed_mechanics_chapter(db_session):
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
    return chapter, concept


def _make_question(db_session, concept, qtype, skill=ProblemSolvingSkill.EXECUTION, answer="42"):
    q = Question(
        question_text=f"Q-{uuid_lib.uuid4()}", answer=answer, solution="THE_SOLUTION_TEXT",
        primary_concept_id=concept.id, difficulty=2, question_type=qtype,
        exam_type=QExamType.JEE_MAIN, estimated_time_seconds=60,
        problem_solving_skill=skill,
    )
    db_session.add(q)
    return q


def _seed_full_distribution(db_session, chapter, concept):
    """Seeds exactly enough questions to satisfy the default 4/5/4/4/3 = 20 mix."""
    for _ in range(4):
        _make_question(db_session, concept, QuestionType.CONCEPTUAL)
    for _ in range(5):
        _make_question(db_session, concept, QuestionType.APPLICATION)
    for _ in range(4):
        _make_question(
            db_session, concept, QuestionType.NUMERICAL,
            skill=ProblemSolvingSkill.STRATEGY_SETUP,
        )
    for _ in range(4):
        _make_question(db_session, concept, QuestionType.MULTI_STEP)
    for _ in range(3):
        _make_question(db_session, concept, QuestionType.TRANSFER)
    db_session.commit()


def _seed_small_distribution(db_session, chapter, concept, distribution):
    for category, count in distribution.items():
        qtype_map = {
            "concept_understanding": (QuestionType.CONCEPTUAL, ProblemSolvingSkill.EXECUTION),
            "standard_application": (QuestionType.APPLICATION, ProblemSolvingSkill.EXECUTION),
            "strategy_selection": (QuestionType.NUMERICAL, ProblemSolvingSkill.STRATEGY_SETUP),
            "multi_step": (QuestionType.MULTI_STEP, ProblemSolvingSkill.EXECUTION),
            "transfer": (QuestionType.TRANSFER, ProblemSolvingSkill.EXECUTION),
        }
        qtype, skill = qtype_map[category]
        for _ in range(count):
            _make_question(db_session, concept, qtype, skill=skill)
    db_session.commit()


SMALL_DISTRIBUTION = {
    "concept_understanding": 1,
    "standard_application": 1,
    "strategy_selection": 1,
    "multi_step": 1,
    "transfer": 1,
}


# ---------------------------------------------------------------------
# Session start / question freezing
# ---------------------------------------------------------------------

def test_diagnostic_session_starts(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_full_distribution(db_session, chapter, concept)

    resp = client.post("/diagnostics/start", headers=headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["total_questions"] == sum(DIAGNOSTIC_TARGET_DISTRIBUTION.values())
    assert body["answered_count"] == 0
    assert body["remaining_questions"] == body["total_questions"]


def test_selected_questions_are_frozen_for_session(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_full_distribution(db_session, chapter, concept)

    session = client.post("/diagnostics/start", headers=headers).json()
    first_next = client.get(f"/diagnostics/{session['id']}/next", headers=headers).json()

    # Add a brand-new question that would otherwise be a better/earlier
    # match than anything already selected — it must NOT appear in this
    # already-started session.
    _make_question(db_session, concept, QuestionType.CONCEPTUAL)
    db_session.commit()

    second_next = client.get(f"/diagnostics/{session['id']}/next", headers=headers).json()
    assert first_next["question_id"] == second_next["question_id"]

    status = client.get(f"/diagnostics/{session['id']}", headers=headers).json()
    assert status["total_questions"] == sum(DIAGNOSTIC_TARGET_DISTRIBUTION.values())


def test_insufficient_question_bank_handled_clearly(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    # Only seed 2 conceptual questions when the default distribution wants 4.
    _make_question(db_session, concept, QuestionType.CONCEPTUAL)
    _make_question(db_session, concept, QuestionType.CONCEPTUAL)
    db_session.commit()

    resp = client.post("/diagnostics/start", headers=headers)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "shortfalls" in detail
    assert detail["shortfalls"]["concept_understanding"] == {"requested": 4, "available": 2}
    # every other category should also be reported as fully unavailable (0 questions seeded)
    assert detail["shortfalls"]["standard_application"]["available"] == 0


def test_select_diagnostic_questions_supports_smaller_distribution_override(client, db_session):
    """
    Verifies the 'configurable selection logic... allow tests to use
    smaller fixtures' requirement directly at the service level, since
    the API always uses the production default distribution.
    """
    from app.diagnostics.service import select_diagnostic_questions

    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_small_distribution(db_session, chapter, concept, SMALL_DISTRIBUTION)

    questions, shortfalls = select_diagnostic_questions(
        db_session, chapter.id, distribution=SMALL_DISTRIBUTION
    )
    assert shortfalls == {}
    assert len(questions) == sum(SMALL_DISTRIBUTION.values())


# ---------------------------------------------------------------------
# Next question / no leaks
# ---------------------------------------------------------------------

def test_next_question_no_leak_with_full_distribution(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_full_distribution(db_session, chapter, concept)

    session = client.post("/diagnostics/start", headers=headers).json()

    resp = client.get(
        f"/diagnostics/{session['id']}/next",
        headers=headers,
    )

    assert resp.status_code == 200

    data = resp.json()

    # Security: student-facing diagnostic responses must never
    # expose the canonical answer or solution.
    assert "answer" not in data
    assert "solution" not in data


# ---------------------------------------------------------------------
# Answer submission reuses Phase 2 pipeline
# ---------------------------------------------------------------------

def test_answer_submission_reuses_attempt_pipeline_and_generates_evidence(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_full_distribution(db_session, chapter, concept)

    session = client.post("/diagnostics/start", headers=headers).json()
    next_q = client.get(f"/diagnostics/{session['id']}/next", headers=headers).json()

    resp = client.post(
        f"/diagnostics/{session['id']}/answer",
        headers=headers,
        json={
            "question_id": next_q["question_id"],
            "selected_answer": "42",
            "response_time_seconds": 45,
            "hints_used": 2,
            "confidence": "medium",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["attempt"]["correct"] is True
    assert body["attempt"]["confidence"] == "medium"
    assert body["attempt"]["response_time_seconds"] == 45
    assert body["attempt"]["hints_used"] == 2

    attempts = client.get("/attempts/me", headers=headers).json()
    assert len(attempts) == 1
    assert attempts[0]["session_id"] == session["id"]  # linked to the diagnostic session

    evidence = client.get("/evidence/me", headers=headers).json()
    assert len(evidence) == 1
    assert evidence[0]["correct"] is True


def test_progress_increments_correctly(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_full_distribution(db_session, chapter, concept)

    session = client.post("/diagnostics/start", headers=headers).json()
    total = session["total_questions"]

    for i in range(3):
        status_before = client.get(f"/diagnostics/{session['id']}", headers=headers).json()
        assert status_before["answered_count"] == i

        next_q = client.get(f"/diagnostics/{session['id']}/next", headers=headers).json()
        client.post(
            f"/diagnostics/{session['id']}/answer",
            headers=headers,
            json={
                "question_id": next_q["question_id"],
                "selected_answer": "wrong",
                "response_time_seconds": 30,
                "hints_used": 0,
            },
        )

    status_after = client.get(f"/diagnostics/{session['id']}", headers=headers).json()
    assert status_after["answered_count"] == 3
    assert status_after["remaining_questions"] == total - 3
    assert status_after["status"] == "in_progress"  # no auto-completion in this phase


# ---------------------------------------------------------------------
# Security / integrity
# ---------------------------------------------------------------------

def test_wrong_student_cannot_access_another_students_session(client, db_session):
    headers_a = _setup_student(client, db_session, email="a@example.com")
    headers_b = _setup_student(client, db_session, email="b@example.com")
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_full_distribution(db_session, chapter, concept)

    session_a = client.post("/diagnostics/start", headers=headers_a).json()

    resp = client.get(f"/diagnostics/{session_a['id']}", headers=headers_b)
    assert resp.status_code == 404

    resp_next = client.get(f"/diagnostics/{session_a['id']}/next", headers=headers_b)
    assert resp_next.status_code == 404

    resp_answer = client.post(
        f"/diagnostics/{session_a['id']}/answer",
        headers=headers_b,
        json={
            "question_id": str(concept.id),  # irrelevant, should 404 before validation matters
            "selected_answer": "x",
            "response_time_seconds": 10,
        },
    )
    assert resp_answer.status_code == 404


def test_out_of_session_question_is_rejected(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_full_distribution(db_session, chapter, concept)

    session = client.post("/diagnostics/start", headers=headers).json()

    # A question that exists in the DB but was never selected into this session.
    foreign_question = _make_question(db_session, concept, QuestionType.CONCEPTUAL)
    db_session.commit()

    resp = client.post(
        f"/diagnostics/{session['id']}/answer",
        headers=headers,
        json={
            "question_id": str(foreign_question.id),
            "selected_answer": "42",
            "response_time_seconds": 30,
        },
    )
    assert resp.status_code == 400
    assert "not part of this diagnostic session" in resp.json()["detail"]


def test_duplicate_answer_is_rejected(client, db_session):
    headers = _setup_student(client, db_session)
    chapter, concept = _seed_mechanics_chapter(db_session)
    _seed_full_distribution(db_session, chapter, concept)

    session = client.post("/diagnostics/start", headers=headers).json()
    next_q = client.get(f"/diagnostics/{session['id']}/next", headers=headers).json()

    first = client.post(
        f"/diagnostics/{session['id']}/answer",
        headers=headers,
        json={
            "question_id": next_q["question_id"],
            "selected_answer": "42",
            "response_time_seconds": 30,
        },
    )
    assert first.status_code == 200

    second = client.post(
        f"/diagnostics/{session['id']}/answer",
        headers=headers,
        json={
            "question_id": next_q["question_id"],
            "selected_answer": "42",
            "response_time_seconds": 30,
        },
    )
    assert second.status_code == 400
    assert "already been answered" in second.json()["detail"]

    # exactly one attempt exists for that question, not two
    attempts = client.get("/attempts/me", headers=headers).json()
    assert len(attempts) == 1
