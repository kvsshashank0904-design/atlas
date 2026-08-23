import uuid

import enum

from sqlalchemy import String, Integer, ForeignKey, Enum, Text, UniqueConstraint
from app.core.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models_base import UUIDPkMixin, TimestampMixin


class ExamImportance(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConceptStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class Subject(Base, UUIDPkMixin, TimestampMixin):
    """
    Top of the curriculum tree. Section 1: MVP scope is a single subject
    (Physics) inside a single exam pack (JEE), but the model supports
    more subjects/exams without any schema change — that's the whole
    point of Section 1's "don't rebuild the core system" requirement.
    """
    __tablename__ = "subjects"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    exam_pack: Mapped[str] = mapped_column(String(60), nullable=False)  # e.g. "jee"

    chapters = relationship("Chapter", back_populates="subject", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("name", "exam_pack", name="uq_subject_name_pack"),)


class Chapter(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "chapters"

    subject_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("subjects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    subject = relationship("Subject", back_populates="chapters")
    concepts = relationship("Concept", back_populates="chapter", cascade="all, delete-orphan")


class Concept(Base, UUIDPkMixin, TimestampMixin):
    """
    Section 7. concept_code is the human-readable ID from the PRD
    (e.g. "PHY_NLM_001") kept distinct from the internal UUID pk so
    seed data / question metadata can reference stable codes.
    """
    __tablename__ = "concepts"

    chapter_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("chapters.id"), nullable=False
    )
    concept_code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5, matches question difficulty scale
    exam_importance: Mapped[ExamImportance] = mapped_column(
        Enum(ExamImportance, name="exam_importance"), nullable=False
    )
    status: Mapped[ConceptStatus] = mapped_column(
        Enum(ConceptStatus, name="concept_status"), default=ConceptStatus.ACTIVE
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)

    chapter = relationship("Chapter", back_populates="concepts")

    # prerequisites this concept depends on
    prerequisite_links = relationship(
        "ConceptDependency",
        foreign_keys="ConceptDependency.concept_id",
        back_populates="concept",
        cascade="all, delete-orphan",
    )
    # concepts that depend on this one (useful for prerequisite_importance in Study GPS later)
    dependent_links = relationship(
        "ConceptDependency",
        foreign_keys="ConceptDependency.prerequisite_concept_id",
        back_populates="prerequisite_concept",
    )


class ConceptDependency(Base, UUIDPkMixin):
    """
    Explicit prerequisite edges (Section 7: 'Relationships must be
    represented explicitly'). concept_id REQUIRES prerequisite_concept_id.
    """
    __tablename__ = "concept_dependencies"

    concept_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("concepts.id"), nullable=False
    )
    prerequisite_concept_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("concepts.id"), nullable=False
    )

    concept = relationship("Concept", foreign_keys=[concept_id], back_populates="prerequisite_links")
    prerequisite_concept = relationship(
        "Concept", foreign_keys=[prerequisite_concept_id], back_populates="dependent_links"
    )

    __table_args__ = (
        UniqueConstraint("concept_id", "prerequisite_concept_id", name="uq_concept_prereq"),
    )
