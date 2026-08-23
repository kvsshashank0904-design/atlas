from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.auth.models import User
from app.auth.dependencies import get_current_user
from app.students.models import StudentProfile


def get_current_student_profile(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> StudentProfile:
    """
    Resolves the StudentProfile owned by the authenticated user. Used
    everywhere an endpoint must scope data to "my own records" — attempts
    and evidence both depend on this rather than accepting a student_id
    from the request, which is what makes cross-student access impossible
    by construction rather than by a manual ownership check.
    """
    profile = db.query(StudentProfile).filter(
        StudentProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Onboarding not completed yet")
    return profile
