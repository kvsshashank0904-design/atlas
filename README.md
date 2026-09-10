# Atlas — Adaptive Learning Intelligence

Atlas is an adaptive learning companion for JEE Physics Mechanics. It records
what a student does, derives a learning state from evidence, and is being
extended to choose, deliver, and evaluate the next useful intervention.

**Development status: MVP in progress, not yet hackathon-ready.** The existing
backend and connected frontend implement authentication, onboarding, diagnostics,
and evidence-backed Learning DNA. Study GPS, owned study sessions, mistake probes,
closed-loop adaptation, and final PostgreSQL/browser acceptance remain outstanding.

## Product loop

Observe → diagnose → understand the student → select an intervention →
teach/practise → verify → identify supported mistakes → update learning state →
select the next mission.

Initial curriculum: **Vectors → Kinematics → Newton's Laws → Friction →
Work, Energy & Power**. Additional prerequisite edges are stored explicitly in
the curriculum graph.

## Engineering principles

- Deterministic backend logic owns correctness, evidence, mastery, confidence,
  Learning DNA, and mission decisions. An LLM is not required to run the MVP.
- One shared grading/attempt/evidence pipeline; existing architecture is extended,
  not replaced.
- No fabricated progress or historical trajectories. Unmeasured is not failed.
- Student-reported confidence is distinct from evidence-derived confidence.
- Learning metrics are engineering heuristics, not validated psychological traits.
- Persistence changes require Alembic migrations and regression tests.

## Repository

```text
backend/
  app/auth/             JWT authentication
  app/students/         Profiles, goals, shared attempt pipeline
  app/curriculum/       Concepts and prerequisite relationships
  app/questions/        Questions and authored Mechanics content
  app/evidence/         Attempt-derived evidence
  app/learning_dna/     Deterministic scoring, state and explanations
  app/diagnostics/      Frozen diagnostic sessions and completion
  alembic/versions/     Database migration history
  scripts/             Repeatable curriculum/content seeds
  tests/               Backend regression and integration tests
frontend/              Existing Next.js / React / TypeScript / Tailwind app
docs/                  Implementation record
```

## Prerequisites

- Python 3.12 (the version used for verification).
- Node.js 20.9+ and npm for the existing Next.js frontend.
- PostgreSQL; the included Docker Compose configuration uses PostgreSQL 16.
  Docker Desktop is one option on Windows.

## Backend setup

Run from the repository root. Create a virtual environment:

```bash
cd backend
python -m venv .venv
```

Activate on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Then install the declared dependencies:

```bash
python -m pip install -r requirements.txt
```

Create `backend/.env` from `backend/.env.example`. Configure `DATABASE_URL`
and replace `JWT_SECRET_KEY` with a private random secret. Do not commit `.env`.
Optional `CONTENT_EDITOR_EMAILS` is a comma-separated editor allowlist; by
default students cannot author assessment questions.

For a **new local development database**, from `backend/`:

```bash
docker compose up -d postgres
python -m alembic upgrade head
python -m scripts.seed_mvp
python -m uvicorn app.main:app --reload
```

The Compose database uses the development connection configured in `.env.example`.
Use different credentials for any hosted environment. Wait for PostgreSQL to
be ready before running Alembic.

**Existing database warning:** inspect its schema and migration history first.
Do not blindly stamp the baseline, recreate tables, clear data, or run downgrade
against an existing personal/shared database.

The API runs at `http://localhost:8000`; interactive API docs are at
`http://localhost:8000/docs`. `/health` currently confirms process health, not
database readiness.

### Content

`seed_mechanics` retains the original curriculum and two example questions.
`seed_mvp` extends this with 25 authored diagnostic candidates and 15 reserved
study/probe/check questions. It preserves existing questions with the same
stable content identity. The new content uses explicit A–D choices to avoid
ambiguity in the existing exact-string grading contract.

The diagnostic requires 20 distinct questions across conceptual understanding,
application, strategy, multi-step reasoning, and transfer. Study questions are
excluded from diagnostic selection. Content seed repeatability, reserved-question exclusion, and the complete 20-question
HTTP diagnostic-to-DNA flow are verified on a migrated SQLite test database.

## Frontend setup

In a second terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. Create an account, complete onboarding, and start
or resume the 20-question Mechanics diagnostic. Explicitly complete it to update
Learning DNA, then select a concept to inspect the supporting evidence.

The frontend forwards `/api/*` to `http://127.0.0.1:8000/*`. To change the backend,
set `ATLAS_BACKEND_URL` in `frontend/.env.local` before starting or building Next.js.
This same-origin proxy avoids a separate browser CORS configuration. Login uses
form encoding and persists the bearer token locally; logout clears the student UI.
Active screens use backend data. Empty concepts remain unmeasured. The coordinate
plot shows current mastery and problem-solving values, not historical progress
or the output of a trained SVM.

## Verification

Backend, from `backend/` with the virtual environment active:

```bash
python -m pytest -q
```

Frontend, from `frontend/`:

```bash
npx tsc --noEmit
npm run lint
npm run build
```

### PostgreSQL integration gate

Use a dedicated local/test PostgreSQL role with CREATE DATABASE permission.
The integration tests create and drop individually named disposable databases;
they do not migrate or empty the supplied admin database.

PowerShell example using the included local development credentials:

```powershell
$env:ATLAS_TEST_POSTGRES_ADMIN_URL = 'postgresql+psycopg2://atlas:atlas@localhost:5432/postgres'
python -m pytest tests/test_postgresql_reliability.py -q
```

Linux/macOS equivalent:

```bash
ATLAS_TEST_POSTGRES_ADMIN_URL=postgresql+psycopg2://atlas:atlas@localhost:5432/postgres python -m pytest tests/test_postgresql_reliability.py -q
```

Latest completed Phase 3 run: **104 passed, 4 skipped, 0 failures,
371 deprecation warnings**. The four skipped tests require live PostgreSQL.
Frontend typecheck, ESLint, and production build passed again at this checkpoint.

## Completion roadmap

1. Backend stability — locally verified; live PostgreSQL gate open.
2. Mechanics bank and diagnostic readiness — locally verified; PostgreSQL gate open.
3. Authentication, onboarding, and diagnostic integration — implemented; signed-in browser acceptance open.
4. Evidence-backed Learning DNA interface — implemented; signed-in browser acceptance open.
5. Deterministic, explainable Study GPS.
6. Owned, resumable, retry-safe study sessions.
7. Narrow authored-probe mistake observations; undetermined when unsupported.
8. Evidence-driven adaptation and before/after state.
9. Scientific dark UI refinement using real measurements.
10. PostgreSQL/browser acceptance checks and a rehearsed three-minute demo.

Changes are uploaded only when explicitly requested. See
[the implementation record](docs/MVP-IMPLEMENTATION.md) for progress.

### Real frontend API integration smoke check

Use only a disposable migrated database seeded with `python -m scripts.seed_mvp`.
Run FastAPI and Next.js against it, then from `frontend/`:

```bash
ATLAS_SMOKE_ALLOW_WRITE=yes ATLAS_SMOKE_BASE_URL=http://localhost:3000 npm run test:api
```

This creates a disposable student and 20 real diagnostic attempts through the
actual frontend API client and Next proxy. It verifies login, onboarding,
prerequisite retrieval, resume, duplicate rejection, deferred recalculation,
completion, evidence consistency and token expiry. It leaves that test student in
the disposable database. It does not automate browser clicks or replace backend
responses. This check passed against a fresh migrated, seeded SQLite QA database;
it does not close the PostgreSQL or signed-in browser acceptance gates.
