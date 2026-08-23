import uuid
import datetime

from pydantic import BaseModel, Field

from app.students.models import PreparationLevel, ExamType


class GoalCreate(BaseModel):
    exam_type: ExamType
    target_score: int = Field(ge=0, le=360)
    exam_date: datetime.date


class GoalOut(GoalCreate):
    id: uuid.UUID
    is_active: bool

    class Config:
        from_attributes = True


class StudentProfileCreate(BaseModel):
    available_time_minutes_per_day: int = Field(ge=15, le=960)
    days_available_per_week: int = Field(ge=1, le=7)
    preparation_level: PreparationLevel
    goal: GoalCreate


class StudentProfileOut(BaseModel):
    id: uuid.UUID
    available_time_minutes_per_day: int
    days_available_per_week: int
    preparation_level: PreparationLevel
    goals: list[GoalOut]

    class Config:
        from_attributes = True
