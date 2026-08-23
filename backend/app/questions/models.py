import uuid

import enum

from sqlalchemy import String, Integer, Text, ForeignKey, Enum
from app.core.types import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.models_base import UUIDPkMixin, TimestampMixin


class QuestionType(str, enum.Enum):
    CONCEPTUAL = "conceptual"
    FORMULA_RECALL = "formula_recall"
    NUMERICAL = "numerical"
    APPLICATION = "application"
    MULTI_STEP = "multi_step"
    TRANSFER = "transfer"
    PYQ_STYLE = "pyq_style"


class ExamType(str, enum.Enum):
    JEE_MAIN = "jee_main"
    JEE_ADVANCED = "jee_advanced"


class ProblemSolvingSkill(str, enum.Enum):
    """Section 16 stages — what this question is primarily designed to exercise."""
    UNDERSTANDING = "understanding"
    CONCEPT_SELECTION = "concept_selection"
    STRATEGY_SETUP = "strategy_setup"
    EXECUTION = "execution"


class Question(Base, UUIDPkMixin, TimestampMixin):
    """
    Section 8. Difficulty scale: 1 Easy, 2 Medium, 3 Hard,
    4 JEE Main level, 5 JEE Advanced style — kept as a plain int per PRD.
    """
    __tablename__ = "questions"

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)

    primary_concept_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("concepts.id"), nullable=False
    )
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type"), nullable=False
    )
    exam_type: Mapped[ExamType] = mapped_column(Enum(ExamType, name="q_exam_type"), nullable=False)
    estimated_time_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    problem_solving_skill: Mapped[ProblemSolvingSkill] = mapped_column(
        Enum(ProblemSolvingSkill, name="problem_solving_skill"), nullable=False
    )
    required_strategy: Mapped[str] = mapped_column(String(200), nullable=True)

    primary_concept = relationship("Concept")
    concept_links = relationship(
        "QuestionConcept", back_populates="question", cascade="all, delete-orphan"
    )


class QuestionConcept(Base, UUIDPkMixin):
    """
    Section 8: a question can tag multiple concept_ids (a multi-step
    problem might touch Vectors + Newton's Laws), while primary_concept
    on Question stays the single main concept used for DNA updates.
    """
    __tablename__ = "question_concepts"

    question_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("questions.id"), nullable=False
    )
    concept_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("concepts.id"), nullable=False
    )

    question = relationship("Question", back_populates="concept_links")
    concept = relationship("Concept")
