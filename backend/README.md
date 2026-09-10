# Atlas MVP — Backend

Implemented: authentication, student profiles/goals, curriculum, questions,
attempts/evidence, deterministic Learning DNA, and diagnostic completion.
Study GPS, study sessions, mistake diagnosis, teaching, and retention remain
out of scope. `later_vault.md` tracks deferred ideas.

## What's here

```
app/
  core/        settings, DB session, shared model mixins, cross-DB UUID type
  auth/        User model, signup/login/me, JWT + bcrypt
  students/    StudentProfile + Goal (onboarding, Section 6)
  curriculum/  Subject -> Chapter -> Concept -> ConceptDependency (Section 7)
  questions/   Question + QuestionConcept with full metadata (Section 8)
  evidence/     append-only attempt observations
  learning_dna/ deterministic scoring, current LearningState, read APIs
  diagnostics/  frozen diagnostic sessions and completion
  [empty packages for later features]
scripts/seed_mechanics.py   seeds Vectors -> Kinematics -> Newton's Laws ->
                            Friction -> Work/Energy/Power + 2 sample questions
tests/                      pytest suite (SQLite in-memory, no Postgres needed)
alembic/versions/0001_*      baseline for all 14 current application tables
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

alembic upgrade head
alembic check                   # no model/schema drift expected

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

Migration/seed tests also run the real CLI against temporary SQLite files and
compile PostgreSQL migration SQL. These checks do not replace live PostgreSQL
verification. To run the opt-in PostgreSQL migration, seed, foreign-key, and
concurrency tests against a local PostgreSQL instance:

```bash
ATLAS_TEST_POSTGRES_ADMIN_URL=postgresql+psycopg2://atlas:atlas@localhost:5432/postgres \
  pytest tests/test_postgresql_reliability.py -q
```

The supplied role needs `CREATE DATABASE`. Each test creates a uniquely named
`atlas_m1_<uuid>` database and drops only that database afterward. The supplied
admin database is never migrated or cleared. Without the environment variable,
these four tests are explicitly skipped. A configured but unreachable server
causes a test error, not a skip.

## Migration baseline and existing databases

Revision `0001` freezes the existing schema, including UUID columns, named
PostgreSQL enums, indexes, foreign keys, uniqueness, and LearningState checks.
It has no application-model imports and does not add learning features. Fresh
databases use `alembic upgrade head`; do not generate a new initial revision.
Downgrade removes tables in dependency order and cleans up PostgreSQL enum
types so a disposable database can be upgraded again.

For an existing unversioned database, back it up and compare its full schema
with a disposable database upgraded to `0001`. Only an exact matching schema
can be adopted with `alembic stamp 0001`, followed by `alembic check`. Stamping
does not create or repair tables. If the schema differs or is incomplete,
prepare an explicit reconciliation migration instead of blindly stamping it
or running this baseline over existing tables. No existing database is
automatically stamped or reset.

## Transaction and seed behavior

* An ordinary `POST /attempts` commits the attempt, its evidence, and the
  primary concept's recalculated LearningState together. Any failure rolls
  them all back. The scoring formulas and response schema are unchanged.
* Diagnostic answers commit attempt/evidence and frozen-slot linkage together;
  their route still defers recalculation until explicit completion. Completion
  commits all tested concept states and session status together. Repeating it
  preserves `completed_at` and does not duplicate history.
* PostgreSQL profile-row locks serialize these writes per student, including
  the first LearningState creation. SQLite does not validate row locking.
* Shared grading/recalculation functions retain their default commit behavior.
  Internal callers use `commit=False` to own the complete transaction and must
  commit or roll back; pending writes are flushed before returning.
* Run the seed once per deployment process. Sequential reruns preserve existing
  IDs and authored content; fresh databases have equivalent content/edges
  (UUIDs and timestamps are intentionally generated independently). A concept
  code belonging to another chapter causes a full rollback. Question identity
  is checked within the intended primary concept, not by text globally.
* The seed still contains five concepts and only two sample questions. It is
  not a complete bank for the 20-question diagnostic; content expansion is a
  later milestone.

## First manual smoke test (mirrors PRD Section 48, Phase 1 slice)

1. `POST /auth/signup` → `POST /auth/login` → get a bearer token.
2. `POST /students/onboarding` with JEE Main / target 180 / 4 months / 3h/day.
3. `GET /curriculum/subjects` → confirm Physics → Mechanics → the 5
   concepts appear with correct prerequisite edges.
4. `GET /questions?concept_code=PHY_NLM_001` → confirm questions return
   **without** `answer`/`solution` fields.

After these checks, submit a practice attempt and verify `/evidence/me` and
`/learning-dna/me` agree on the updated evidence count. With an adequate question
bank, also verify diagnostic answer -> explicit completion -> Learning DNA.

## Notes on decisions made without explicit PRD guidance

- Self-hosted JWT auth instead of Supabase (PRD allowed either).
- UUID primary keys everywhere (not specified, but matches the
  `student_id`/`question_id` string-ID style in the PRD's JSON examples
  while staying DB-agnostic).
- `later_vault.md` started per Section 49/53's instruction.
