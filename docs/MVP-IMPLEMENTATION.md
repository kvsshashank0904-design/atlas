# Atlas MVP implementation record

## Phase 0: unchanged audit
Existing FastAPI modules, 14-table Alembic baseline, shared grading/evidence pipeline,
diagnostic lifecycle and DNA aggregation retained. Dashboard initially used mock-data.ts.
No Study GPS or session implementation existed. PostgreSQL/Docker unavailable.
Baseline: 98 passed, 4 PostgreSQL tests skipped, 299 warnings. Frontend npm install,
TypeScript, ESLint and production build passed. No source changes during audit.

## Plan
1. Preserve Milestone 1; correct default chapter lookup and restrict content authoring.
2. Add reviewed Mechanics content with reserved authored probe/check questions.
3. Connect existing frontend to authentication, onboarding and diagnostics.
4. Display real DNA, evidence explanations and curriculum edges.
5. Compute explainable next actions using deterministic coverage/prerequisite/skill rules.
6. Persist owned mission sessions and ordered items; reuse shared attempt transaction.
7. Classify only supported authored-probe observations, otherwise undetermined.
8. Recompute state and planner after study evidence; show genuine before/after snapshots.
9. Refine existing dark UI with measured state plots and focused question workspace.
10. Run regression/build/browser checks, document clean setup and honest limitations.

Live PostgreSQL verification remains required before final acceptance. The user authorized a phase-by-phase GitHub upload on 2026-09-10; use a separate branch and draft PR, without merging master.


## Milestone 1: backend stability
- Retained attribute-based curriculum loader, Alembic baseline for 14 tables,
  atomic practice attempt/evidence/state writes, atomic diagnostic linkage and completion,
  and PostgreSQL per-student locks from the earlier stabilization package.
- Added SQL exam-pack filtering to default diagnostic chapter resolution.
- Restricted question creation to configured CONTENT_EDITOR_EMAILS; default denies authoring.
- Added tests/test_mvp_stability.py (2 tests).
- Result before content work: 100 passed, 4 PostgreSQL checks skipped, 300 warnings.
- Live PostgreSQL migration/locking remains unverified in this environment.

## Milestone 2: Mechanics content and README
- Root README explains product, architecture, setup, migration safety, test commands and remaining work.
- app/questions/mechanics_content.py supplies 40 reviewed choice questions with worked solutions,
  types, skills, difficulty and time metadata supplied by scripts/seed_mvp.py.
- 25 diagnostic candidates cover all five target categories; 15 reserved questions form five
  main/probe/fresh-check sequences. These sequences are content only; sessions are not implemented yet.
- Existing curriculum/seed retained. Clarified which block receives the applied force in the legacy
  two-block example. Existing previously authored rows are not rewritten.
- Diagnostic selector excludes reserved content; scoring formulas and original tests are unchanged.
- tests/test_mvp_content.py adds 2 tests: fresh migrated seed/repeatability/editor preservation,
  and a real authenticated HTTP flow through all 20 answers, duplicate rejection, explicit completion,
  DNA and evidence consistency. Canonical answers are read only inside the server-side test harness.
- frontend/package-lock.json captures the successfully installed existing dependency versions.
- No frontend functionality changed in this milestone.

## Next phase: Milestone 3
Connect the existing Next.js dashboard to FastAPI with auth, onboarding, a diagnostic runner,
resume and explicit completion. Preserve current components and deterministic services.
Then implement real Learning DNA UI (Milestone 4), Study GPS (5), sessions (6),
conservative mistake observations (7), adaptation (8), UI refinement (9) and final QA (10).
Do not claim the complete MVP is ready at this checkpoint.

## Current limitations
- Live PostgreSQL: 4 opt-in checks still need a PostgreSQL host.
- Browser end-to-end learning flow: not implemented yet; the frontend is still the existing prototype.
- Seed is an additive MVP bank, not a comprehensive JEE preparation library.
- The reserved probe sequences target strategy selection; no misconception diagnoses are yet implemented.
- Local source began as an audited snapshot without a normal Git parent. Uploads must build on
  the verified remote tree and preserve remote-only files (including frontend/app/favicon.ico).


## Verified Phase 2 checkpoint — 2026-09-10
- Full backend suite: **102 passed, 4 skipped, 0 failures, 366 deprecation warnings**.
- Frontend: TypeScript, ESLint and production build all exit 0.
- Build emitted a recoverable Turbopack cache reset warning, then completed successfully.
- Git diff whitespace check passed.
- Original 82 backend tests preserved. Added across stabilization and content: 24 tests
  (20 locally passing and 4 opt-in PostgreSQL checks).
- Ready to upload as a draft PR, not to label the whole MVP complete.

### Files changed relative to audited master
README.md; backend/README.md; backend/alembic/versions/0001_baseline_existing_backend_schema.py;
backend/app/core/config.py; backend/app/curriculum/router.py; backend/app/diagnostics/service.py;
backend/app/learning_dna/service.py; backend/app/questions/mechanics_content.py;
backend/app/questions/router.py; backend/app/students/attempt_router.py;
backend/app/students/attempt_service.py; backend/app/students/dependencies.py;
backend/scripts/seed_mechanics.py; backend/scripts/seed_mvp.py;
backend/tests/test_backend_reliability.py; backend/tests/test_migrations_and_seed.py;
backend/tests/test_mvp_content.py; backend/tests/test_mvp_stability.py;
backend/tests/test_postgresql_reliability.py; docs/MVP-IMPLEMENTATION.md;
frontend/package-lock.json.
