"""Migration/seed checks use disposable databases and the real CLI entrypoints."""
import os
from pathlib import Path
import subprocess
import sys

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.curriculum.models import Chapter, Concept, ExamImportance, Subject
from app.questions.models import Question
from scripts.seed_mechanics import CONCEPT_CHAIN, SAMPLE_QUESTIONS

BACKEND = Path(__file__).resolve().parents[1]


def run_cli(url, *args, check=True):
    env = dict(os.environ, DATABASE_URL=url, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, *args], cwd=BACKEND, env=env,
                            capture_output=True, text=True, timeout=60)
    if check:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


def migrate(url, *args):
    return run_cli(url, "-m", "alembic", *args)


@pytest.fixture
def migrated_database(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    migrate(url, "upgrade", "head")
    engine = create_engine(url)
    try:
        yield url, engine
    finally:
        engine.dispose()


def snapshot(engine):
    with engine.connect() as connection:
        return {
            table.name: sorted((tuple(map(str, row)) for row in connection.execute(select(table))))
            for table in Base.metadata.sorted_tables
        }


def assert_matches_models(engine):
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        inspector = inspect(connection)
        assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
        for name, table in Base.metadata.tables.items():
            expected_checks = {c.name for c in table.constraints if c.__class__.__name__ == "CheckConstraint"}
            assert {c["name"] for c in inspector.get_check_constraints(name)} == expected_checks
            expected_fks = {
                (tuple(fk.parent.name for fk in c.elements),
                 c.elements[0].column.table.name, tuple(fk.column.name for fk in c.elements))
                for c in table.foreign_key_constraints
            }
            actual_fks = {
                (tuple(c["constrained_columns"]), c["referred_table"], tuple(c["referred_columns"]))
                for c in inspector.get_foreign_keys(name)
            }
            assert actual_fks == expected_fks


def test_migration_upgrade_downgrade_reupgrade_matches_models(migrated_database):
    url, engine = migrated_database
    assert_matches_models(engine)
    migrate(url, "check")
    migrate(url, "upgrade", "head")
    migrate(url, "downgrade", "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    migrate(url, "upgrade", "head")
    assert_matches_models(engine)


def test_postgresql_offline_sql_has_native_uuid_enums_and_enum_cleanup():
    # SQL generation does not connect to a server.
    url = "postgresql+psycopg2://atlas:atlas@localhost/atlas"
    sql = migrate(url, "upgrade", "head", "--sql").stdout
    assert "id UUID NOT NULL" in sql
    assert sql.count("CREATE TABLE ") == 15  # 14 app tables + revision table
    assert sql.count("CREATE TYPE ") == 10
    assert "CREATE TYPE diagnostic_status AS ENUM ('IN_PROGRESS', 'COMPLETED')" in sql
    assert "uq_learning_state_student_concept" in sql
    assert "ck_learning_state_evidence_count_non_negative" in sql
    downgrade = migrate(url, "downgrade", "0001:base", "--sql").stdout
    assert downgrade.count("DROP TABLE ") == 15  # includes alembic_version in offline base downgrade
    assert downgrade.count("DROP TYPE ") == 10
    assert downgrade.index("DROP TABLE student_profiles") < downgrade.index("DROP TYPE preparation_level")


def test_seed_rerun_preserves_ids_content_and_authored_edits(migrated_database):
    url, engine = migrated_database
    run_cli(url, "-m", "scripts.seed_mechanics")
    with Session(engine) as db:
        question = db.query(Question).first()
        question.solution = "Reviewed explanation: preserve this edit"
        db.commit()
    before = snapshot(engine)
    run_cli(url, "-m", "scripts.seed_mechanics")
    assert snapshot(engine) == before
    assert len(before["subjects"]) == len(before["chapters"]) == 1
    assert len(before["concepts"]) == 5
    assert len(before["concept_dependencies"]) == 6
    assert len(before["questions"]) == 2
    with Session(engine) as db:
        for item in CONCEPT_CHAIN:
            concept = db.query(Concept).filter_by(concept_code=item["code"]).one()
            assert sorted(link.prerequisite_concept.concept_code for link in concept.prerequisite_links) == sorted(item["prereqs"])


def test_seed_conflicting_concept_rolls_back_without_changing_existing_data(migrated_database):
    url, engine = migrated_database
    with Session(engine) as db:
        subject = Subject(name="Other Physics", exam_pack="other")
        db.add(subject)
        db.flush()
        chapter = Chapter(name="Other chapter", subject_id=subject.id, order_index=1)
        db.add(chapter)
        db.flush()
        db.add(Concept(chapter_id=chapter.id, concept_code="PHY_KIN_001", name="Existing",
                       difficulty=2, exam_importance=ExamImportance.HIGH))
        db.commit()
    before = snapshot(engine)
    result = run_cli(url, "-m", "scripts.seed_mechanics", check=False)
    assert result.returncode != 0
    assert "already belongs to another chapter" in result.stderr
    assert snapshot(engine) == before


def test_seed_same_text_in_other_concept_does_not_suppress_sample(migrated_database):
    url, engine = migrated_database
    from tests.test_backend_reliability import make_bank
    with Session(engine) as db:
        _, questions = make_bank(db)
        questions[0].question_text = SAMPLE_QUESTIONS[0]["question_text"]
        existing_id = questions[0].id
        db.commit()
    run_cli(url, "-m", "scripts.seed_mechanics")
    before = snapshot(engine)
    run_cli(url, "-m", "scripts.seed_mechanics")
    assert snapshot(engine) == before
    with Session(engine) as db:
        assert db.query(Question).count() == 3
        assert db.get(Question, existing_id).answer == "42"
        seeded = db.query(Question).join(Concept, Question.primary_concept_id == Concept.id).filter(
            Concept.concept_code == "PHY_NLM_001"
        ).all()
        assert len(seeded) == 2
        assert {q.answer for q in seeded} == {q["answer"] for q in SAMPLE_QUESTIONS}


def test_seed_fresh_databases_have_same_semantic_content(tmp_path):
    def content(db_path):
        url = f"sqlite:///{db_path}"
        migrate(url, "upgrade", "head")
        run_cli(url, "-m", "scripts.seed_mechanics")
        engine = create_engine(url)
        try:
            with Session(engine) as db:
                return (
                    sorted((c.concept_code, c.name, c.difficulty, c.exam_importance.value,
                            tuple(sorted(p.prerequisite_concept.concept_code for p in c.prerequisite_links)))
                           for c in db.query(Concept)),
                    sorted((q.primary_concept.concept_code, q.question_text, q.answer, q.solution,
                            q.difficulty, q.question_type.value, q.problem_solving_skill.value)
                           for q in db.query(Question)),
                )
        finally:
            engine.dispose()
    assert content(tmp_path / "first.db") == content(tmp_path / "second.db")
