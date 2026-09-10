"""Opt-in PostgreSQL checks. Never migrate or erase the supplied admin database.

ATLAS_TEST_POSTGRES_ADMIN_URL must point to a role allowed to CREATE DATABASE.
Each test creates and drops only its own atlas_m1_<random UUID> database.
"""
from concurrent.futures import ThreadPoolExecutor
import os
from threading import Barrier
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.diagnostics import service as diagnostics
from app.diagnostics.models import DiagnosticSession, DiagnosticSessionItem
from app.evidence.models import EvidenceEvent
from app.learning_dna.models import LearningState
from app.students.attempt_models import Attempt
from app.students.attempt_router import submit_attempt
from app.students.attempt_schemas import AttemptSubmit
from app.students.models import StudentProfile
from tests.test_backend_reliability import make_student, make_bank, start_small, answer_payload, practice_payload
from tests.test_migrations_and_seed import migrate, run_cli, snapshot, assert_matches_models


@pytest.fixture
def postgres_database():
    admin_url = os.environ.get("ATLAS_TEST_POSTGRES_ADMIN_URL")
    if not admin_url:
        pytest.skip("ATLAS_TEST_POSTGRES_ADMIN_URL not set; PostgreSQL integration unavailable")
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    if admin.dialect.name != "postgresql":
        admin.dispose()
        pytest.fail("ATLAS_TEST_POSTGRES_ADMIN_URL must use PostgreSQL")
    database_name = f"atlas_m1_{uuid.uuid4().hex}"
    created = False
    engine = None
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        created = True
        url = admin.url.set(database=database_name).render_as_string(hide_password=False)
        migrate(url, "upgrade", "head")
        engine = create_engine(url, poolclass=NullPool, connect_args={"options": "-c lock_timeout=10000 -c statement_timeout=20000"})
        yield url, engine
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{database_name}"'))
        admin.dispose()


def test_postgresql_fresh_migration_roundtrip_and_foreign_keys(postgres_database):
    url, engine = postgres_database
    assert_matches_models(engine)
    migrate(url, "check")
    assert len(inspect(engine).get_enums()) == 10
    assert str(next(c for c in inspect(engine).get_columns("users") if c["name"] == "id")["type"]) == "UUID"
    with Session(engine) as db:
        db.add(LearningState(student_id=uuid.uuid4(), concept_id=uuid.uuid4(),
                             concept_mastery=0, accuracy=0, problem_solving_score=0,
                             hint_dependence=0, evidence_count=0, confidence_score=0))
        with pytest.raises(IntegrityError) as exc:
            db.commit()
        assert exc.value.orig.pgcode == "23503"
        db.rollback()
    migrate(url, "upgrade", "head")
    migrate(url, "downgrade", "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    assert inspect(engine).get_enums() == []
    migrate(url, "upgrade", "head")
    assert_matches_models(engine)


def test_postgresql_seed_cli_is_idempotent(postgres_database):
    url, engine = postgres_database
    run_cli(url, "-m", "scripts.seed_mechanics")
    before = snapshot(engine)
    run_cli(url, "-m", "scripts.seed_mechanics")
    assert snapshot(engine) == before
    assert len(before["concepts"]) == 5
    assert len(before["questions"]) == 2


def test_postgresql_concurrent_diagnostic_answers_record_once(postgres_database):
    _, engine = postgres_database
    with Session(engine, autoflush=False) as db:
        student, _ = make_student(db)
        chapter, questions = make_bank(db)
        diagnostic = start_small(db, student, chapter)
        student_id, session_id = student.id, diagnostic.id
        payload = answer_payload(questions[0])
    barrier = Barrier(2, timeout=10)

    def answer():
        with Session(engine, autoflush=False) as db:
            session = db.get(DiagnosticSession, session_id)
            # Both sessions cache the unanswered slot before either submits.
            cached = db.query(DiagnosticSessionItem).filter_by(session_id=session_id).one()
            assert cached.attempt_id is None
            barrier.wait()
            try:
                diagnostics.submit_diagnostic_answer(db, session, student_id, payload)
                return "accepted"
            except diagnostics.DuplicateAnswerError:
                return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(answer) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == ["accepted", "duplicate"]
    with Session(engine) as db:
        assert db.query(Attempt).count() == db.query(EvidenceEvent).count() == 1
        assert db.query(DiagnosticSessionItem).one().attempt_id == db.query(Attempt).one().id
        assert db.query(LearningState).count() == 0


def test_postgresql_concurrent_practice_keeps_all_evidence_in_state(postgres_database):
    _, engine = postgres_database
    with Session(engine, autoflush=False) as db:
        student, _ = make_student(db)
        _, questions = make_bank(db)
        student_id = student.id
        payload = practice_payload(questions[0])
    barrier = Barrier(2, timeout=10)

    def practice(answer):
        with Session(engine, autoflush=False) as db:
            student = db.get(StudentProfile, student_id)
            barrier.wait()
            result = submit_attempt(AttemptSubmit(**dict(payload, selected_answer=answer)), db, student)
            return result.correct

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(practice, answer) for answer in ("42", "wrong")]
        assert sorted(f.result(timeout=30) for f in futures) == [False, True]
    with Session(engine) as db:
        assert db.query(Attempt).count() == db.query(EvidenceEvent).count() == 2
        state = db.query(LearningState).one()
        assert (state.evidence_count, state.accuracy) == (2, 50)
