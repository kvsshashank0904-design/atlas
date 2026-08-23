import uuid

import enum

from sqlalchemy import String, Integer, ForeignKey, Enum, Date
from app.core.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models_base import UUIDPkMixin, TimestampMixin


class PreparationLevel(str, enum.Enum):
    JUST_STARTING = "just_starting"
    SOME_CHAPTERS_COMPLETED = "some_chapters_completed"
    MOST_SYLLABUS_COVERED = "most_syllabus_covered"
    REVISION_PHASE = "revision_phase"


class ExamType(str, enum.Enum):
    JEE_MAIN = "jee_main"
    JEE_ADVANCED = "jee_advanced"


class StudentProfile(Base, UUIDPkMixin, TimestampMixin):
    """
    One-to-one with User. Holds onboarding data from Section 6:
    available time and current preparation level. Academic goal
    (exam/target score/date) lives in Goal since a student could in
    future have more than one active goal.
    """
    __tablename__ = "student_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), unique=True, nullable=False
    )

    available_time_minutes_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    days_available_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    preparation_level: Mapped[PreparationLevel] = mapped_column(
        Enum(PreparationLevel, name="preparation_level"), nullable=False
    )

    user = relationship("User", back_populates="student_profile")
    goals = relationship("Goal", back_populates="student_profile", cascade="all, delete-orphan")


class Goal(Base, UUIDPkMixin, TimestampMixin):
    """Section 6 Academic Goal: exam, target score, exam date."""
    __tablename__ = "goals"

    student_profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("student_profiles.id"), nullable=False
    )
    exam_type: Mapped[ExamType] = mapped_column(Enum(ExamType, name="exam_type"), nullable=False)
    target_score: Mapped[int] = mapped_column(Integer, nullable=False)
    exam_date: Mapped[Date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    student_profile = relationship("StudentProfile", back_populates="goals")
