import uuid
import enum
from datetime import datetime

from sqlalchemy import Integer, ForeignKey, Boolean, String, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models_base import UUIDPkMixin
from app.core.types import GUID


class EvidenceEventType(str, enum.Enum):
    """
    Phase 2 only emits the two attempt-outcome types. Section 15's
    progressive-diagnosis clarification events (e.g. concept_identification
    weakness) belong to the Mistake Engine in a later phase and are
    intentionally NOT included here yet.
    """
    CORRECT_ATTEMPT = "correct_attempt"
    INCORRECT_ATTEMPT = "incorrect_attempt"


class EvidenceEvent(Base, UUIDPkMixin):
    """
    Section 10. Evidence is preserved historically and NEVER overwritten
    or edited after creation — no updated_at, no update path exists
    anywhere in this module. Learning DNA (a later phase) will read and
    aggregate these events but must never mutate them; if a correction is
    ever needed, a new event should be appended, not an old one changed.

    mistake_type and diagnosis_confidence from the PRD's Section 10
    example belong to the Mistake Engine (a later phase) and are
    deliberately left off this model until that engine exists to
    populate them meaningfully.
    """
    __tablename__ = "evidence_events"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("concepts.id"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id"), nullable=False
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("attempts.id"), nullable=False, unique=True
    )

    event_type: Mapped[EvidenceEventType] = mapped_column(
        Enum(EvidenceEventType, name="evidence_event_type"), nullable=False
    )
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    response_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    student = relationship("StudentProfile")
    concept = relationship("Concept")
    question = relationship("Question")
    attempt = relationship("Attempt")
