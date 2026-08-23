from app.curriculum.models import Subject, Chapter, Concept, ConceptDependency, ExamImportance
from app.questions.models import (
    Question, QuestionType, ExamType, ProblemSolvingSkill,
)


def _auth_headers(client, email="rahul@example.com"):
    client.post("/auth/signup", json={"name": "R", "email": email, "password": "password123"})
    login = client.post("/auth/login", data={"username": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _seed_vectors_and_kinematics(db_session):
    subject = Subject(name="Physics", exam_pack="jee")
    db_session.add(subject)
    db_session.flush()
    chapter = Chapter(subject_id=subject.id, name="Mechanics", order_index=1)
    db_session.add(chapter)
    db_session.flush()

    vectors = Concept(
        chapter_id=chapter.id, concept_code="PHY_VEC_001", name="Vectors",
        difficulty=2, exam_importance=ExamImportance.HIGH,
    )
    kinematics = Concept(
        chapter_id=chapter.id, concept_code="PHY_KIN_001", name="Kinematics",
        difficulty=2, exam_importance=ExamImportance.HIGH,
    )
    db_session.add_all([vectors, kinematics])
    db_session.flush()

    db_session.add(
        ConceptDependency(concept_id=kinematics.id, prerequisite_concept_id=vectors.id)
    )
    db_session.commit()
    return vectors, kinematics


def test_prerequisite_chain_is_explicit(client, db_session):
    headers = _auth_headers(client)
    _seed_vectors_and_kinematics(db_session)

    resp = client.get("/curriculum/concepts/PHY_KIN_001", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["prerequisite_concept_codes"] == ["PHY_VEC_001"]


def test_question_list_never_exposes_answer(client, db_session):
    headers = _auth_headers(client)
    vectors, _ = _seed_vectors_and_kinematics(db_session)

    db_session.add(
        Question(
            question_text="What is a unit vector?",
            answer="A vector of magnitude 1",
            solution="Divide the vector by its magnitude.",
            primary_concept_id=vectors.id,
            difficulty=1,
            question_type=QuestionType.CONCEPTUAL,
            exam_type=ExamType.JEE_MAIN,
            estimated_time_seconds=60,
            problem_solving_skill=ProblemSolvingSkill.UNDERSTANDING,
        )
    )
    db_session.commit()

    resp = client.get("/questions", headers=headers, params={"concept_code": "PHY_VEC_001"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert "answer" not in body[0]
    assert "solution" not in body[0]
