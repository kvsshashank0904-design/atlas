from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.models import User
from app.auth.dependencies import get_current_user
from app.students.models import StudentProfile, Goal
from app.students.schemas import StudentProfileCreate, StudentProfileOut

router = APIRouter(prefix="/students", tags=["students"])


@router.post("/onboarding", response_model=StudentProfileOut, status_code=201)
def complete_onboarding(
    payload: StudentProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Section 6. Called once, right after signup. Creates the student
    profile plus the initial active Goal. Analytics event
    'diagnostic_started' is NOT fired here — that belongs to the
    diagnostics module in Phase 3.
    """
    existing = db.query(StudentProfile).filter(
        StudentProfile.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Onboarding already completed")

    profile = StudentProfile(
        user_id=current_user.id,
        available_time_minutes_per_day=payload.available_time_minutes_per_day,
        days_available_per_week=payload.days_available_per_week,
        preparation_level=payload.preparation_level,
    )
    db.add(profile)
    db.flush()  # get profile.id without committing yet

    goal = Goal(
        student_profile_id=profile.id,
        exam_type=payload.goal.exam_type,
        target_score=payload.goal.target_score,
        exam_date=payload.goal.exam_date,
    )
    db.add(goal)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me/profile", response_model=StudentProfileOut)
def get_my_profile(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    profile = db.query(StudentProfile).filter(
        StudentProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Onboarding not completed yet")
    return profile
