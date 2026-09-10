"""Run after Alembic: python -m scripts.seed_mvp. Additive, no user data edits."""
from app.core.database import SessionLocal
from app.curriculum.models import Concept
from app.questions.models import Question, ExamType
from app.questions.mechanics_content import BANK, KINDS, SKILLS, content_id
from scripts.seed_mechanics import seed as seed_curriculum


def add_content(db):
    for code, rows in BANK.items():
        concept = db.query(Concept).filter_by(concept_code=code).one()
        for index, (stem, answer, solution) in enumerate(rows):
            qid = content_id(code, index)
            existing = db.get(Question, qid)
            if existing:
                if existing.primary_concept_id != concept.id:
                    raise ValueError("MVP content identity belongs to another concept")
                continue  # preserve authored edits
            db.add(Question(id=qid, primary_concept_id=concept.id,
                            question_text=stem + " Enter one letter: A, B, C or D.",
                            answer=answer, solution=solution, difficulty=2 if index in (0, 1, 2, 6) else 3,
                            question_type=KINDS[index], problem_solving_skill=SKILLS[index],
                            exam_type=ExamType.JEE_MAIN, estimated_time_seconds=60 if index in (0, 2, 6) else 150,
                            required_strategy="Resolve the physical model before calculation"))
    db.flush()


def seed():
    seed_curriculum()
    with SessionLocal() as db:
        try:
            add_content(db)
            db.commit()
        except Exception:
            db.rollback()
            raise
    print("Mechanics MVP bank ready: 25 diagnostic + 15 reserved study questions; legacy examples retained.")


if __name__ == "__main__":
    seed()
