from tests.test_backend_reliability import make_student, make_bank, start_small, answer_payload
from app.diagnostics import service
from app.curriculum.models import ConceptDependency


def test_diagnostic_list_is_owned_resumable_and_has_no_answers(client, db_session):
    student, headers = make_student(db_session)
    other, other_headers = make_student(db_session)
    chapter, questions = make_bank(db_session)
    diagnostic = start_small(db_session, student, chapter)
    start_small(db_session, other, chapter)
    assert client.get("/diagnostics/me").status_code == 401
    rows = client.get("/diagnostics/me", headers=headers).json()
    assert len(rows) == 1 and rows[0]["id"] == str(diagnostic.id)
    assert rows[0]["answered_count"] == 0 and rows[0]["remaining_questions"] == 1
    assert "answer" not in rows[0] and "solution" not in rows[0]
    assert client.get(f"/diagnostics/{diagnostic.id}", headers=other_headers).status_code == 404
    service.submit_diagnostic_answer(db_session, diagnostic, student.id, answer_payload(questions[0]))
    row = client.get("/diagnostics/me", headers=headers).json()[0]
    assert row["answered_count"] == 1 and row["status"] == "in_progress"
    service.complete_diagnostic(db_session, diagnostic)
    assert client.get("/diagnostics/me", headers=headers).json()[0]["status"] == "completed"


def test_curriculum_list_contains_actual_prerequisite_edges(client, db_session):
    _, headers = make_student(db_session)
    _, questions = make_bank(db_session, concept_count=2)
    db_session.add(ConceptDependency(concept_id=questions[1].primary_concept_id,
                                    prerequisite_concept_id=questions[0].primary_concept_id))
    db_session.commit()
    concepts = client.get("/curriculum/subjects", headers=headers).json()[0]["chapters"][0]["concepts"]
    by_code = {c["concept_code"]: c for c in concepts}
    assert by_code["TEST_0"]["prerequisite_concept_codes"] == []
    assert by_code["TEST_1"]["prerequisite_concept_codes"] == ["TEST_0"]
