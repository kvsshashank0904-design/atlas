import uuid
import enum
from datetime import datetime

from sqlalchemy import Integer, ForeignKey, DateTime, Enum, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models_base import UUIDPkMixin
from app.core.types import GUID


class DiagnosticStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    # ABANDONED intentionally omitted for this MVP phase — not needed
    # until there's a reason to distinguish "gave up" from "still going".


class DiagnosticSession(Base, UUIDPkMixin):
    """
    Phase 3D-1: one diagnostic run for one student. student_id always
    comes from get_current_student_profile (JWT-derived) — no endpoint
    in this module accepts a client-supplied student_id.

    `chapter_id` is this session's scope (the PRD's "subject_id or
    diagnostic_scope" field, phrased either way is fine per the spec).
    A Chapter is the right existing granularity for "JEE Physics ->
    Mechanics" specifically, and the engine generalizes to any other
    chapter/subject later just by pointing at a different Chapter row —
    no schema change needed for SAT, university courses, etc.

    Deliberately has NO stored current_index/progress column: how many
    items are answered is always derivable from
    DiagnosticSessionItem.attempt_id (count of non-null), the same way
    LearningState is derived from EvidenceEvent rather than duplicating
    it. A stored counter here would just be redundant state that could
    drift out of sync with the actual items.
    """
    __tablename__ = "diagnostic_sessions"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    chapter_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("chapters.id"), nullable=False
    )
    status: Mapped[DiagnosticStatus] = mapped_column(
        Enum(DiagnosticStatus, name="diagnostic_status"),
        default=DiagnosticStatus.IN_PROGRESS,
        nullable=False,
    )
    # Frozen at creation time — the count of questions actually selected
    # for this session. Never recalculated later, so it stays accurate
    # even if the question bank changes after the session starts.
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student = relationship("StudentProfile")
    chapter = relationship("Chapter")
    items = relationship(
        "DiagnosticSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DiagnosticSessionItem.order_index",
    )


class DiagnosticSessionItem(Base, UUIDPkMixin):
    """
    One frozen question slot within a diagnostic session. The full set
    of (session_id, question_id) rows is written once, at session-start
    time, and never added to or removed from afterward — this IS the
    mechanism that freezes the selected question set for the session
    (PRD requirement: "Selected question set must not change midway
    through the session").

    attempt_id is the only field that ever changes after creation, and
    it's set exactly once (from null to an Attempt id) when this
    question is answered — reusing Phase 2's grade_and_record_attempt,
    never a second grading path.
    """
    __tablename__ = "diagnostic_session_items"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("diagnostic_sessions.id"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id"), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("attempts.id"), nullable=True
    )

    session = relationship("DiagnosticSession", back_populates="items")
    question = relationship("Question")
    attempt = relationship("Attempt")

    __table_args__ = (
        UniqueConstraint("session_id", "order_index", name="uq_diagnostic_item_order"),
        # A question can only occupy one slot in a given session — this
        # is also what makes "duplicate answer" and "out-of-session
        # question" checks in the service layer reliable: there's never
        # more than one row to match against for a given pair.
        UniqueConstraint("session_id", "question_id", name="uq_diagnostic_item_question"),
    )
