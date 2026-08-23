# Atlas MVP — Backend (Phase 1)

Phase 1 only, per the PRD's development order (Section 47):
project setup, database, authentication, basic student profile,
curriculum/concept database, question database.

Nothing from Phase 2 onward (attempts, evidence, diagnostics, mistake
engine, Study GPS, teaching engine, retention, admin dashboard) is built
yet — see the PRD's phased plan. `later_vault.md` tracks explicit
out-of-scope ideas.

## What's here

```
app/
  core/        settings, DB session, shared model mixins, cross-DB UUID type
  auth/        User model, signup/login/me, JWT + bcrypt
  students/    StudentProfile + Goal (onboarding, Section 6)
  curriculum/  Subject -> Chapter -> Concept -> ConceptDependency (Section 7)
  questions/   Question + QuestionConcept with full metadata (Section 8)
  [15 more empty module folders for Phase 2+, per Section 37]
scripts/seed_mechanics.py   seeds Vectors -> Kinematics -> Newton's Laws ->
                            Friction -> Work/Energy/Power + 2 sample questions
tests/                      pytest suite (SQLite in-memory, no Postgres needed)
alembic/                    migrations
```

## Setup

Requires Python 3.11+ and Docker (for Postgres), or any Postgres 14+ instance.

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env — at minimum set a real JWT_SECRET_KEY

docker compose up -d          # starts local Postgres on :5432

alembic revision --autogenerate -m "phase 1 initial schema"
alembic upgrade head

python -m scripts.seed_mechanics   # loads the Mechanics concept chain

uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Tests

```bash
pytest
```

Tests run against an in-memory SQLite DB (see `tests/conftest.py`), so
they don't need Postgres or Docker running — just `pip install -r
requirements.txt` first.

## First manual smoke test (mirrors PRD Section 48, Phase 1 slice)

1. `POST /auth/signup` → `POST /auth/login` → get a bearer token.
2. `POST /students/onboarding` with JEE Main / target 180 / 4 months / 3h/day.
3. `GET /curriculum/subjects` → confirm Physics → Mechanics → the 5
   concepts appear with correct prerequisite edges.
4. `GET /questions?concept_code=PHY_NLM_001` → confirm questions return
   **without** `answer`/`solution` fields.

If all four work, Phase 1 has a heartbeat. Phase 2 (attempts + evidence
events) is the next thing to build — do not start it until this is
confirmed working against a real Postgres instance.

## Notes on decisions made without explicit PRD guidance

- Self-hosted JWT auth instead of Supabase (PRD allowed either).
- UUID primary keys everywhere (not specified, but matches the
  `student_id`/`question_id` string-ID style in the PRD's JSON examples
  while staying DB-agnostic).
- `later_vault.md` started per Section 49/53's instruction.
