from sqlalchemy.orm import Session
from app.curriculum.models import Chapter
from app.questions.models import Question
from app.questions.mechanics_content import BANK, RESERVED_IDS, content_id
from app.diagnostics.service import select_diagnostic_questions
from tests.test_migrations_and_seed import migrated_database, run_cli, snapshot


def test_seeded_diagnostic_http_loop_persists_real_evidence(migrated_database):
    from uuid import UUID
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import get_db
    from app.evidence.models import EvidenceEvent
    from app.students.attempt_models import Attempt

    url, engine = migrated_database
    run_cli(url, "-m", "scripts.seed_mvp")

    def database():
        with Session(engine, autoflush=False) as db:
            yield db

    app.dependency_overrides[get_db] = database
    try:
        with TestClient(app) as client:
            assert client.post("/auth/signup", json={"name": "Test Student", "email": "phase2@example.com", "password": "phase2-test-password"}).status_code == 201
            token = client.post("/auth/login", data={"username": "phase2@example.com", "password": "phase2-test-password"}).json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            assert client.post("/students/onboarding", headers=headers, json={
                "available_time_minutes_per_day": 30, "days_available_per_week": 5,
                "preparation_level": "just_starting", "goal": {
                    "exam_type": "jee_main", "target_score": 180, "exam_date": "2027-04-01"}}).status_code == 201
            response = client.post("/diagnostics/start", headers=headers)
            assert response.status_code == 201
            session_id = response.json()["id"]
            assert response.json()["total_questions"] == 20
            for index in range(20):
                question = client.get(f"/diagnostics/{session_id}/next", headers=headers).json()
                assert "answer" not in question and "solution" not in question
                assert UUID(question["question_id"]) not in RESERVED_IDS
                with Session(engine) as db:
                    answer = db.get(Question, UUID(question["question_id"])).answer
                payload = {"question_id": question["question_id"], "selected_answer": answer,
                           "response_time_seconds": 30, "confidence": "medium"}
                result = client.post(f"/diagnostics/{session_id}/answer", headers=headers, json=payload)
                assert result.status_code == 200
                assert result.json()["attempt"]["correct"] is True
                assert result.json()["remaining_questions"] == 19 - index
                assert client.post(f"/diagnostics/{session_id}/answer", headers=headers, json=payload).status_code == 400
            assert client.get("/learning-dna/me", headers=headers).json() == []
            completed = client.post(f"/diagnostics/{session_id}/complete", headers=headers)
            assert completed.status_code == 200
            states = client.get("/learning-dna/me", headers=headers).json()
            assert sum(state["evidence_count"] for state in states) == 20
            assert all(state["accuracy"] == 100 for state in states)
            assert client.post(f"/diagnostics/{session_id}/complete", headers=headers).status_code == 200
            with Session(engine) as db:
                assert db.query(Attempt).count() == db.query(EvidenceEvent).count() == 20
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_mvp_seed_fills_diagnostic_and_reserves_fresh_content(migrated_database):
    url, engine = migrated_database
    run_cli(url, "-m", "scripts.seed_mvp")
    before = snapshot(engine)
    run_cli(url, "-m", "scripts.seed_mvp")
    assert snapshot(engine) == before
    with Session(engine) as db:
        chapter = db.query(Chapter).one()
        selected, shortfalls = select_diagnostic_questions(db, chapter.id)
        assert not shortfalls
        assert len(selected) == len({q.id for q in selected}) == 20
        assert not ({q.id for q in selected} & RESERVED_IDS)
        assert db.query(Question).count() == 42
        for code, rows in BANK.items():
            for i, (_, answer, solution) in enumerate(rows):
                q = db.get(Question, content_id(code, i))
                assert q.answer == answer and answer in "ABCD"
                assert q.solution == solution and len(solution) > 30
                assert "Enter one letter" in q.question_text
        q = db.get(Question, content_id("PHY_VEC_001", 0))
        q.solution = "Editor correction must be preserved."
        db.commit()
    run_cli(url, "-m", "scripts.seed_mvp")
    with Session(engine) as db:
        assert db.get(Question, content_id("PHY_VEC_001", 0)).solution == "Editor correction must be preserved."
