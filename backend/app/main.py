from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.students.router import router as students_router
from app.curriculum.router import router as curriculum_router
from app.questions.router import router as questions_router
from app.students.attempt_router import router as attempts_router
from app.evidence.router import router as evidence_router
from app.learning_dna.router import router as learning_dna_router

app = FastAPI(
    title="Atlas API",
    description=(
        "Adaptive learning system — Phase 1 (auth, curriculum, questions), "
        "Phase 2 (attempts, evidence), Phase 3A-B (Learning DNA data model + "
        "deterministic scoring), Phase 3C (Learning DNA read API + explainability)."
    ),
    version="0.3.0",
)

app.include_router(auth_router)
app.include_router(students_router)
app.include_router(curriculum_router)
app.include_router(questions_router)
app.include_router(attempts_router)
app.include_router(evidence_router)
app.include_router(learning_dna_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
