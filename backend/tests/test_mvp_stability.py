from app.curriculum.models import Subject, Chapter
from app.diagnostics.service import _resolve_chapter
from tests.test_curriculum_and_questions import _auth_headers


def test_default_chapter_filters_exam_pack(db_session):
    for pack in ("other", "jee"):
        subject = Subject(name="Physics", exam_pack=pack)
        db_session.add(subject)
        db_session.flush()
        db_session.add(Chapter(subject_id=subject.id, name="Mechanics", order_index=1))
    db_session.commit()
    assert _resolve_chapter(db_session, None).subject.exam_pack == "jee"


def test_student_cannot_author_questions(client):
    headers = _auth_headers(client)
    payload = dict(question_text="Q", answer="A", solution="S", primary_concept_code="X",
                   difficulty=1, question_type="conceptual", exam_type="jee_main",
                   estimated_time_seconds=30, problem_solving_skill="understanding")
    assert client.post("/questions", json=payload, headers=headers).status_code == 403
