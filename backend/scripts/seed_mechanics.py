"""
Seeds the initial JEE Physics -> Mechanics concept chain from PRD Section 1:
Vectors -> Kinematics -> Newton's Laws -> Friction -> Work, Energy & Power.

Run with:  python -m scripts.seed_mechanics
Idempotent: safe to re-run, skips anything that already exists by code.
"""
from app.core.database import SessionLocal
from app.curriculum.models import (
    Subject, Chapter, Concept, ConceptDependency, ExamImportance, ConceptStatus,
)
from app.questions.models import Question, QuestionType, ExamType, ProblemSolvingSkill

CONCEPT_CHAIN = [
    {
        "code": "PHY_VEC_001",
        "name": "Vectors",
        "difficulty": 2,
        "importance": ExamImportance.HIGH,
        "prereqs": [],
    },
    {
        "code": "PHY_KIN_001",
        "name": "Kinematics",
        "difficulty": 2,
        "importance": ExamImportance.HIGH,
        "prereqs": ["PHY_VEC_001"],
    },
    {
        "code": "PHY_NLM_001",
        "name": "Newton's Laws",
        "difficulty": 3,
        "importance": ExamImportance.HIGH,
        "prereqs": ["PHY_VEC_001", "PHY_KIN_001"],
    },
    {
        "code": "PHY_FRIC_001",
        "name": "Friction",
        "difficulty": 3,
        "importance": ExamImportance.HIGH,
        "prereqs": ["PHY_NLM_001"],
    },
    {
        "code": "PHY_WEP_001",
        "name": "Work, Energy & Power",
        "difficulty": 3,
        "importance": ExamImportance.HIGH,
        "prereqs": ["PHY_NLM_001", "PHY_FRIC_001"],
    },
]

SAMPLE_QUESTIONS = [
    {
        "concept_code": "PHY_NLM_001",
        "question_text": (
            "A block of mass 2 kg rests on a frictionless surface. A horizontal "
            "force of 10 N is applied. Find its acceleration."
        ),
        "answer": "5 m/s^2",
        "solution": "F = ma -> a = F/m = 10/2 = 5 m/s^2.",
        "difficulty": 2,
        "question_type": QuestionType.NUMERICAL,
        "exam_type": ExamType.JEE_MAIN,
        "estimated_time_seconds": 90,
        "problem_solving_skill": ProblemSolvingSkill.EXECUTION,
        "required_strategy": "Direct application of F=ma",
    },
    {
        "concept_code": "PHY_NLM_001",
        "question_text": (
            "Two blocks (3 kg and 2 kg) connected by a string are pulled by a "
            "12 N force on a frictionless surface. Find the tension in the string."
        ),
        "answer": "4.8 N",
        "solution": (
            "System acceleration a = F/(m1+m2) = 12/5 = 2.4 m/s^2. "
            "For the 2 kg block: T = m2 * a = 2 * 2.4 = 4.8 N."
        ),
        "difficulty": 4,
        "question_type": QuestionType.MULTI_STEP,
        "exam_type": ExamType.JEE_MAIN,
        "estimated_time_seconds": 180,
        "problem_solving_skill": ProblemSolvingSkill.STRATEGY_SETUP,
        "required_strategy": "System approach then isolate one block for tension",
    },
]


def seed():
    db = SessionLocal()
    try:
        subject = db.query(Subject).filter_by(name="Physics", exam_pack="jee").first()
        if not subject:
            subject = Subject(name="Physics", exam_pack="jee")
            db.add(subject)
            db.flush()

        chapter = db.query(Chapter).filter_by(subject_id=subject.id, name="Mechanics").first()
        if not chapter:
            chapter = Chapter(subject_id=subject.id, name="Mechanics", order_index=1)
            db.add(chapter)
            db.flush()

        code_to_concept = {}
        for item in CONCEPT_CHAIN:
            concept = db.query(Concept).filter_by(concept_code=item["code"]).first()
            if not concept:
                concept = Concept(
                    chapter_id=chapter.id,
                    concept_code=item["code"],
                    name=item["name"],
                    difficulty=item["difficulty"],
                    exam_importance=item["importance"],
                    status=ConceptStatus.ACTIVE,
                )
                db.add(concept)
                db.flush()
            code_to_concept[item["code"]] = concept

        for item in CONCEPT_CHAIN:
            concept = code_to_concept[item["code"]]
            for prereq_code in item["prereqs"]:
                prereq = code_to_concept[prereq_code]
                exists = (
                    db.query(ConceptDependency)
                    .filter_by(concept_id=concept.id, prerequisite_concept_id=prereq.id)
                    .first()
                )
                if not exists:
                    db.add(
                        ConceptDependency(
                            concept_id=concept.id, prerequisite_concept_id=prereq.id
                        )
                    )

        for q in SAMPLE_QUESTIONS:
            existing = (
                db.query(Question)
                .filter_by(question_text=q["question_text"])
                .first()
            )
            if existing:
                continue
            concept = code_to_concept[q["concept_code"]]
            db.add(
                Question(
                    question_text=q["question_text"],
                    answer=q["answer"],
                    solution=q["solution"],
                    primary_concept_id=concept.id,
                    difficulty=q["difficulty"],
                    question_type=q["question_type"],
                    exam_type=q["exam_type"],
                    estimated_time_seconds=q["estimated_time_seconds"],
                    problem_solving_skill=q["problem_solving_skill"],
                    required_strategy=q["required_strategy"],
                )
            )

        db.commit()
        print(f"Seeded {len(CONCEPT_CHAIN)} concepts and {len(SAMPLE_QUESTIONS)} sample questions.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
