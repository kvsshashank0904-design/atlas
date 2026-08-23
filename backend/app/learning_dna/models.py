import uuid
from datetime import datetime

from sqlalchemy import Integer, Float, ForeignKey, DateTime, func, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models_base import UUIDPkMixin
from app.core.types import GUID


class LearningState(Base, UUIDPkMixin):
    """
    Phase 3A: the data foundation for Atlas's current Learning DNA state
    (PRD Section 12). This table holds the CURRENT computed summary for
    one (student, concept) pair — exactly one row per pair.

    Deliberately NOT populated by any scoring logic yet: no service
    computes these values from EvidenceEvent in this phase (that's
    Phase 3B). EvidenceEvent (Phase 2) remains the sole immutable
    historical record; this model only defines where the eventual
    computed summary will live, and the constraints it must always
    satisfy once real values are written to it.
    """
    __tablename__ = "learning_states"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("concepts.id"), nullable=False, index=True
    )

    concept_mastery: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    problem_solving_score: Mapped[float] = mapped_column(Float, nullable=False)
    hint_dependence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    student = relationship("StudentProfile")
    concept = relationship("Concept")

    __table_args__ = (
        # A student may have only one current LearningState per concept —
        # enforced at the database level, not just in application code.
        UniqueConstraint("student_id", "concept_id", name="uq_learning_state_student_concept"),
        CheckConstraint(
            "concept_mastery >= 0.0 AND concept_mastery <= 100.0",
            name="ck_learning_state_concept_mastery_range",
        ),
        CheckConstraint(
            "accuracy >= 0.0 AND accuracy <= 100.0",
            name="ck_learning_state_accuracy_range",
        ),
        CheckConstraint(
            "problem_solving_score >= 0.0 AND problem_solving_score <= 100.0",
            name="ck_learning_state_problem_solving_score_range",
        ),
        CheckConstraint(
            "hint_dependence >= 0.0 AND hint_dependence <= 100.0",
            name="ck_learning_state_hint_dependence_range",
        ),
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name="ck_learning_state_confidence_score_range",
        ),
        CheckConstraint(
            "evidence_count >= 0",
            name="ck_learning_state_evidence_count_non_negative",
        ),
    )
