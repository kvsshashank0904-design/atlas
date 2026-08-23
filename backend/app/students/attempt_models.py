import uuid
import enum
from datetime import datetime

from sqlalchemy import Integer, ForeignKey, Boolean, String, DateTime, Enum, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models_base import UUIDPkMixin
from app.core.types import GUID


class ConfidenceLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Attempt(Base, UUIDPkMixin):
    """
    Section 9. One row per question attempt. Deliberately richer than
    correct/incorrect — Atlas needs interaction metadata (response time,
    hints, confidence) to eventually diagnose *why*, not just *whether*.

    `correct` is NEVER set from client input — see attempts/service.py.
    Attempts have no updated_at: once submitted, an attempt is a fact
    about what happened and is never edited (Section 10 applies the same
    immutability principle to Evidence, and attempts are the source of it).
    """
    __tablename__ = "attempts"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("student_profiles.id"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id"), nullable=False, index=True
    )

    selected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)

    response_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[ConfidenceLevel | None] = mapped_column(
        Enum(ConfidenceLevel, name="confidence_level"), nullable=True
    )
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    student = relationship("StudentProfile")
    question = relationship("Question")
