"""baseline existing backend schema

Revision ID: 0001
Revises: None
Create Date: 2026-09-08 06:08:17.835702

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def _uuid_type():
    # Freeze the current GUID storage without importing evolving app models.
    return sa.CHAR(36).with_variant(postgresql.UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    op.create_table('subjects',
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('exam_pack', sa.String(length=60), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'exam_pack', name='uq_subject_name_pack')
    )
    op.create_table('users',
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('chapters',
    sa.Column('subject_id', _uuid_type(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('student_profiles',
    sa.Column('user_id', _uuid_type(), nullable=False),
    sa.Column('available_time_minutes_per_day', sa.Integer(), nullable=False),
    sa.Column('days_available_per_week', sa.Integer(), nullable=False),
    sa.Column('preparation_level', sa.Enum('JUST_STARTING', 'SOME_CHAPTERS_COMPLETED', 'MOST_SYLLABUS_COVERED', 'REVISION_PHASE', name='preparation_level'), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('concepts',
    sa.Column('chapter_id', _uuid_type(), nullable=False),
    sa.Column('concept_code', sa.String(length=40), nullable=False),
    sa.Column('name', sa.String(length=160), nullable=False),
    sa.Column('difficulty', sa.Integer(), nullable=False),
    sa.Column('exam_importance', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='exam_importance'), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'RETIRED', name='concept_status'), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_concepts_concept_code'), 'concepts', ['concept_code'], unique=True)
    op.create_table('diagnostic_sessions',
    sa.Column('student_id', _uuid_type(), nullable=False),
    sa.Column('chapter_id', _uuid_type(), nullable=False),
    sa.Column('status', sa.Enum('IN_PROGRESS', 'COMPLETED', name='diagnostic_status'), nullable=False),
    sa.Column('total_questions', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['student_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_diagnostic_sessions_student_id'), 'diagnostic_sessions', ['student_id'], unique=False)
    op.create_table('goals',
    sa.Column('student_profile_id', _uuid_type(), nullable=False),
    sa.Column('exam_type', sa.Enum('JEE_MAIN', 'JEE_ADVANCED', name='exam_type'), nullable=False),
    sa.Column('target_score', sa.Integer(), nullable=False),
    sa.Column('exam_date', sa.Date(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['student_profile_id'], ['student_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('concept_dependencies',
    sa.Column('concept_id', _uuid_type(), nullable=False),
    sa.Column('prerequisite_concept_id', _uuid_type(), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ),
    sa.ForeignKeyConstraint(['prerequisite_concept_id'], ['concepts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('concept_id', 'prerequisite_concept_id', name='uq_concept_prereq')
    )
    op.create_table('learning_states',
    sa.Column('student_id', _uuid_type(), nullable=False),
    sa.Column('concept_id', _uuid_type(), nullable=False),
    sa.Column('concept_mastery', sa.Float(), nullable=False),
    sa.Column('accuracy', sa.Float(), nullable=False),
    sa.Column('problem_solving_score', sa.Float(), nullable=False),
    sa.Column('hint_dependence', sa.Float(), nullable=False),
    sa.Column('evidence_count', sa.Integer(), nullable=False),
    sa.Column('confidence_score', sa.Float(), nullable=False),
    sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.CheckConstraint('accuracy >= 0.0 AND accuracy <= 100.0', name='ck_learning_state_accuracy_range'),
    sa.CheckConstraint('concept_mastery >= 0.0 AND concept_mastery <= 100.0', name='ck_learning_state_concept_mastery_range'),
    sa.CheckConstraint('confidence_score >= 0.0 AND confidence_score <= 1.0', name='ck_learning_state_confidence_score_range'),
    sa.CheckConstraint('evidence_count >= 0', name='ck_learning_state_evidence_count_non_negative'),
    sa.CheckConstraint('hint_dependence >= 0.0 AND hint_dependence <= 100.0', name='ck_learning_state_hint_dependence_range'),
    sa.CheckConstraint('problem_solving_score >= 0.0 AND problem_solving_score <= 100.0', name='ck_learning_state_problem_solving_score_range'),
    sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['student_profiles.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('student_id', 'concept_id', name='uq_learning_state_student_concept')
    )
    op.create_index(op.f('ix_learning_states_concept_id'), 'learning_states', ['concept_id'], unique=False)
    op.create_index(op.f('ix_learning_states_student_id'), 'learning_states', ['student_id'], unique=False)
    op.create_table('questions',
    sa.Column('question_text', sa.Text(), nullable=False),
    sa.Column('answer', sa.Text(), nullable=False),
    sa.Column('solution', sa.Text(), nullable=False),
    sa.Column('primary_concept_id', _uuid_type(), nullable=False),
    sa.Column('difficulty', sa.Integer(), nullable=False),
    sa.Column('question_type', sa.Enum('CONCEPTUAL', 'FORMULA_RECALL', 'NUMERICAL', 'APPLICATION', 'MULTI_STEP', 'TRANSFER', 'PYQ_STYLE', name='question_type'), nullable=False),
    sa.Column('exam_type', sa.Enum('JEE_MAIN', 'JEE_ADVANCED', name='q_exam_type'), nullable=False),
    sa.Column('estimated_time_seconds', sa.Integer(), nullable=False),
    sa.Column('problem_solving_skill', sa.Enum('UNDERSTANDING', 'CONCEPT_SELECTION', 'STRATEGY_SETUP', 'EXECUTION', name='problem_solving_skill'), nullable=False),
    sa.Column('required_strategy', sa.String(length=200), nullable=True),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['primary_concept_id'], ['concepts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('attempts',
    sa.Column('student_id', _uuid_type(), nullable=False),
    sa.Column('question_id', _uuid_type(), nullable=False),
    sa.Column('selected_answer', sa.Text(), nullable=False),
    sa.Column('correct', sa.Boolean(), nullable=False),
    sa.Column('response_time_seconds', sa.Integer(), nullable=False),
    sa.Column('hints_used', sa.Integer(), nullable=False),
    sa.Column('confidence', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='confidence_level'), nullable=True),
    sa.Column('session_id', sa.String(length=100), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['student_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attempts_question_id'), 'attempts', ['question_id'], unique=False)
    op.create_index(op.f('ix_attempts_session_id'), 'attempts', ['session_id'], unique=False)
    op.create_index(op.f('ix_attempts_student_id'), 'attempts', ['student_id'], unique=False)
    op.create_table('question_concepts',
    sa.Column('question_id', _uuid_type(), nullable=False),
    sa.Column('concept_id', _uuid_type(), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('diagnostic_session_items',
    sa.Column('session_id', _uuid_type(), nullable=False),
    sa.Column('question_id', _uuid_type(), nullable=False),
    sa.Column('order_index', sa.Integer(), nullable=False),
    sa.Column('attempt_id', _uuid_type(), nullable=True),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.ForeignKeyConstraint(['attempt_id'], ['attempts.id'], ),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['diagnostic_sessions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('session_id', 'order_index', name='uq_diagnostic_item_order'),
    sa.UniqueConstraint('session_id', 'question_id', name='uq_diagnostic_item_question')
    )
    op.create_index(op.f('ix_diagnostic_session_items_session_id'), 'diagnostic_session_items', ['session_id'], unique=False)
    op.create_table('evidence_events',
    sa.Column('student_id', _uuid_type(), nullable=False),
    sa.Column('concept_id', _uuid_type(), nullable=False),
    sa.Column('question_id', _uuid_type(), nullable=False),
    sa.Column('attempt_id', _uuid_type(), nullable=False),
    sa.Column('event_type', sa.Enum('CORRECT_ATTEMPT', 'INCORRECT_ATTEMPT', name='evidence_event_type'), nullable=False),
    sa.Column('correct', sa.Boolean(), nullable=False),
    sa.Column('difficulty', sa.Integer(), nullable=False),
    sa.Column('question_type', sa.String(length=30), nullable=False),
    sa.Column('response_time_seconds', sa.Integer(), nullable=False),
    sa.Column('hints_used', sa.Integer(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('id', _uuid_type(), nullable=False),
    sa.ForeignKeyConstraint(['attempt_id'], ['attempts.id'], ),
    sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ),
    sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
    sa.ForeignKeyConstraint(['student_id'], ['student_profiles.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('attempt_id')
    )
    op.create_index(op.f('ix_evidence_events_concept_id'), 'evidence_events', ['concept_id'], unique=False)
    op.create_index(op.f('ix_evidence_events_student_id'), 'evidence_events', ['student_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_evidence_events_student_id'), table_name='evidence_events')
    op.drop_index(op.f('ix_evidence_events_concept_id'), table_name='evidence_events')
    op.drop_table('evidence_events')
    op.drop_index(op.f('ix_diagnostic_session_items_session_id'), table_name='diagnostic_session_items')
    op.drop_table('diagnostic_session_items')
    op.drop_table('question_concepts')
    op.drop_index(op.f('ix_attempts_student_id'), table_name='attempts')
    op.drop_index(op.f('ix_attempts_session_id'), table_name='attempts')
    op.drop_index(op.f('ix_attempts_question_id'), table_name='attempts')
    op.drop_table('attempts')
    op.drop_table('questions')
    op.drop_index(op.f('ix_learning_states_student_id'), table_name='learning_states')
    op.drop_index(op.f('ix_learning_states_concept_id'), table_name='learning_states')
    op.drop_table('learning_states')
    op.drop_table('concept_dependencies')
    op.drop_table('goals')
    op.drop_index(op.f('ix_diagnostic_sessions_student_id'), table_name='diagnostic_sessions')
    op.drop_table('diagnostic_sessions')
    op.drop_index(op.f('ix_concepts_concept_code'), table_name='concepts')
    op.drop_table('concepts')
    op.drop_table('student_profiles')
    op.drop_table('chapters')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_table('subjects')
    # PostgreSQL named enums outlive their tables unless explicitly dropped.
    if op.get_bind().dialect.name == "postgresql":
        for name in (
            "evidence_event_type", "confidence_level", "problem_solving_skill",
            "q_exam_type", "question_type", "exam_type", "diagnostic_status",
            "concept_status", "exam_importance", "preparation_level",
        ):
            postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=False)
